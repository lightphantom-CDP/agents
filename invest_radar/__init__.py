"""InvestRadar - hourly, Buffett-minded "is this a good price to add?" scores.

A lightweight, dependency-light tool that pulls real-time-ish market data for a
small watchlist (S&P 500 + a few mega-cap compounders), scores each 0-100 on a
blend of *valuation*, *dip/margin-of-safety*, *long-term trend* and *timing*, and
tracks progress toward a personal savings goal.

It is intentionally built on the Python standard library plus ``requests`` only,
so it runs anywhere without a heavy data-science stack.

This is educational tooling, not financial advice.
"""

from .config import DEFAULT_WATCHLIST, GoalConfig

__all__ = ["DEFAULT_WATCHLIST", "GoalConfig", "__version__"]

__version__ = "1.0.0"
