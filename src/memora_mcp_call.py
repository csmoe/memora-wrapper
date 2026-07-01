#!/usr/bin/env python3
"""Call the memora-wrapper MCP server once and print the tool result as JSON."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _json_out(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(code)


def _read_payload() -> dict[str, Any]:
    if len(sys.argv) >= 3:
        raw = sys.argv[2]
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _decode_tool_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured

    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"ok": True, "text": text}

    return {"ok": False, "error": "MCP tool returned no structured content."}


async def _call_tool(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent
    server_path = project_root / "src" / "memora_mcp.py"
    params = StdioServerParameters(
        command="uv",
        args=["run", "--project", str(project_root), "python", str(server_path)],
        cwd=str(project_root),
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, payload)
            return _decode_tool_result(result)


def main() -> None:
    if len(sys.argv) < 2:
        _json_out({"ok": False, "error": "No MCP tool name provided."}, code=1)
    tool_name = sys.argv[1]
    try:
        result = asyncio.run(_call_tool(tool_name, _read_payload()))
        _json_out(result, code=0 if result.get("ok") else 1)
    except Exception as exc:
        _json_out({"ok": False, "error": str(exc)}, code=1)


if __name__ == "__main__":
    main()
