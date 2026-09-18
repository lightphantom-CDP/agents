#!/usr/bin/env python3
"""
CAI Application — MediShield Claim Review UI

Professional claim adjudication front-end for Agent Studio workflows.
Binds to $CDSW_APP_PORT (required for CAI Application health checks).

Env vars:
  WORKFLOW_APP_URL   — deployed Agent Studio workflow app base URL (from API docs sidebar)
  CDSW_API_KEY       — API key (User Settings → API Keys → Create API key)
  WORKFLOW_INPUT_KEY — chat input field (default: user_input for conversational workflows)
  WORKFLOW_USE_SESSION — set "true" only if kickoff requires a prior createSession (default: false)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request, send_from_directory


def _is_valid_app_dir(path: Path) -> bool:
    return (path / "app.py").exists() and (path / "templates" / "index.html").is_file()


def _resolve_app_dir() -> Path:
    """App root — works as a script and under PBJ Workbench (no __file__)."""
    override = os.getenv("CLAIM_REVIEW_UI_DIR", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
        if _is_valid_app_dir(path):
            return path
        print(
            f"WARN: CLAIM_REVIEW_UI_DIR is set but invalid: {path}\n"
            f"  Need: {path}/templates/index.html\n"
            f"  Fix path or remove CLAIM_REVIEW_UI_DIR and restart."
        )

    try:
        path = Path(__file__).resolve().parent
        if _is_valid_app_dir(path):
            return path
    except NameError:
        pass

    candidates: list[Path] = []
    project = os.getenv("CDSW_PROJECT", "").strip()
    if project:
        candidates.append(Path(f"/home/cdsw/{project}/claim-review-ui"))
    candidates.extend(
        [
            Path.cwd() / "claim-review-ui",
            Path.cwd(),
            Path("/home/cdsw/insuranceclaim/claim-review-ui"),
        ]
    )
    valid: list[Path] = []
    for path in candidates:
        if _is_valid_app_dir(path):
            valid.append(path.resolve())
    if not valid:
        return Path.cwd().resolve()
    # Prefer the tree that includes logos (static/) — avoids broken images on CAI.
    for path in valid:
        if (path / "static").is_dir():
            return path
    return valid[0]


_APP_DIR = _resolve_app_dir()
_LOGO_FILES = ("leon-hospital-logo.png", "cloudera-logo.png")


def _static_dir_candidates() -> list[Path]:
    """CAI/PBJ may run app.py from a different cwd than claim-review-ui/static/."""
    project = os.getenv("CDSW_PROJECT", "").strip()
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path)
        if key not in seen:
            seen.add(key)
            candidates.append(path)

    add(_APP_DIR / "static")
    add(Path.cwd() / "claim-review-ui" / "static")
    add(Path.cwd() / "static")
    if project:
        add(Path(f"/home/cdsw/{project}/claim-review-ui/static"))
        add(Path(f"/home/cdsw/{project}/static"))
    try:
        add(Path(__file__).resolve().parent / "static")
    except NameError:
        pass
    override = os.getenv("CLAIM_REVIEW_UI_DIR", "").strip()
    if override:
        add(Path(override).expanduser() / "static")
    add(Path("/home/cdsw/insuranceclaim/claim-review-ui/static"))
    return candidates


def _resolve_static_dir() -> Path:
    for path in _static_dir_candidates():
        if (path / "leon-hospital-logo.png").is_file():
            return path.resolve()
    for path in _static_dir_candidates():
        if path.is_dir():
            return path.resolve()
    return (_APP_DIR / "static").resolve()


_STATIC_DIR = _resolve_static_dir()


def _static_assets_status() -> dict[str, Any]:
    """Report whether logo files exist — use /health to debug missing images on CAI."""
    assets: dict[str, bool] = {}
    for name in _LOGO_FILES:
        assets[name] = (_STATIC_DIR / name).is_file()
    return {
        "app_dir": str(_APP_DIR),
        "static_dir": str(_STATIC_DIR),
        "static_dir_exists": _STATIC_DIR.is_dir(),
        "static_candidates": [str(p) for p in _static_dir_candidates()],
        "assets": assets,
        "all_present": all(assets.values()),
    }


def _ensure_guardrails_import_path() -> None:
    """Find guardrails_check.py next to app.py or in CAI project root."""
    candidates = [
        _APP_DIR,
        Path.cwd(),
        Path("/home/cdsw"),
    ]
    project = os.getenv("CDSW_PROJECT", "").strip()
    if project:
        candidates.append(Path(f"/home/cdsw/{project}"))
    for path in candidates:
        if (path / "guardrails_check.py").exists():
            root = str(path)
            if root not in sys.path:
                sys.path.insert(0, root)
            return


_ensure_guardrails_import_path()
from guardrails_check import check_input, check_output, mode as guardrails_mode

try:
    from notify_manual_review import is_manual_review_text, notifications_enabled, notify_manual_review
except ImportError:
    def notifications_enabled() -> bool:
        return False

    def is_manual_review_text(_text: str) -> bool:
        return False

    def notify_manual_review(*_a: Any, **_kw: Any) -> dict[str, Any]:
        return {"error": "notify_manual_review module not found"}

APP = Flask(
    __name__,
    template_folder=str(_APP_DIR / "templates"),
    static_folder=str(_STATIC_DIR),
    static_url_path="/static",
)


@APP.get("/static/<path:filename>")
def serve_static(filename: str) -> Any:
    """Explicit static route — CAI proxy sometimes misses Flask default static handler."""
    target = _STATIC_DIR / filename
    if not target.is_file():
        return jsonify(
            {
                "error": "static file not found",
                "filename": filename,
                "static_dir": str(_STATIC_DIR),
                "static_assets": _static_assets_status(),
            }
        ), 404
    return send_from_directory(_STATIC_DIR, filename)

DEMO_CLAIMS = [
    {"id": "CLM-50021", "label": "Reject", "tone": "danger", "hint": "Pre-existing + prior auth"},
    {"id": "CLM-50005", "label": "Approve", "tone": "success", "hint": "Clean claim"},
    {"id": "CLM-50003", "label": "Partial", "tone": "warning", "hint": "Missing prior auth"},
    {"id": "CLM-50001", "label": "Manual", "tone": "info", "hint": "Borderline case"},
]


def workflow_config() -> dict[str, str | bool]:
    use_session = os.getenv("WORKFLOW_USE_SESSION", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    api_key = (
        os.getenv("CDSW_API_KEY", "").strip()
        or os.getenv("CDSW_APIV2_KEY", "").strip()
    )
    return {
        "app_url": os.getenv("WORKFLOW_APP_URL", "").strip().rstrip("/"),
        "api_key": api_key,
        "input_key": os.getenv("WORKFLOW_INPUT_KEY", "user_input").strip(),
        "use_session": use_session,
    }


def api_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def events_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def create_session(app_url: str, api_key: str) -> str:
    resp = requests.post(
        f"{app_url}/api/workflow/createSession",
        json={},
        headers=api_headers(api_key),
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    session_id = (
        body.get("session_id")
        or body.get("response", {}).get("session_id")
        or body.get("data", {}).get("session_id")
    )
    if not session_id:
        raise RuntimeError(f"No session_id in createSession response: {body}")
    return str(session_id)


def build_prompt(claim_id: str, policy_id: str | None) -> str:
    parts = [
        f"Please review hospital insurance claim {claim_id} and recommend "
        "Approved, Partial approval, Rejected, or Manual review."
    ]
    if policy_id:
        parts.append(f"Policy number: {policy_id}.")
    parts.append(
        "Look up the claim facts and check MediShield policy rules. "
        "Explain your decision in plain English for a claims adjuster, "
        "cite relevant policy sections, and suggest the next step."
    )
    return " ".join(parts)


def kickoff_workflow(app_url: str, api_key: str, inputs: dict) -> str:
    resp = requests.post(
        f"{app_url}/api/workflow/kickoff",
        json={"inputs": inputs},
        headers=api_headers(api_key),
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    trace_id = body.get("response", {}).get("trace_id") or body.get("trace_id")
    if not trace_id:
        raise RuntimeError(f"No trace_id in kickoff response: {body}")
    return trace_id


_COMPLETE_EVENT_TYPES = frozenset(
    {
        "Crew.complete",
        "crew_kickoff_completed",
        "crew_kickoff_complete",
        "CrewKickoffCompletedEvent",
    }
)


def _normalize_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict):
        for key in ("events", "response", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [e for e in nested if isinstance(e, dict)]
        if payload.get("type"):
            return [payload]
    return []


def _extract_event_output(event: dict[str, Any]) -> Any:
    attrs = event.get("attributes") or {}
    if not isinstance(attrs, dict):
        attrs = {}
    for key in ("output", "result", "raw", "content", "text"):
        if attrs.get(key) not in (None, ""):
            return attrs[key]
        if event.get(key) not in (None, ""):
            return event[key]
    return None


def _is_crew_complete(event_type: str) -> bool:
    etype = event_type.lower()
    if event_type in _COMPLETE_EVENT_TYPES:
        return True
    if "complete" in etype and ("kickoff" in etype or "crew" in etype):
        return True
    return False


def _is_crew_failed(event_type: str) -> bool:
    etype = event_type.lower()
    return "fail" in etype and ("kickoff" in etype or "crew" in etype)


def _parse_workflow_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return complete/error only when the CREW finishes.

    Intermediate agent/task events (and their transient errors) are ignored so
    the UI shows the final, self-corrected crew answer — never an early draft.
    """
    completion_output: Any = None
    crew_error: str | None = None

    # Forward scan: keep the LAST crew-completion output (the final answer).
    for event in events:
        event_type = str(event.get("type", ""))
        attrs = event.get("attributes") or {}
        if not isinstance(attrs, dict):
            attrs = {}

        if _is_crew_complete(event_type):
            output = _extract_event_output(event)
            if output is not None:
                completion_output = output  # overwrite → last one wins

        if _is_crew_failed(event_type):
            crew_error = str(attrs.get("error") or event_type)

    if completion_output is not None:
        return {"status": "complete", "output": completion_output}
    if crew_error:
        return {"status": "error", "error": crew_error}
    return None


