"""
MCP stdio client — call leon_hospital_notify MCP server from Flask or Agent Studio tools.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

MCP_DIR = Path(__file__).resolve().parent


def _server_params() -> StdioServerParameters:
    python = sys.executable
    return StdioServerParameters(
        command=python,
        args=[str(MCP_DIR / "notify_server.py")],
        env={
            **os.environ,
            "NTFY_TOPIC": os.getenv("NTFY_TOPIC", ""),
            "NTFY_SERVER": os.getenv("NTFY_SERVER", "https://ntfy.sh"),
            "SLACK_WEBHOOK_URL": os.getenv("SLACK_WEBHOOK_URL", ""),
            "HOSPITAL_NAME": os.getenv("HOSPITAL_NAME", "Leon Hospital"),
        },
    )


async def call_notify_manual_review_ticket(
    claim_id: str,
    reason: str,
    trace_id: str = "",
) -> dict[str, Any]:
    """Invoke MCP tool notify_manual_review_ticket on the local notify_server."""
    params = _server_params()
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            payload = {
                "claim_id": claim_id,
                "reason": reason,
                "trace_id": trace_id,
            }
            result = await session.call_tool("notify_manual_review_ticket", payload)
            text = ""
            if result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        text += block.text
            if not text:
                return {"error": "empty MCP response", "raw": str(result)}
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"result": text}


def notify_via_mcp(claim_id: str, reason: str, trace_id: str = "") -> dict[str, Any]:
    """Sync wrapper for Flask / Agent Studio tool."""
    return asyncio.run(call_notify_manual_review_ticket(claim_id, reason, trace_id))


async def list_notify_tools() -> list[str]:
    params = _server_params()
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools.tools]
