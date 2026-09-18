"""
Free notifications for manual-review claims (Leon Hospital demo).

Channels (set at least one):
  NTFY_TOPIC          — e.g. leon-hospital-claims (https://ntfy.sh, free)
  SLACK_WEBHOOK_URL   — optional Slack incoming webhook
  NTFY_SERVER         — default https://ntfy.sh (or self-hosted ntfy)
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import requests

DEFAULT_HOSPITAL = "Leon Hospital"


def _ascii_header(value: str) -> str:
    """ntfy Title header must be ASCII-safe for requests (no em dash / unicode)."""
    return (
        value.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .encode("ascii", "replace")
        .decode("ascii")
    )


def notifications_enabled() -> bool:
    mode = os.getenv("NOTIFY_ENABLED", "true").strip().lower()
    if mode in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("NTFY_TOPIC", "").strip() or os.getenv("SLACK_WEBHOOK_URL", "").strip())


def send_ntfy(topic: str, title: str, message: str, server: str | None = None) -> dict[str, Any]:
    base = (server or os.getenv("NTFY_SERVER", "https://ntfy.sh")).rstrip("/")
    url = f"{base}/{topic}"
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": _ascii_header(title)[:250],
            "Priority": "high",
            "Tags": "hospital,claim",
        },
        timeout=20,
    )
    return {"channel": "ntfy", "ok": resp.ok, "status_code": resp.status_code, "topic": topic}


def send_slack(webhook_url: str, text: str) -> dict[str, Any]:
    resp = requests.post(webhook_url, json={"text": text}, timeout=20)
    return {"channel": "slack", "ok": resp.ok, "status_code": resp.status_code}


def build_ticket_id(claim_id: str) -> str:
    return f"MR-{claim_id}-{uuid.uuid4().hex[:6].upper()}"


def notify_manual_review(
    claim_id: str,
    reason: str,
    *,
    trace_id: str = "",
    hospital: str | None = None,
) -> dict[str, Any]:
    """Send a manual-review ticket notification. No PII — claim ID and reason only."""
    claim_id = (claim_id or "UNKNOWN").strip().upper()
    reason = (reason or "Manual review required").strip()
    hospital_name = (hospital or os.getenv("HOSPITAL_NAME", DEFAULT_HOSPITAL)).strip()
    ticket_id = build_ticket_id(claim_id)

    lines = [
        "Manual review required",
        f"Ticket: {ticket_id}",
        f"Claim: {claim_id}",
        f"Reason: {reason}",
        f"Hospital: {hospital_name}",
    ]
    if trace_id:
        lines.append(f"Trace: {trace_id}")
    message = "\n".join(lines)
    title = f"{hospital_name} - {claim_id} needs review"

    channels: list[dict[str, Any]] = []
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if topic:
        channels.append(send_ntfy(topic, title, message))

    slack = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if slack:
        channels.append(send_slack(slack, message))

    result: dict[str, Any] = {
        "ticket_id": ticket_id,
        "claim_id": claim_id,
        "status": "open",
        "notified": bool(channels) and all(c.get("ok") for c in channels),
        "channels": channels,
    }

    if not channels:
        result["dry_run"] = True
        result["preview"] = message
        result["hint"] = (
            "No notification channel configured. Set NTFY_TOPIC (free at ntfy.sh) "
            "or SLACK_WEBHOOK_URL on the application, then restart."
        )
    elif not result["notified"]:
        result["error"] = "One or more notification channels failed"
        result["hint"] = "Check NTFY_TOPIC is subscribed in the ntfy app, or verify Slack webhook URL."

    return result
