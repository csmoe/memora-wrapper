# memora-wrapper

Persistent memory for [Pi](https://pi.dev) and Codex-compatible MCP clients, backed by [Microsoft Memora](https://github.com/microsoft/Memora).

`memora-wrapper` exposes one Python MCP server and uses it everywhere. The Pi extension calls the MCP tools through a local stdio MCP client shim; Codex can connect to the same MCP server directly. OpenAI chat models use native structured parsing; DeepSeek and other OpenAI-compatible chat providers use JSON mode with schema validation.

## What It Adds

- MCP server: `src/memora_mcp.py`.
- Pi extension commands: `/memora status`, `/memora setup`, `/memora recall`, `/memora remember`, `/memora list`, and `/memora clear`.
- `memora_remember` tool for durable facts, decisions, preferences, and task outcomes.
- `memora_recall` tool for semantic memory lookup.
- `memora_list` tool for inspecting stored memories.
- `memora_delete` and `memora_clear` maintenance tools over MCP.
- Optional automatic recall before each prompt.
- Optional automatic capture after each agent run.

The MCP runtime is a uv project. Its Python dependencies live in `pyproject.toml`; it does not install Memora's full benchmark, RL, or local-Hugging-Face dependency set.

## Install

Global install:

```bash
pi install npm:pi-memora
```

Project-local install:

```bash
pi install npm:pi-memora -l
```

Local checkout:

```bash
pi install /path/to/memora-wrapper
```

One-session trial:

```bash
pi -e npm:pi-memora
```

If Pi is already running after installation, run `/reload` or start a new Pi session.

After installation, `/memora status` reports whether the Memora runtime is ready. `/memora setup` prepares the uv runtime and verifies the bundled Memora source.

## Codex MCP

Configure Codex with an MCP server that launches this package:

```toml
[mcp_servers.memora-wrapper]
command = "uv"
args = ["run", "--project", "/path/to/memora-wrapper", "python", "/path/to/memora-wrapper/src/memora_mcp.py"]
```

The server exposes `memora_status`, `memora_setup_instructions`, `memora_remember`, `memora_recall`, `memora_list`, `memora_delete`, and `memora_clear`.

Codex does not automatically capture every turn from MCP alone. Ask Codex to call `memora_remember`, or add Codex instructions that tell it when to use the memory tools.

## Before Launching

Set the embedding provider environment in the same shell before starting Pi or launching the Codex MCP server. The package does not read env files or edit shell startup files.

Required:

- An embedding model name.
- An embedding API key, unless the embedding provider can use the same credential Pi already uses for the active model.
- An embedding base URL when the provider is not OpenAI's default API.

Then start Pi or the MCP server from that shell:

```bash
pi
# or
uv run --project /path/to/memora-wrapper python /path/to/memora-wrapper/src/memora_mcp.py
```

After Pi starts, run:

```text
/memora setup
/memora status
```

## Provider Setup

Memora's chat/extraction calls use Pi's active OpenAI-compatible model and Pi's resolved model auth. OpenAI uses native structured parsing; DeepSeek and other compatible providers use JSON mode with schema validation. Only configure embeddings here.

OpenAI:

```bash
export PI_MEMORA_EMBEDDING_MODEL=text-embedding-3-small
```

OpenRouter:

```bash
export PI_MEMORA_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
export PI_MEMORA_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
export PI_MEMORA_EMBEDDING_API_KEY=...
```

If the embedding provider is different from Pi's active model provider, set that provider's embedding API key with `PI_MEMORA_EMBEDDING_API_KEY`.

Azure OpenAI:

```bash
export OPENAI_API_TYPE=azure
export AZURE_OPENAI_ENDPOINT=...
export AZURE_OPENAI_API_VERSION=2024-12-01-preview
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

## Pi Usage

```text
/memora status
/memora setup
/memora remember The project uses ChromaDB for local vector storage.
/memora recall repository architecture decisions
/memora list 10
/memora clear clear
```

The model may also call `memora_remember`, `memora_recall`, and `memora_list` directly.

## Configuration

Package-specific environment variables:

- `PI_MEMORA_HOME`: memory data root. Defaults to `${XDG_DATA_HOME:-$HOME/.local/share}/memora-wrapper`.
- `PI_MEMORA_SCOPE`: `project` or `global`. Defaults to `project`.
- `PI_MEMORA_AUTORECALL`: set to `0` to disable automatic recall.
- `PI_MEMORA_AUTOCAPTURE`: set to `0` to disable automatic capture.
- `PI_MEMORA_TOP_K`: recall count. Defaults to `5`.
- `PI_MEMORA_EMBEDDING_MODEL`: embedding model. Defaults to `text-embedding-3-small`.
- `PI_MEMORA_EMBEDDING_BASE_URL`: OpenAI-compatible embeddings base URL.
- `PI_MEMORA_EMBEDDING_API_KEY`: embeddings API key.

Provider-native variables such as `AZURE_OPENAI_ENDPOINT` are still used for provider-specific embedding configuration.

## Data And Safety

- Memory data is stored under `PI_MEMORA_HOME`.
- Memora source is vendored under `vendor/Memora` inside the installed package.
- The extension does not read env files or write shell configuration.
- Rotate any API key pasted into chat, logs, issue trackers, or support requests.
- Disable autocapture with `PI_MEMORA_AUTOCAPTURE=0` when working with secrets or private data.
- If you change embedding models, clear or rebuild the existing collection first. Vector dimensions may differ.