def poll_workflow(app_url: str, api_key: str, trace_id: str, timeout_sec: int = 180) -> dict:
    timeout_sec = int(os.getenv("WORKFLOW_POLL_TIMEOUT", str(timeout_sec)))
    deadline = time.time() + timeout_sec
    last_events: list[dict[str, Any]] = []

    while time.time() < deadline:
        resp = requests.get(
            f"{app_url}/api/workflow/events",
            params={"trace_id": trace_id},
            headers=events_headers(api_key),
            timeout=60,
        )
        resp.raise_for_status()
        events = _normalize_events(resp.json())
        last_events = events

        parsed = _parse_workflow_events(events)
        if parsed:
            parsed["trace_id"] = trace_id
            return parsed

        time.sleep(2)

    last_types = [str(e.get("type", "?")) for e in last_events[-5:]]
    return {
        "status": "timeout",
        "error": (
            "Workflow did not complete within timeout. "
            f"Last event types: {last_types or ['none']}."
        ),
        "trace_id": trace_id,
        "events": last_events[-5:] if last_events else [],
    }


CLAIM_ID_RE = re.compile(r"CLM-\d{5}", re.IGNORECASE)


def extract_claim_id(text: str) -> str | None:
    match = CLAIM_ID_RE.search(text or "")
    return match.group(0).upper() if match else None


