"""
Guardrails for claim-review-ui.

GUARDRAILS_MODE:
  off            — no checks
  simple         — regex rules only (no extra packages)
  guardrails_ai  — Guardrails AI validators + simple rules

Env vars (guardrails_ai):
  GUARDRAILS_API_KEY or GUARDRAILS_AI_API_KEY — Hub token from guardrailsai.com/hub/keys
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any

_BYPASS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"approve\s+.+\s+without\s+(checking|lookup|tools)", re.I),
    re.compile(r"skip\s+(the\s+)?tools?", re.I),
]

_MEDICAL_ADVICE_PATTERNS = [
    re.compile(r"\b(you should take|prescribe|dosage|mg\s+per\s+day)\b", re.I),
    re.compile(r"\b(start\s+taking|stop\s+taking)\s+\w+\s+(medication|medicine|drug)", re.I),
]

# Lightweight PII patterns (simple mode + fallback when Presidio not installed)
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "US Social Security number"),
    (re.compile(r"\bSSN\b", re.I), "SSN reference"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "email address"),
    (
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "phone number",
    ),
]

_CONFIGURED = False


def mode() -> str:
    return os.getenv("GUARDRAILS_MODE", "simple").strip().lower()


def hub_api_key() -> str:
    return (
        os.getenv("GUARDRAILS_API_KEY", "").strip()
        or os.getenv("GUARDRAILS_AI_API_KEY", "").strip()
    )


def ensure_guardrails_configured() -> None:
    """Write ~/.guardrailsrc from env (CAI pods may not keep CLI config)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # guardrails-ai 0.11+ requires ~/.guardrailsrc even for local Presidio inference.
    rc_path = Path.home() / ".guardrailsrc"
    if not rc_path.exists():
        token = hub_api_key()
        lines = [
            f"id={uuid.uuid4()}",
            "enable_metrics=false",
            "use_remote_inferencing=false",
        ]
        if token:
            lines.insert(1, f"token={token}")
        rc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _CONFIGURED = True


def check_input(text: str) -> dict[str, Any]:
    if mode() == "off":
        return {"passed": True}

    simple = _check_input_simple(text)
    if not simple.get("passed"):
        return simple

    if mode() == "guardrails_ai":
        result = _check_input_guardrails_ai(text)
        if result is not None:
            return result

    return simple


def check_output(text: str) -> dict[str, Any]:
    if mode() == "off":
        return {"passed": True}

    simple = _check_output_simple(text)
    if not simple.get("passed"):
        return simple

    if mode() == "guardrails_ai":
        result = _check_output_guardrails_ai(text)
        if result is not None:
            return result

    return simple


def _check_pii_simple(text: str) -> dict[str, Any] | None:
    for pattern, label in _PII_PATTERNS:
        if pattern.search(text):
            return {
                "passed": False,
                "reason": f"Request blocked: do not send {label} in chat. Use claim ID only (e.g. CLM-50021).",
                "engine": "simple",
            }
    return None


def _check_input_simple(text: str) -> dict[str, Any]:
    for pattern in _BYPASS_PATTERNS:
        if pattern.search(text):
            return {
                "passed": False,
                "reason": "Request blocked: claim reviews must use governed claim data and policy tools.",
                "engine": "simple",
            }
    pii = _check_pii_simple(text)
    if pii:
        return pii
    return {"passed": True, "engine": "simple"}


def _check_output_simple(text: str) -> dict[str, Any]:
    for pattern in _MEDICAL_ADVICE_PATTERNS:
        if pattern.search(text):
            return {
                "passed": False,
                "reason": "Response blocked: this copilot provides claim adjudication only, not medical advice.",
                "engine": "simple",
            }
    pii = _check_pii_simple(text)
    if pii:
        return {
            "passed": False,
            "reason": pii["reason"].replace("Request blocked:", "Response blocked:"),
            "engine": "simple",
        }
    return {"passed": True, "engine": "simple"}


def _pii_guard():
    from guardrails import Guard, OnFailAction
    from guardrails_ai.detect_pii import DetectPII

    ensure_guardrails_configured()
    # guardrails-ai >= 0.11: Guard.use() takes Validator instances only (no kwargs).
    validator = DetectPII(
        pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN"],
        use_local=True,
        on_fail=OnFailAction.EXCEPTION,
    )
    return Guard().use(validator)


def _check_input_guardrails_ai(text: str) -> dict[str, Any] | None:
    try:
        ensure_guardrails_configured()
        guard = _pii_guard()
        guard.validate(text)
        return {"passed": True, "engine": "guardrails_ai"}
    except ImportError:
        return None  # fall back to simple rules (includes PII regex)
    except Exception as exc:
        return {"passed": False, "reason": str(exc), "engine": "guardrails_ai"}


def _check_output_guardrails_ai(text: str) -> dict[str, Any]:
    """Same PII check on output — block if agent echoes SSN/phone/email."""
    return _check_input_guardrails_ai(text) or {"passed": True, "engine": "guardrails_ai"}
