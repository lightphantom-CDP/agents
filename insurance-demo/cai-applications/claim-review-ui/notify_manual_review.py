"""
Manual-review notifications via **MCP server** (leon_hospital_notify).

Set USE_MCP_NOTIFY=true (default) to call notify_server.py over stdio.
Falls back to direct ntfy/Slack HTTP if MCP is unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

USE_MCP = os.getenv("USE_MCP_NOTIFY", "false").strip().lower() in ("1", "true", "yes", "on")


def _mcp_paths() -> list[Path]:
    project = os.getenv("CDSW_PROJECT", "").strip()
    return [
        Path(__file__).resolve().parent.parent.parent / "mcp",
        Path(f"/home/cdsw/{project}/mcp") if project else Path("/dev/null"),
        Path("/home/cdsw/insuranceclaim/mcp"),
        Path.cwd() / "mcp",
    ]


def _ensure_mcp_on_path() -> bool:
    for base in _mcp_paths():
        if (base / "mcp_client.py").is_file():
            root = str(base)
            if root not in sys.path:
                sys.path.insert(0, root)
            return True
    return False


def is_manual_review_text(text: str) -> bool:
    lower = (text or "").lower()
    return any(
        m in lower
        for m in (
            "manual review",
            "manual_review",
            "route to clinical review",
            "escalate to a human",
            "escalate to human",
            "senior adjuster",
            "clinical specialist",
        )
    )


def notifications_enabled() -> bool:
    mode = os.getenv("NOTIFY_ENABLED", "true").strip().lower()
    if mode in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("NTFY_TOPIC", "").strip() or os.getenv("SLACK_WEBHOOK_URL", "").strip())


def notify_manual_review(
    claim_id: str,
    reason: str,
    *,
    trace_id: str = "",
    hospital: str | None = None,
) -> dict[str, Any]:
    if USE_MCP and _ensure_mcp_on_path():
        try:
            from mcp_client import notify_via_mcp  # type: ignore

            result = notify_via_mcp(claim_id, reason, trace_id)
            result["via"] = "mcp:leon_hospital_notify"
            return result
        except Exception as exc:
            return {
                "error": f"MCP notify failed: {exc}",
                "hint": "Upload insurance-demo/mcp/ to CAI project and pip install mcp",
                "via": "mcp:leon_hospital_notify",
            }

    return _notify_direct(claim_id, reason, trace_id=trace_id, hospital=hospital)


def _notify_direct(
    claim_id: str,
    reason: str,
    *,
    trace_id: str = "",
    hospital: str | None = None,
) -> dict[str, Any]:
    import uuid

    import requests

    claim_id = (claim_id or "UNKNOWN").strip().upper()
    hospital_name = (hospital or os.getenv("HOSPITAL_NAME", "Leon Hospital")).strip()
    ticket_id = f"MR-{claim_id}-{uuid.uuid4().hex[:6].upper()}"
    lines = [
        "Manual review required",
        f"Ticket: {ticket_id}",
        f"Claim: {claim_id}",
        f"Reason: {(reason or 'Manual review required').strip()}",
        f"Hospital: {hospital_name}",
    ]
    if trace_id:
        lines.append(f"Trace: {trace_id}")
    message = "\n".join(lines)
    title = f"{hospital_name} - {claim_id} needs review"
    channels: list[dict[str, Any]] = []

    topic = os.getenv("NTFY_TOPIC", "").strip()
    if topic:
        server = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        resp = requests.post(
            f"{server}/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("ascii", "replace").decode("ascii")[:250],
                "Priority": "high",
            },
            timeout=20,
        )
        channels.append({"channel": "ntfy", "ok": resp.ok})

    slack = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if slack:
        resp = requests.post(slack, json={"text": message}, timeout=20)
        channels.append({"channel": "slack", "ok": resp.ok})

    out: dict[str, Any] = {
        "ticket_id": ticket_id,
        "claim_id": claim_id,
        "notified": bool(channels) and all(c.get("ok") for c in channels),
        "channels": channels,
        "via": "direct:http",
    }
    if not channels:
        out["dry_run"] = True
        out["preview"] = message
        out["hint"] = "Set NTFY_TOPIC or enable MCP (upload mcp/ folder + pip install mcp)."
    return out