# Known governed facts for the demo claims (from claim_features_v1 / demo_claims.json).
# Used only to VERIFY the agent answer is grounded — never to generate it.
_EXPECTED_CLAIMS: dict[str, dict[str, Any]] = {
    "CLM-50005": {"amount": 337.39, "outcome": "approved"},
    "CLM-50021": {"amount": 4843.14, "outcome": "rejected"},
    "CLM-50003": {"amount": 5086.23, "outcome": "partial"},
    "CLM-50001": {"amount": 668.78, "outcome": "manual review"},
}

_OUTCOME_SYNONYMS: dict[str, list[str]] = {
    "approved": ["approve", "approved"],
    "rejected": ["reject", "rejected", "denied", "denial", "deny"],
    "partial": ["partial"],
    "manual review": ["manual review", "manual_review", "clinical review", "escalate"],
}


def grounding_check(output_text: str, claim_id: str | None) -> dict[str, Any]:
    """Verify the answer matches governed facts. Returns checked/grounded/issues."""
    exp = _EXPECTED_CLAIMS.get((claim_id or "").upper())
    if not exp:
        return {"checked": False}

    text = (output_text or "").lower()
    issues: list[str] = []

    amt = float(exp["amount"])
    amount_variants = [f"{amt:.2f}", f"{amt:,.2f}", str(int(round(amt)))]
    if not any(v.lower() in text for v in amount_variants):
        issues.append(f"expected amount {amt:.2f} not present")

    outcome = str(exp["outcome"])
    synonyms = _OUTCOME_SYNONYMS.get(outcome, [outcome])
    if not any(s in text for s in synonyms):
        issues.append(f"expected decision '{outcome}' not present")

    return {
        "checked": True,
        "grounded": not issues,
        "issues": issues,
        "expected_amount": amt,
        "expected_outcome": outcome,
    }


