# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import inspect
import json
import logging
import os
from typing import Any, Dict, Optional, Sequence, Union
from omegaconf import DictConfig
from openai import AzureOpenAI, OpenAI, ContentFilterFinishReasonError
from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from memora.utils.token_usage import TokenUsageCallback

logger = logging.getLogger(__name__)


def get_aoai_chat_completion_client(cfg: DictConfig) -> AzureOpenAI:
    """
    get the azure openai client
    Args:
        cfg: the config

    Returns: the azure openai client
    """
    _default_azure_ad_token_provider = get_bearer_token_provider(
        ManagedIdentityCredential(client_id=cfg.openai.managed_identity),
        "https://cognitiveservices.azure.com/.default",
    )

    client = AzureOpenAI(
        api_version=cfg.openai.llm_api_version,
        azure_endpoint=cfg.openai.llm_api_base,
        azure_ad_token_provider=_default_azure_ad_token_provider,
    )
    
    return client


def get_openai_chat_completion_client(cfg: DictConfig) -> OpenAI:
    """
    Get the standard OpenAI client (non-Azure).
    Args:
        cfg: the config (requires cfg.openai.api_key or OPENAI_API_KEY env var)

    Returns: the OpenAI client
    """
    api_key = cfg.openai.get("api_key", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key must be provided via cfg.openai.api_key or OPENAI_API_KEY environment variable."
        )
    client = OpenAI(api_key=api_key)
    return client


