"""Real-time investment scoring for a Warren-Buffett-style DCA plan.

This package fetches near-real-time market data (no API key required) and
computes a 0-100 "good time to buy" score for a watchlist of assets, then
turns those scores into a concrete, disciplined dollar-cost-averaging plan
that is measured against a long-term savings goal.

Nothing here is financial advice. It is an educational tool. See the module
``investment_advisor.planner`` for the honest math on what a goal actually
requires, and ``README.md`` for the methodology and its limitations.
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "config",
    "data",
    "indicators",
    "scoring",
    "planner",
    "report",
    "advisor",
]

__version__ = "1.0.0"
