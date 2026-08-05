"""Optional push notifications via Pushover (used elsewhere in this course).

Entirely best-effort: if the ``PUSHOVER_TOKEN`` / ``PUSHOVER_USER`` environment
variables are not set, notifications are silently skipped. No third-party
library is required - it posts with the standard library.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import List

from .report import Report


def _pushover(title: str, message: str) -> bool:
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if not token or not user:
        return False
    data = urllib.parse.urlencode({
        "token": token,
        "user": user,
        "title": title[:250],
        "message": message[:1024],
    }).encode()
    try:
        req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as err:
        print(f"[notify] pushover failed: {err}")
        return False


def maybe_notify(report: Report, threshold: float = 66.0) -> bool:
    """Send an alert only when something is actually worth acting on."""
    hits: List[str] = [
        f"{r.symbol} {r.composite:.0f} ({r.label})"
        for r in report.results
        if r.composite >= threshold
    ]
    if report.portfolio_score < threshold and not hits:
        return False
    title = f"Buy signal: portfolio {report.portfolio_score:.0f}/100"
    body = report.overall_reason
    if hits:
        body += "\n" + " | ".join(hits)
    return _pushover(title, body)
