#!/usr/bin/env python3
"""Compatibility wrapper that routes legacy JSON CLI actions through MCP tools."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ACTION_TO_TOOL = {
    "doctor": "memora_status",
    "missing-setup": "memora_setup_instructions",
    "add": "memora_remember",
    "query": "memora_recall",
    "list": "memora_list",
    "delete": "memora_delete",
    "clear": "memora_clear",
}


def _payload() -> str:
    if len(sys.argv) >= 3:
        return sys.argv[2]
    return sys.stdin.read() or "{}"


def main() -> None:
    action = sys.argv[1] if len(sys.argv) >= 2 else "doctor"
    tool_name = ACTION_TO_TOOL.get(action)
    if not tool_name:
        print(json.dumps({"ok": False, "error": f"Unknown action: {action}"}))
        raise SystemExit(1)

    project_root = Path(__file__).resolve().parent.parent
    caller = project_root / "src" / "memora_mcp_call.py"
    completed = subprocess.run(
        ["uv", "run", "--project", str(project_root), "python", str(caller), tool_name, _payload()],
        cwd=project_root,
        text=True,
        check=False,
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