class ChatCompletionModel:
    """
    Base class for the language model.
    Supports both Azure OpenAI and local Hugging Face models (e.g., Qwen3-8B).
    Model type is automatically determined from the model name.
    """

    def __init__(self, cfg: DictConfig, token_usage_callback=None):
        """
        Args:
            cfg: the config
            token_usage_callback: callback for token usage tracking
        """
        self.cfg = cfg
        self.token_usage_callback = token_usage_callback
        
        # Determine model type from model name
        model_name = cfg.llm.model
        self.model_type = self._determine_model_type(model_name)
        
        if self.model_type == "huggingface":
            # Load local Hugging Face model
            self._load_hf_model(model_name)
            self.client = None
        else:
            # Use OpenAI-compatible client (Azure or standard OpenAI)
            api_type = cfg.openai.get("api_type", "azure")
            if api_type == "openai":
                self.client = get_openai_chat_completion_client(cfg)
            else:
                self.client = get_aoai_chat_completion_client(cfg)
            self.hf_model = None
            self.hf_tokenizer = None
    
    def _determine_model_type(self, model_name: str) -> str:
        """
        Determine if the model is from OpenAI or Hugging Face based on name.
        
        Args:
            model_name: Name of the model
            
        Returns:
            "azure" for OpenAI models, "huggingface" for HF models
        """
        # OpenAI/GPT models
        gpt_models = ["gpt-3", "gpt-4", "gpt-5", "o1", "o3"]
        
        if any(gpt_prefix in model_name.lower() for gpt_prefix in gpt_models):
            return "azure"
        
        # Otherwise assume it's a Hugging Face model
        return "huggingface"
    
    def _load_hf_model(self, model_name: str):
        """
        Load Hugging Face model (e.g., Qwen3-8B) locally.
        
        Args:
            model_name: Hugging Face model identifier (e.g., "Qwen3-8B" or "Qwen/Qwen3-8B")
        """
        # Normalize model name to Hugging Face format
        if not "/" in model_name:
            # Convert "Qwen3-8B" to "Qwen/Qwen3-8B"
            if model_name.startswith("Qwen"):
                model_name = f"Qwen/{model_name}"
        
        print(f"Loading Hugging Face model: {model_name}")
        
        self.hf_tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        self.hf_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        print(f"Model loaded successfully on device: {next(self.hf_model.parameters()).device}")

    def invoke(
        self,
        input: Union[str, Sequence[str]],
        prompt_args: Optional[Dict] = None,
        response_format: Any = None,
        source: str = "Unknown",
        **kwargs: Any,
    ) -> str:
        """
        Generate the response from the chat completion model
        Supports:
        - `invoke("Hello {name}", {"name": "Alice"})`
        - `invoke([LLMMessage(role="user", content="Hello!")])`

        if using the reasoning model, add the reasoning parameters such as
            reasoning={
                "effort": "medium",  # low, medium or high
                "summary": "detailed" # auto, concise, or detailed (currently only supported with o4-mini and o3)
            }
        Args:
            input: the input to the model
            prompt_args: the arguments for the prompt template
            response_format: the response format. If None, the response will be a string
            source: the source of the request (used for token usage tracking)
            kwargs: the kwargs for the prompt template

        Returns: the response
        """

        if isinstance(input, str):
            if prompt_args:  # Apply string formatting
                formatted_prompt = input.format(**prompt_args)
            else:
                formatted_prompt = input

            # Create a message with the formatted prompt
            messages=[
                {
                    "role": "user",
                    "content": formatted_prompt,
                }
            ]

        elif isinstance(input, list):
            messages = input  # Use messages as-is

        else:
            raise ValueError(
                "Input must be a string or a sequence of LLMMessage objects."
            )
        
        # Route to appropriate model
        if self.model_type == "huggingface":
            return self._invoke_hf(messages, source, **kwargs)
        else:
            return self._invoke_azure(messages, response_format, source, **kwargs)
    
    def _invoke_hf(self, messages: list, source: str = "Unknown", **kwargs) -> str:
        """Invoke Hugging Face model."""
        try:
            # Apply chat template
            text = self.hf_tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize input
            model_inputs = self.hf_tokenizer([text], return_tensors="pt").to(self.hf_model.device)
            
            # Set seed for reproducibility
            seed = self.cfg.llm.get("seed", 42)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            
            # Get generation parameters
            max_new_tokens = kwargs.pop("max_tokens", kwargs.pop("max_new_tokens", 512))
            temperature = kwargs.pop("temperature", 0.7)
            
            # Generate response
            with torch.no_grad():
                generated_ids = self.hf_model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    top_k=50,
                )
            
            # Decode the response
            generated_ids = [
                output_ids[len(input_ids):] 
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            result = self.hf_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Token usage tracking (approximate for HF models)
            if self.token_usage_callback:
                prompt_tokens = len(model_inputs.input_ids[0])
                completion_tokens = len(generated_ids[0])
                
                self.token_usage_callback.update(
                    prompt_tokens,
                    completion_tokens,
                    model="qwen3-8b",
                    source=source,
                )
            
            return result
            
        except Exception as e:
            print(f"Error in HF model invocation: {e}")
            raise e
    
    def _invoke_azure(self, messages: list, response_format: Any, source: str, **kwargs) -> str:
        """Invoke Azure OpenAI model."""
        try:

            if response_format:
                response = self.client.beta.chat.completions.parse(
                    messages=messages,
                    model=self.cfg.llm.model,
                    response_format=response_format,
                    seed=self.cfg.llm.get("seed", 42),
                    **kwargs,
                )
            else:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.cfg.llm.model,
                    seed=self.cfg.llm.get("seed", 42),
                    **kwargs,
                )

        except ContentFilterFinishReasonError as e:
            # Azure OpenAI content filter blocked the request
            logger.warning(
                f"Content filter blocked request. Returning empty response. "
                f"Messages length: {len(messages)}, Response format: {response_format.__name__ if response_format else 'None'}"
            )

            # Return an empty response based on the expected format
            if response_format:
                # Create an empty instance of the response format
                # Most Pydantic models used for memory extraction have an 'entries' field
                try:
                    result = response_format(entries=[])
                except Exception:
                    # If that doesn't work, try creating with no arguments
                    try:
                        result = response_format()
                    except Exception:
                        # As a last resort, raise the original error
                        logger.error(f"Could not create empty response for format {response_format}")
                        raise e
            else:
                result = ""

            return result

        except Exception as e:
            print(f"Error in Azure OpenAI invocation: {e}")
            raise e

        if response_format:
            # transform the response to the response format
            result = response.choices[0].message.parsed
        else:
            result = response.choices[0].message.content

        # calculate the tokens
        if self.token_usage_callback:
            usage = response.usage
            assert isinstance(self.token_usage_callback, TokenUsageCallback)

            # update source if not provided
            if source == "Unknown":
                try:
                    caller = inspect.stack()[1].frame.f_locals.get("self", None)
                    source = caller.__class__.__name__ if caller else "Unknown"
                except Exception as e:
                    source = "Unknown"

            self.token_usage_callback.update(
                usage.prompt_tokens,
                usage.completion_tokens,
                model=self.client.model_info["family"],
                source=source,
            )

        return result
