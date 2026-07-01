#!/usr/bin/env python3
"""MCP server exposing Microsoft Memora as memory tools."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from memora_core import (
    clear_memories,
    delete_memory,
    list_memories,
    recall,
    remember,
    setup_instructions,
    status,
)


mcp = FastMCP(
    "memora-wrapper",
    instructions=(
        "Persistent memory backed by Microsoft Memora. "
        "Use memora_remember for durable facts and decisions, memora_recall for relevant context, "
        "and memora_list to inspect stored memories."
    ),
)


def _payload(cwd: str | None = None, metadata: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"cwd": cwd or os.getcwd()}
    if metadata:
        payload["metadata"] = metadata
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def _run_core(fn, *args, **kwargs) -> dict[str, Any]:
    # Memora and some dependencies print diagnostics; stdio MCP stdout is reserved for protocol frames.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            return fn(*args, **kwargs)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "setup": setup_instructions().get("setup", [])}


@mcp.tool()
def memora_status(cwd: str | None = None) -> dict[str, Any]:
    """Check whether Memora is importable and report the active memory scope."""
    return _run_core(status, _payload(cwd))


@mcp.tool()
def memora_setup_instructions() -> dict[str, Any]:
    """Return the commands needed to install the pinned Memora source checkout."""
    return _run_core(setup_instructions)


@mcp.tool()
def memora_remember(
    text: str,
    memory_type: str = "doc",
    cwd: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store durable facts, decisions, preferences, or task outcomes in Memora."""
    stripped = text.strip()
    if not stripped:
        return {"ok": False, "error": "No text provided."}
    return _run_core(remember, _payload(cwd, metadata, text=stripped, type=memory_type))


@mcp.tool()
def memora_recall(
    query: str,
    top_k: int = 5,
    strategy: str = "semantic",
    cwd: str | None = None,
) -> dict[str, Any]:
    """Recall memories relevant to a query."""
    stripped = query.strip()
    if not stripped:
        return {"ok": False, "error": "No query provided."}

    return _run_core(recall, _payload(cwd, query=stripped, top_k=top_k, strategy=strategy))


@mcp.tool()
def memora_list(limit: int = 20, cwd: str | None = None) -> dict[str, Any]:
    """List recent memories for the active scope."""
    return _run_core(list_memories, _payload(cwd, limit=limit))


@mcp.tool()
def memora_delete(key: str, cwd: str | None = None) -> dict[str, Any]:
    """Delete one memory by key or index."""
    stripped = key.strip()
    if not stripped:
        return {"ok": False, "error": "No key provided."}
    return _run_core(delete_memory, _payload(cwd, key=stripped))


@mcp.tool()
def memora_clear(confirm: str, cwd: str | None = None) -> dict[str, Any]:
    """Clear all memories in the active scope. Pass confirm='clear'."""
    return _run_core(clear_memories, _payload(cwd, confirm=confirm))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the memora-wrapper MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default=os.getenv("PI_MEMORA_MCP_TRANSPORT", "stdio"),
        help="MCP transport. Defaults to stdio.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run a local status check and exit.")
    args = parser.parse_args()

    if args.self_test:
        print(memora_status())
        return

    mcp.run(args.transport)


if __name__ == "__main__":
    main()
