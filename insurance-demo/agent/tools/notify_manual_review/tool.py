"""
Agent Studio Tool — ntfy push when a claim needs human manual review.

No MCP required. Set NTFY_TOPIC on the project or in tool user config.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, Field, field_validator

OUTPUT_KEY = "tool_output"
DEFAULT_HOSPITAL = "Leon Hospital"


def _ascii_header(value: str) -> str:
    """ntfy Title header must be ASCII-safe (no em dash / unicode)."""
    return (
        value.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .encode("ascii", "replace")
        .decode("ascii")
    )


def _embedded_notify(
    claim_id: str,
    reason: str,
    *,
    trace_id: str = "",
    hospital: str | None = None,
) -> dict[str, Any]:
    """Self-contained ntfy/Slack push — no external notify_lib.py needed.

    Agent Studio's Tools Catalog often keeps only tool.py + requirements.txt,
    so the notify logic is embedded here to survive redeploys.
    """
    claim_id = (claim_id or "UNKNOWN").strip().upper()
    reason = (reason or "Manual review required").strip()
    hospital_name = (hospital or os.getenv("HOSPITAL_NAME", DEFAULT_HOSPITAL)).strip()
    ticket_id = f"MR-{claim_id}-{uuid.uuid4().hex[:6].upper()}"

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
        server = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        resp = requests.post(
            f"{server}/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": _ascii_header(title)[:250],
                "Priority": "high",
                "Tags": "hospital,claim",
            },
            timeout=20,
        )
        channels.append(
            {"channel": "ntfy", "ok": resp.ok, "status_code": resp.status_code, "topic": topic}
        )

    slack = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if slack:
        resp = requests.post(slack, json={"text": message}, timeout=20)
        channels.append({"channel": "slack", "ok": resp.ok, "status_code": resp.status_code})

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
            "or SLACK_WEBHOOK_URL on the workflow application, then restart."
        )
    elif not result["notified"]:
        result["error"] = "One or more notification channels failed"
    return result

def _tool_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        pass
    project = os.environ.get("CDSW_PROJECT", "").strip()
    candidates = [
        Path("/tool"),
        Path.cwd(),
        Path.cwd() / "notify_manual_review",
    ]
    if project:
        candidates.append(Path(f"/home/cdsw/{project}/agent/tools/notify_manual_review"))
    for path in candidates:
        if path.is_dir():
            return path
    return Path("/tool")


class UserParameters(BaseModel):
    ntfy_topic: str = Field(
        default="",
        description="ntfy.sh topic, e.g. leon-hospital-claims (or set NTFY_TOPIC env var)",
    )
    hospital_name: str = Field(
        default="Leon Hospital",
        description="Hospital name shown in the push notification title",
    )
    ntfy_server: str = Field(
        default="https://ntfy.sh",
        description="ntfy server base URL (default https://ntfy.sh)",
    )


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim ID, e.g. CLM-50001")
    reason: str = Field(description="One-line manual review reason (no PII)")
    trace_id: str = Field(default="", description="Optional workflow trace ID")

    @field_validator("claim_id", mode="before")
    @classmethod
    def normalize_claim_id(cls, value: Any) -> str:
        return str(value or "").strip().upper()


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    claim_id = args.claim_id
    if not claim_id.startswith("CLM-"):
        return {"error": f"Invalid claim_id: {claim_id}"}

    topic = (config.ntfy_topic or os.getenv("NTFY_TOPIC", "")).strip()
    if topic:
        os.environ["NTFY_TOPIC"] = topic
    if config.ntfy_server:
        os.environ["NTFY_SERVER"] = config.ntfy_server.strip()
    if config.hospital_name:
        os.environ["HOSPITAL_NAME"] = config.hospital_name.strip()

    try:
        result = _embedded_notify(
            claim_id,
            args.reason,
            trace_id=args.trace_id,
            hospital=config.hospital_name or None,
        )
        result["via"] = "python:notify_manual_review"
        return result
    except Exception as exc:
        return {"error": f"Notification failed: {exc}", "via": "python:notify_manual_review"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True)
    parser.add_argument("--tool-params", required=True)
    cli_args = parser.parse_args()

    user_config = UserParameters(**json.loads(cli_args.user_params))
    tool_args = ToolParameters(**json.loads(cli_args.tool_params))
    result = run_tool(user_config, tool_args)
    print(OUTPUT_KEY, json.dumps(result, indent=2, default=str))