def _maybe_notify_manual_review(
    output_text: str,
    claim_id: str | None,
    trace_id: str | None,
) -> dict[str, Any] | None:
    """Send free ntfy/Slack alert only when the agent recommends manual human review."""
    if not notifications_enabled():
        return None
    if not is_manual_review_text(output_text):
        return None
    reason = "AI recommended manual review — see chat for details"
    lower = output_text.lower()
    if "experimental" in lower:
        reason = "Experimental treatment — clinical review required"
    elif "clinical" in lower:
        reason = "Clinical review required per policy"
    elif "prior auth" in lower or "prior authorization" in lower:
        reason = "Prior authorization / clinical review required"
    try:
        return notify_manual_review(
            claim_id=claim_id or "UNKNOWN",
            reason=reason,
            trace_id=trace_id or "",
        )
    except Exception as exc:
        return {"error": str(exc), "claim_id": claim_id}


def resolve_chat_message(payload: dict) -> tuple[str, str | None, str | None]:
    """Return (workflow_message, claim_id, policy_id)."""
    message = (payload.get("message") or "").strip()
    claim_id = (payload.get("claim_id") or "").strip().upper() or None
    policy_id = (payload.get("policy_id") or "").strip() or None

    if message:
        found = extract_claim_id(message)
        if found:
            claim_id = found
        return message, claim_id, policy_id

    if claim_id:
        if not CLAIM_ID_RE.match(claim_id):
            raise ValueError(f"Invalid claim_id: {claim_id}")
        return build_prompt(claim_id, policy_id), claim_id, policy_id

    raise ValueError("message or claim_id is required")


