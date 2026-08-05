"""Warren Buffett Investment Scorer.

A small, dependency-light toolkit that answers one practical question on an
hourly schedule: *"Is right now a reasonable price to add to my positions?"*

It blends a Warren-Buffett-style "margin of safety" view (buy quality when it is
on sale) with a handful of classic technical timing signals, and turns them into
an easy 0-100 score per instrument plus a plain-English recommendation.

The package is intentionally built on the Python standard library so it runs
anywhere (no pandas/numpy required). Live prices come from Yahoo Finance's public
chart endpoint, with automatic retries, host rotation and an offline demo mode so
the tool never hard-fails.

Nothing here is financial advice - it is an educational decision-support tool.
"""

__version__ = "1.0.0"

from .scoring import score_series, ScoreResult  # noqa: E402,F401
from .goal import plan_goal, GoalPlan  # noqa: E402,F401

__all__ = ["__version__", "score_series", "ScoreResult", "plan_goal", "GoalPlan"]
