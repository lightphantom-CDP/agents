#!/usr/bin/env python3
"""
Diagnose UI hallucination — call the SAME workflow API the claim-review-ui uses.

Compares workflow output to expected demo claim facts. Run in CAI notebook or terminal.

  export WORKFLOW_APP_URL="https://workflow-....cloudera.site"
  export CDSW_API_KEY="your-full-api-key"

  python scripts/test_ui_workflow_response.py
  python scripts/test_ui_workflow_response.py --claim CLM-50005
  python scripts/test_ui_workflow_response.py --message "Review claim CLM-50021"
  python scripts/test_ui_workflow_response.py --all-demo-claims
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any

import requests

# Expected demo facts (from demo_claims.json / workshop script)
DEMO_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "CLM-50005": {
        "outcome": "approved",
        "amount": 337.39,
        "must_not_contain": ["john doe", "manual review", "upcoding", "250.00", "250"],
    },
    "CLM-50021": {
        "outcome": "rejected",
        "amount": 4843.14,
        "must_contain_any": ["reject", "denied", "denial"],
        "must_not_contain": ["john doe", "approved"],
    },
    "CLM-50003": {
        "outcome": "partial",
        "must_contain_any": ["partial"],
    },
    "CLM-50001": {
        "outcome": "manual_review",
        "must_contain_any": ["manual review", "clinical"],
    },
}

HALLUCINATION_MARKERS = [
    "john doe",
    "jane doe",
    "pt-8829",
    "pr-1002",
    "general hospital",
    "acute sinusitis",
    "j01.90",
    "99214",
    "upcoding",
    "financial discrepancies",
]

CLAIM_RE = re.compile(r"CLM-\d{5}", re.I)


def build_prompt(claim_id: str) -> str:
    """Same prompt shape as claim-review-ui app.py build_prompt()."""
    return (
        f"Please review hospital insurance claim {claim_id} and recommend "
        "Approved, Partial approval, Rejected, or Manual review. "
        "Look up the claim facts and check MediShield policy rules. "
        "Explain your decision in plain English for a claims adjuster, "
        "cite relevant policy sections, and suggest the next step."
    )


def resolve_message(payload: dict) -> tuple[str, str | None]:
    """Same logic as claim-review-ui resolve_chat_message (simplified)."""
    message = (payload.get("message") or "").strip()
    claim_id = (payload.get("claim_id") or "").strip().upper() or None

    if message:
        m = CLAIM_RE.search(message)
        return message, (m.group(0).upper() if m else None)

    if claim_id:
        return build_prompt(claim_id), claim_id

    raise ValueError("message or claim_id required")


def normalize_events(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict):
        for key in ("events", "response", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [e for e in nested if isinstance(e, dict)]
    return []


def extract_output(events: list[dict]) -> str | None:
    complete_types = (
        "crew.complete",
        "crew_kickoff_completed",
        "crew_kickoff_complete",
        "crewkickoffcompletedevent",
    )
    for event in reversed(events):
        etype = str(event.get("type", "")).lower()
        attrs = event.get("attributes") or {}
        if not isinstance(attrs, dict):
            attrs = {}
        if etype in complete_types or ("kickoff" in etype and "complete" in etype):
            for key in ("output", "result", "raw", "content", "text"):
                val = attrs.get(key) if isinstance(attrs, dict) else None
                if val not in (None, ""):
                    return str(val)
                if event.get(key) not in (None, ""):
                    return str(event[key])
    return None


def kickoff_and_poll(
    app_url: str,
    api_key: str,
    inputs: dict,
    poll_timeout: int = 300,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    ev_headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    base = app_url.rstrip("/")

    kick = requests.post(
        f"{base}/api/workflow/kickoff",
        json={"inputs": inputs},
        headers=headers,
        timeout=60,
    )
    if not kick.ok:
        return {"status": "error", "http_status": kick.status_code, "body": kick.text[:800]}

    body = kick.json()
    trace_id = body.get("response", {}).get("trace_id") or body.get("trace_id")
    if not trace_id:
        return {"status": "error", "error": "no trace_id", "body": body}

    deadline = time.time() + poll_timeout
    last_events: list[dict] = []
    while time.time() < deadline:
        ev = requests.get(
            f"{base}/api/workflow/events",
            params={"trace_id": trace_id},
            headers=ev_headers,
            timeout=60,
        )
        last_events = normalize_events(ev.json())
        output = extract_output(last_events)
        if output is not None:
            return {
                "status": "complete",
                "trace_id": trace_id,
                "output": output,
                "event_count": len(last_events),
            }
        time.sleep(2)

    return {
        "status": "timeout",
        "trace_id": trace_id,
        "event_count": len(last_events),
        "last_event_types": [e.get("type") for e in last_events[-5:]],
    }


def check_hallucination(claim_id: str | None, text: str) -> list[str]:
    """Return list of warning strings."""
    warnings: list[str] = []
    lower = (text or "").lower()

    for marker in HALLUCINATION_MARKERS:
        if marker in lower:
            warnings.append(f"HALLUCINATION_MARKER: '{marker}' found in output")

    if claim_id and claim_id in DEMO_EXPECTATIONS:
        exp = DEMO_EXPECTATIONS[claim_id]
        if "amount" in exp:
            amt = exp["amount"]
            amt_str = f"{amt:.2f}"
            if amt_str not in text and str(int(amt)) not in text:
                warnings.append(
                    f"AMOUNT_MISMATCH: expected ~${amt_str} for {claim_id} in output"
                )
        for bad in exp.get("must_not_contain", []):
            if bad.lower() in lower:
                warnings.append(f"UNEXPECTED_TEXT: '{bad}' for {claim_id}")
        must_any = exp.get("must_contain_any", [])
        if must_any and not any(m in lower for m in must_any):
            warnings.append(f"OUTCOME_MISMATCH: expected one of {must_any}")

    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        warnings.append("PII_SSN_PATTERN in output")

    if "patient" in lower and ("john" in lower or "jane" in lower):
        warnings.append("INVENTED_PATIENT_NAME suspected")

    return warnings


def run_ui_style_test(
    app_url: str,
    api_key: str,
    *,
    message: str | None = None,
    claim_id: str | None = None,
    poll_timeout: int = 300,
) -> dict[str, Any]:
    """Mimic claim-review-ui POST /api/chat payload → workflow kickoff."""
    payload: dict[str, str] = {}
    if message:
        payload["message"] = message
    if claim_id:
        payload["claim_id"] = claim_id

    prompt, resolved_claim = resolve_message(payload)
    inputs = {"user_input": prompt, "context": ""}

    print("\n" + "=" * 60)
    print(f"CLAIM: {resolved_claim or '(from message)'}")
    print(f"PROMPT SENT TO WORKFLOW:\n{prompt[:500]}")
    print("=" * 60)

    result = kickoff_and_poll(app_url, api_key, inputs, poll_timeout=poll_timeout)
    result["claim_id"] = resolved_claim
    result["prompt"] = prompt

    if result.get("status") == "complete":
        output = str(result.get("output", ""))
        warnings = check_hallucination(resolved_claim, output)
        result["hallucination_warnings"] = warnings
        result["verdict"] = "PASS" if not warnings else "FAIL (possible hallucination)"
        print(f"\nSTATUS: {result['status']}")
        print(f"TRACE:  {result.get('trace_id')}")
        print(f"VERDICT: {result['verdict']}")
        if warnings:
            print("\nWARNINGS:")
            for w in warnings:
                print(f"  - {w}")
        print("\n--- OUTPUT (first 2500 chars) ---")
        print(output[:2500])
    else:
        print(f"\nSTATUS: {result.get('status')}")
        print(json.dumps(result, indent=2, default=str)[:2000])

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Test workflow response like claim-review-ui")
    parser.add_argument("--claim", help="Test via claim_id (UI sidebar style)")
    parser.add_argument("--message", help='Test via message (UI chat style), e.g. "Review claim CLM-50005"')
    parser.add_argument("--all-demo-claims", action="store_true")
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()

    app_url = os.getenv("WORKFLOW_APP_URL", "").strip()
    api_key = os.getenv("CDSW_API_KEY", "").strip() or os.getenv("CDSW_APIV2_KEY", "").strip()
    if not app_url or not api_key:
        print("ERROR: Set WORKFLOW_APP_URL and CDSW_API_KEY")
        print("  export WORKFLOW_APP_URL=https://workflow-....cloudera.site")
        print("  export CDSW_API_KEY=your-full-secret")
        return 1

    print("WORKFLOW_APP_URL:", app_url)
    print("API key length:", len(api_key))

    results: list[dict] = []

    if args.all_demo_claims:
        for cid in ("CLM-50005", "CLM-50021", "CLM-50003", "CLM-50001"):
            results.append(
                run_ui_style_test(app_url, api_key, message=f"Review claim {cid}", poll_timeout=args.poll_timeout)
            )
    elif args.message:
        results.append(run_ui_style_test(app_url, api_key, message=args.message, poll_timeout=args.poll_timeout))
    elif args.claim:
        results.append(run_ui_style_test(app_url, api_key, claim_id=args.claim.upper(), poll_timeout=args.poll_timeout))
    else:
        # Default: both styles for CLM-50005 (common hallucination case)
        results.append(run_ui_style_test(app_url, api_key, claim_id="CLM-50005", poll_timeout=args.poll_timeout))
        results.append(
            run_ui_style_test(
                app_url, api_key, message="Please review hospital insurance claim CLM-50005",
                poll_timeout=args.poll_timeout,
            )
        )

    fails = sum(1 for r in results if r.get("verdict", "").startswith("FAIL"))
    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(results)} run(s), {fails} failed hallucination checks")
    if fails and results[0].get("status") == "complete":
        print("\nIf this script FAILs but Agent Studio TEST tab passes:")
        print("  1. WORKFLOW_APP_URL on claim-review-ui points to OLD deployment")
        print("  2. Redeploy workflow after agent changes")
        print("  3. Trino/tools fail in workflow pod (tools return error, model invents)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
