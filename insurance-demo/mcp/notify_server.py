#!/usr/bin/env python3
"""
MCP server — free notifications when a claim needs human manual review.

Run:
  uv run notify_server.py
  # or: python notify_server.py

Env:
  NTFY_TOPIC=leon-hospital-claims
  SLACK_WEBHOOK_URL=   (optional)
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from notify_lib import notify_manual_review

mcp = FastMCP("leon_hospital_notify")


@mcp.tool()
def notify_manual_review_ticket(
    claim_id: str,
    reason: str,
    trace_id: str = "",
) -> str:
    """
    Open a manual-review ticket and send a free push notification (ntfy.sh / Slack).
    Call ONLY when the recommendation is manual review / human escalation.
    Do not call for approved, rejected, or partial approval.
    """
    result = notify_manual_review(claim_id, reason, trace_id=trace_id)
    return json.dumps(result, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
