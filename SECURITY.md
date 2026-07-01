# Security

Report security issues privately to the package maintainer.

## API Keys

Never paste API keys into chat, issue trackers, or logs. If a key is exposed, revoke or rotate it immediately.

`memora-wrapper` reads credentials from the process environment passed to Pi or the MCP server. It does not intentionally print secrets, but provider errors can contain account metadata.

## Data Stored

Memora stores extracted memories under `${XDG_DATA_HOME:-$HOME/.local/share}/memora-wrapper` by default. Autocapture may persist information from user prompts, assistant messages, and tool results. Disable it for sensitive work:

```bash
export PI_MEMORA_AUTOCAPTURE=0
```

## Execution

Pi extensions and this package's Python bridge run with your local user permissions. Review the source and only install packages you trust.
