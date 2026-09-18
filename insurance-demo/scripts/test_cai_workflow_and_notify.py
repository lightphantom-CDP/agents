#!/usr/bin/env python3
"""
CAI session smoke tests — workflow API + ntfy notification.

Usage (notebook or terminal in CAI project):

  export WORKFLOW_APP_URL="https://workflow-....cloudera.site"
  export CDSW_API_KEY="your-full-api-key"
  export NTFY_TOPIC="leon-hospital-claims"
  export HOSPITAL_NAME="Leon Hospital"

  python scripts/test_cai_workflow_and_notify.py
  python scripts/test_cai_workflow_and_notify.py --claim CLM-50001
  python scripts/test_cai_workflow_and_notify.py --notify-only
  python scripts/test_cai_workflow_and_notify.py --all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
NOTIFY_TOOL_DIR = ROOT / "agent" / "tools" / "notify_manual_review"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def test_ntfy_direct() -> bool:
    """POST directly to ntfy.sh — proves phone channel works."""
    topic = _env("NTFY_TOPIC", "leon-hospital-claims")
    hospital = _env("HOSPITAL_NAME", "Leon Hospital")
    server = _env("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    if not topic:
        print("SKIP ntfy direct: NTFY_TOPIC not set")
        return False

    url = f"{server}/{topic}"
    message = "CAI test — manual review channel OK"
    title = f"{hospital} — test"
    print(f"\n=== 1) Direct ntfy POST → {url} ===")
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={"Title": title[:250], "Priority": "high", "Tags": "hospital,claim"},
        timeout=20,
    )
    print(f"status: {resp.status_code}")
    if resp.ok:
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text[:300])
        print("OK — check phone for push")
        return True
    print("FAIL —", resp.text[:300])
    return False


def test_notify_tool(claim_id: str = "CLM-50001") -> bool:
    """Run notify_manual_review Python tool (no Agent Studio)."""
    topic = _env("NTFY_TOPIC", "leon-hospital-claims")
    hospital = _env("HOSPITAL_NAME", "Leon Hospital")
    if not topic:
        print("SKIP notify tool: NTFY_TOPIC not set")
        return False

    os.environ["NTFY_TOPIC"] = topic
    os.environ["HOSPITAL_NAME"] = hospital

    candidates = [
        NOTIFY_TOOL_DIR,
        Path("/home/cdsw/mcp"),
        Path(f"/home/cdsw/{_env('CDSW_PROJECT')}/agent/tools/notify_manual_review"),
        Path(f"/home/cdsw/{_env('CDSW_PROJECT')}/mcp"),
    ]
    tool_dir = next((p for p in candidates if (p / "tool.py").is_file()), None)
    if tool_dir is None:
        print("SKIP notify tool: tool.py not found. Upload agent/tools/notify_manual_review/")
        return False

    sys.path.insert(0, str(tool_dir))
    print(f"\n=== 2) notify_manual_review tool ({tool_dir}) ===")
    from tool import ToolParameters, UserParameters, run_tool  # type: ignore

    result = run_tool(
        UserParameters(ntfy_topic=topic, hospital_name=hospital),
        ToolParameters(
            claim_id=claim_id,
            reason="CAI script test — insurer manual review queue",
        ),
    )
    print(json.dumps(result, indent=2, default=str))
    ok = bool(result.get("notified")) and not result.get("dry_run")
    print("OK — notified" if ok else "WARN — check dry_run/error above")
    return ok


def kickoff_and_poll(claim_id: str, poll_timeout: int = 300) -> dict[str, Any]:
    """Kickoff deployed workflow and poll until complete or timeout."""
    app_url = _env("WORKFLOW_APP_URL")
    api_key = _env("CDSW_API_KEY") or _env("CDSW_APIV2_KEY")
    if not app_url or not api_key:
        return {
            "error": "Set WORKFLOW_APP_URL and CDSW_API_KEY in environment",
        }

    prompt = (
        f"Review claim {claim_id}. "
        "Look up claim facts and policy. "
        "Recommend Approved, Partial approval, Rejected, or Manual review."
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    ev_headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    print(f"\n=== 3) Workflow kickoff ({claim_id}) ===")
    print(f"URL: {app_url}")
    kick = requests.post(
        f"{app_url.rstrip('/')}/api/workflow/kickoff",
        json={"inputs": {"user_input": prompt, "context": ""}},
        headers=headers,
        timeout=60,
    )
    print(f"kickoff status: {kick.status_code}")
    if not kick.ok:
        return {"error": kick.text[:500]}

    body = kick.json()
    trace_id = body.get("response", {}).get("trace_id") or body.get("trace_id")
    if not trace_id:
        return {"error": f"No trace_id: {body}"}
    print(f"trace_id: {trace_id}")

    deadline = time.time() + poll_timeout
    last_events: list[Any] = []
    while time.time() < deadline:
        ev = requests.get(
            f"{app_url.rstrip('/')}/api/workflow/events",
            params={"trace_id": trace_id},
            headers=ev_headers,
            timeout=60,
        )
        payload = ev.json()
        if isinstance(payload, dict):
            for key in ("events", "response", "data"):
                if isinstance(payload.get(key), list):
                    last_events = payload[key]
                    break
        elif isinstance(payload, list):
            last_events = payload

        for event in reversed(last_events):
            if not isinstance(event, dict):
                continue
            etype = str(event.get("type", ""))
            attrs = event.get("attributes") or {}
            if "complete" in etype.lower() or (
                "kickoff" in etype.lower() and "complete" in etype.lower()
            ):
                output = None
                for key in ("output", "result", "raw", "content", "text"):
                    if isinstance(attrs, dict) and attrs.get(key):
                        output = attrs[key]
                        break
                    if event.get(key):
                        output = event[key]
                        break
                return {
                    "status": "complete",
                    "trace_id": trace_id,
                    "output": output,
                    "event_type": etype,
                }

        print(f"  polling... ({len(last_events)} events)")
        time.sleep(3)

    return {
        "status": "timeout",
        "trace_id": trace_id,
        "last_events": last_events[-3:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CAI workflow + ntfy smoke tests")
    parser.add_argument("--claim", default="CLM-50005", help="Claim ID for workflow test")
    parser.add_argument("--notify-only", action="store_true", help="Only ntfy + notify tool")
    parser.add_argument("--all", action="store_true", help="Run all tests including CLM-50001")
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()

    print("CAI smoke test")
    print("NTFY_TOPIC:", _env("NTFY_TOPIC", "(not set)"))
    print("WORKFLOW_APP_URL:", _env("WORKFLOW_APP_URL", "(not set)"))

    ok_ntfy = test_ntfy_direct()
    ok_tool = test_notify_tool("CLM-50001")

    if args.notify_only:
        return 0 if (ok_ntfy or ok_tool) else 1

    result = kickoff_and_poll(args.claim, poll_timeout=args.poll_timeout)
    print("\n--- Workflow result ---")
    print(json.dumps(result, indent=2, default=str)[:4000])

    if args.all:
        print("\n--- Manual review claim ---")
        r2 = kickoff_and_poll("CLM-50001", poll_timeout=args.poll_timeout)
        print(json.dumps(r2, indent=2, default=str)[:4000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
