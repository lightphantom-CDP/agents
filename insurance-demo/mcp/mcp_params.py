"""MCP connection params for local agents (OpenAI Agents SDK, Cursor, etc.)."""

from __future__ import annotations

import os
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent

leon_hospital_notify_mcp = {
    "command": "python",
    "args": [str(MCP_DIR / "notify_server.py")],
    "env": {
        "NTFY_TOPIC": os.getenv("NTFY_TOPIC", "leon-hospital-claims"),
        "NTFY_SERVER": os.getenv("NTFY_SERVER", "https://ntfy.sh"),
        "SLACK_WEBHOOK_URL": os.getenv("SLACK_WEBHOOK_URL", ""),
        "HOSPITAL_NAME": os.getenv("HOSPITAL_NAME", "Leon Hospital"),
    },
}

insurance_demo_mcp_servers = [
    leon_hospital_notify_mcp,
]