@APP.get("/")
def index():
    cfg = workflow_config()
    template_path = _APP_DIR / "templates" / "index.html"
    if not template_path.is_file():
        return (
            f"UI template missing: {template_path}\n"
            f"app_dir={_APP_DIR}\n"
            "Upload templates/index.html or fix CLAIM_REVIEW_UI_DIR, then restart.",
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    return render_template(
        "index.html",
        demo_claims=DEMO_CLAIMS,
        workflow_configured=bool(cfg["app_url"] and cfg["api_key"]),
        workflow_app_url=cfg["app_url"] or "(not set)",
        guardrails_mode=guardrails_mode(),
    )


@APP.get("/health")
@APP.get("/healthcheck")
def health():
    cfg = workflow_config()
    key = str(cfg.get("api_key") or "")
    return jsonify(
        {
            "status": "ok",
            "workflow_configured": bool(cfg["app_url"] and key),
            "workflow_app_url": cfg.get("app_url") or "",
            "api_key_length": len(key),
            "guardrails_mode": guardrails_mode(),
            "static_assets": _static_assets_status(),
        }
    )


def _run_workflow_chat(payload: dict) -> tuple[dict, int]:
    try:
        prompt, claim_id, policy_id = resolve_chat_message(payload)
    except ValueError as exc:
        return {"error": str(exc)}, 400

    cfg = workflow_config()
    if not cfg["app_url"] or not cfg["api_key"]:
        return {
            "error": "Workflow not configured",
            "hint": (
                "Set WORKFLOW_APP_URL to your deployed Agent Studio application URL "
                "and CDSW_API_KEY in CAI Application or project environment variables."
            ),
        }, 503

    input_guard = check_input(prompt)
    if not input_guard.get("passed"):
        return {
            "error": "Guardrail blocked request",
            "reason": input_guard.get("reason"),
            "engine": input_guard.get("engine", guardrails_mode()),
            "status": "guardrail_blocked",
        }, 400

    input_key = str(cfg["input_key"])
    # Match Agent Studio kickoff API: {"inputs": {"user_input": "...", "context": ""}}
    if input_key == "user_input":
        inputs = {"user_input": prompt, "context": ""}
    else:
        inputs = {input_key: prompt}

    # Retry once on cold-start failure/timeout or an ungrounded first answer.
    max_attempts = int(os.getenv("WORKFLOW_MAX_ATTEMPTS", "2"))

    try:
        result: dict[str, Any] = {}
        output_text = ""
        grounding: dict[str, Any] = {"checked": False}

        for attempt in range(1, max_attempts + 1):
            session_id = None
            if cfg["use_session"]:
                session_id = create_session(cfg["app_url"], cfg["api_key"])
            trace_id = kickoff_workflow(cfg["app_url"], cfg["api_key"], inputs)
            result = poll_workflow(cfg["app_url"], cfg["api_key"], trace_id)
            if session_id:
                result["session_id"] = session_id

            status = result.get("status")
            output_text = result.get("output")
            if isinstance(output_text, dict):
                output_text = json.dumps(output_text)
            elif output_text is None:
                output_text = ""
            else:
                output_text = str(output_text)

            grounding = grounding_check(output_text, claim_id)

            # Good enough to return: completed AND (not checkable OR grounded).
            if status == "complete" and (not grounding.get("checked") or grounding.get("grounded")):
                break
            # Out of attempts — return whatever we have (flagged below).
            if attempt >= max_attempts:
                break
            # else: retry (cold start / hallucinated first pass)

        result["claim_id"] = claim_id
        result["policy_id"] = policy_id
        result["prompt"] = prompt
        result["attempts"] = attempt

        # Hard failure after retries.
        if result.get("status") in ("error", "timeout"):
            return result, 200

        output_guard = check_output(output_text)
        if not output_guard.get("passed"):
            return {
                "status": "guardrail_blocked",
                "error": "Guardrail blocked response",
                "reason": output_guard.get("reason"),
                "engine": output_guard.get("engine", guardrails_mode()),
                "trace_id": result.get("trace_id"),
                "claim_id": claim_id,
            }, 422

        result["guardrails"] = {"passed": True, "engine": output_guard.get("engine", guardrails_mode())}
        result["grounding"] = grounding
        result["message"] = prompt

        ticket = _maybe_notify_manual_review(output_text, claim_id, result.get("trace_id"))
        if ticket:
            result["manual_review_ticket"] = ticket

        return result, 200
    except requests.HTTPError as exc:
        detail = exc.response.text[:500] if exc.response is not None else ""
        hint = ""
        if exc.response is not None and exc.response.status_code == 401:
            hint = (
                "401 Unauthorized: regenerate API key (User Settings → API Keys), paste the "
                "full secret (not Key ID) into CDSW_API_KEY on this application, then Restart."
            )
        return {
            "error": f"Workflow HTTP error: {exc}",
            "detail": detail,
            "hint": hint,
        }, 502
    except Exception as exc:
        return {"error": str(exc)}, 500


@APP.post("/api/chat")
def chat():
    body, status = _run_workflow_chat(request.get_json(silent=True) or {})
    return jsonify(body), status


@APP.post("/api/review")
def review():
    body, status = _run_workflow_chat(request.get_json(silent=True) or {})
    return jsonify(body), status


def _flask_host_port() -> tuple[str, int]:
    """
    Cloudera port rules:
    - PBJ Workbench editor owns CDSW_APP_PORT (8100) for the kernel gateway.
    - Flask must bind CDSW_READONLY_PORT (see Cloudera Flask application docs).
    - Standard editor: bind CDSW_APP_PORT.
    """
    if os.getenv("CLAIM_REVIEW_UI_PORT"):
        return os.getenv("CDSW_APP_HOST", "127.0.0.1"), int(os.environ["CLAIM_REVIEW_UI_PORT"])

    readonly = os.getenv("CDSW_READONLY_PORT", "").strip()
    if readonly:
        return "127.0.0.1", int(readonly)

    editor = os.getenv("ML_RUNTIME_EDITOR", "").lower()
    try:
        get_ipython()  # type: ignore[name-defined]
        in_pbj = True
    except NameError:
        in_pbj = False
    if "pbj" in editor or in_pbj:
        # Kernel gateway already bound CDSW_APP_PORT (8100).
        return "127.0.0.1", 8090

    return os.getenv("CDSW_APP_HOST", "0.0.0.0"), int(os.getenv("CDSW_APP_PORT", "8090"))


def main() -> None:
    host, port = _flask_host_port()
    static_status = _static_assets_status()
    template_path = _APP_DIR / "templates" / "index.html"
    print(f"MediShield Copilot starting on {host}:{port}")
    print(f"  app_dir     : {static_status['app_dir']}")
    print(f"  template    : {template_path} ({'OK' if template_path.is_file() else 'MISSING'})")
    print(f"  static_dir  : {static_status['static_dir']} (exists={static_status['static_dir_exists']})")
    for name, ok in static_status["assets"].items():
        print(f"  static asset: {name} -> {'OK' if ok else 'MISSING — upload static/ folder'}")
    if not static_status["all_present"]:
        print("  static search paths:")
        for path in static_status.get("static_candidates", []):
            print(f"    - {path}")
    override = os.getenv("CLAIM_REVIEW_UI_DIR", "").strip()
    if override and not _is_valid_app_dir(Path(override).expanduser().resolve()):
        print(f"  WARN: remove or fix CLAIM_REVIEW_UI_DIR={override}")
    APP.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
