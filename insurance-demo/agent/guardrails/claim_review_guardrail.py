"""
Custom guardrail for MediShield claim review workflow (Agent Studio).

Upload this file in Configure Guardrails → Custom Guardrails.
Optional requirements.txt can be empty.

API: https://docs.cloudera.com/machine-learning/1.5.5/use-ai-studios/topics/ml-custom-guardrails.html
"""

from __future__ import annotations

import re


class GuardrailBlockedError(Exception):
    """Raise to block the LLM call or response."""


_BYPASS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"approve\s+.+\s+without\s+(checking|lookup|tools)", re.I),
    re.compile(r"skip\s+(the\s+)?tools?", re.I),
    re.compile(r"do\s+not\s+(call|use)\s+tools?", re.I),
]

_MEDICAL_ADVICE_PATTERNS = [
    re.compile(r"\b(you should take|prescribe|dosage|mg\s+per\s+day)\b", re.I),
    re.compile(r"\b(start\s+taking|stop\s+taking)\s+\w+\s+(medication|medicine|drug)", re.I),
]


def _text_from_messages(messages: list[dict]) -> str:
    parts: list[str] = []
    for msg in messages or []:
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def _text_from_response(response: dict) -> str:
    if not isinstance(response, dict):
        return str(response)
    for key in ("content", "text", "output"):
        val = response.get(key)
        if isinstance(val, str):
            return val
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
    return str(response)


def pre_call(messages: list[dict], model: str, kwargs: dict) -> list[dict]:
    text = _text_from_messages(messages)
    for pattern in _BYPASS_PATTERNS:
        if pattern.search(text):
            raise GuardrailBlockedError(
                "Request blocked: claim reviews must use governed claim data and policy tools."
            )
    return messages


def post_call(response: dict, messages: list[dict], model: str) -> dict:
    text = _text_from_response(response)
    for pattern in _MEDICAL_ADVICE_PATTERNS:
        if pattern.search(text):
            raise GuardrailBlockedError(
                "Response blocked: this copilot provides claim adjudication only, not medical advice."
            )
    return response
