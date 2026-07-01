# pi-memora

Memora-backed persistent memory for the Pi coding agent.

`pi-memora` connects Pi extensions to Microsoft Memora through a small uv-backed Python bridge. It can recall relevant memories before a prompt, capture completed turns after the agent finishes, and expose explicit memory tools to the model.

## Features

- Automatic recall before each user prompt.
- Automatic capture after each agent turn.
- Explicit tools: `memora_remember`, `memora_recall`, `memora_list`.
- Slash command: `/memora`.
- uv project for bridge dependencies.
- OpenAI, Azure OpenAI, and OpenAI-compatible providers such as OpenRouter.
- Project-scoped memory by default, with optional global scope.

## Install

```bash
pi install npm:pi-memora
```

Project-local install:

```bash
pi install npm:pi-memora -l
```

Local checkout install:

```bash
pi install /path/to/pi-memora
```

One-session published package trial:

```bash
pi -e npm:pi-memora
```

Local development:

```bash
pi -e /path/to/pi-memora/extensions/memora.ts
```

If Pi is already running after installation, run `/reload` or start a new Pi session.

## Memora Runtime

Memora currently ships as source, so the bridge needs a local Memora checkout. The checkout is pinned to the commit tested by this package and fetched shallowly.

```bash
MEMORA_HOME=${PI_MEMORA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/pi-memora}
MEMORA_REPO=$MEMORA_HOME/Memora
mkdir -p "$MEMORA_HOME"
git init "$MEMORA_REPO"
git -C "$MEMORA_REPO" remote add origin https://github.com/microsoft/Memora.git
git -C "$MEMORA_REPO" fetch --depth 1 origin dec3f8f2444eace7004fc084abe1be9f3d88270e
git -C "$MEMORA_REPO" checkout --detach FETCH_HEAD
```

The bridge itself is a uv project. Its minimal Python dependencies are declared in this package's `pyproject.toml`; it does not install Memora's full benchmark/RL/local-HF dependency set.

## Provider Setup

Set provider settings in the environment before launching Pi.

### OpenAI

```bash
export OPENAI_API_TYPE=openai
export OPENAI_API_KEY=...
export PI_MEMORA_MODEL=gpt-4.1-mini
export PI_MEMORA_EMBEDDING_MODEL=text-embedding-3-small
```

### OpenRouter

```bash
export OPENAI_API_TYPE=openai
export OPENROUTER_API_KEY=...
export PI_MEMORA_LLM_BASE_URL=https://openrouter.ai/api/v1
export PI_MEMORA_MODEL=deepseek/deepseek-v4-pro
export PI_MEMORA_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
export PI_MEMORA_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
```

### Azure OpenAI

```bash
export OPENAI_API_TYPE=azure
export AZURE_OPENAI_ENDPOINT=...
export AZURE_OPENAI_API_VERSION=2024-12-01-preview
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

## Usage

```text
/memora status
/memora setup
/memora recall repository architecture decisions
/memora remember The project uses ChromaDB for local vector storage.
/memora list 10
/memora clear clear
```

The model can call:

- `memora_remember`: store durable facts, decisions, preferences, procedures, and task outcomes.
- `memora_recall`: retrieve relevant memories.
- `memora_list`: list recent memories.

## Configuration

Keep the environment surface small:

- `PI_MEMORA_HOME`: optional storage root. Defaults to `${XDG_DATA_HOME:-$HOME/.local/share}/pi-memora`.
- `PI_MEMORA_SCOPE`: optional memory scope, `project` or `global`. Defaults to `project`.
- `PI_MEMORA_AUTORECALL`: set to `0` to disable automatic recall.
- `PI_MEMORA_AUTOCAPTURE`: set to `0` to disable automatic capture.
- `PI_MEMORA_TOP_K`: optional recall count. Defaults to `5`.
- `PI_MEMORA_MODEL`: chat model used by Memora extraction and update calls.
- `PI_MEMORA_LLM_BASE_URL`: optional OpenAI-compatible chat base URL.
- `PI_MEMORA_LLM_API_KEY`: optional chat API key. Falls back to `OPENAI_API_KEY` or `OPENROUTER_API_KEY`.
- `PI_MEMORA_EMBEDDING_MODEL`: embedding model. Defaults to `text-embedding-3-small`.
- `PI_MEMORA_EMBEDDING_BASE_URL`: optional OpenAI-compatible embeddings base URL.
- `PI_MEMORA_EMBEDDING_API_KEY`: optional embeddings API key. Falls back to `OPENAI_EMBEDDING_API_KEY`, `OPENROUTER_API_KEY`, or `OPENAI_API_KEY`.

OpenAI/Azure/OpenRouter variables are provider variables, not package-specific config.

## Operational Notes

- Rotate any API key pasted into chat, logs, issue trackers, or support requests.
- If you change embedding models for an existing collection, clear or rebuild that collection first. Vector dimensions can differ between models.
- Autocapture can store sensitive conversation details. Disable with `PI_MEMORA_AUTOCAPTURE=0` when working with secrets or private data.
- This package executes a Python bridge with your user permissions. Review source before installing third-party Pi packages.
- `pi-memora` does not write into Pi's own package/config directories.

## Development

```bash
npm install
uv lock
npm test
npm pack --dry-run
```

Live OpenRouter smoke test:

```bash
export OPENAI_API_TYPE=openai
export PI_MEMORA_LLM_BASE_URL=https://openrouter.ai/api/v1
export PI_MEMORA_MODEL=deepseek/deepseek-v4-pro
export PI_MEMORA_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
export PI_MEMORA_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

pi -e ./extensions/memora.ts --no-builtin-tools --tools memora_recall -p "Use memora_recall to summarize pi-memora smoke test memory."
```
