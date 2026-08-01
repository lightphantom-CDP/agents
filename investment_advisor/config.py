"""Default configuration for the investment advisor.

Everything here is overridable from the command line so the tool stays
useful even if your goal, cash, currency or watchlist change.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    """A watchlist entry.

    Attributes:
        symbol: Yahoo Finance ticker used to pull prices.
        name: Human friendly label shown in the report.
        kind: ``"index"`` for broad-market funds, ``"stock"`` for single names.
            The index is treated as the low-risk core of the portfolio, the
            single stocks as higher-risk "satellites".
        policy_weight: Target share of invested capital, Buffett style: the
            index gets the majority, satellites split the rest.
    """

    symbol: str
    name: str
    kind: str
    policy_weight: float


# S&P 500 is represented by SPY (the most liquid S&P 500 ETF). VOO / IVV are
# cheaper equivalents that score essentially identically.
DEFAULT_ASSETS: tuple[Asset, ...] = (
    Asset("SPY", "S&P 500 (SPY ETF)", "index", 0.55),
    Asset("NVDA", "NVIDIA", "stock", 0.15),
    Asset("AMZN", "Amazon", "stock", 0.15),
    Asset("META", "Meta Platforms", "stock", 0.15),
)

# Starting situation described by the investor.
DEFAULT_CASH_USD: float = 4_000.0
DEFAULT_TARGET_IDR: float = 1_000_000_000.0
DEFAULT_HORIZONS_YEARS: tuple[float, ...] = (3.0, 4.0)

# Used only if the live USD/IDR quote cannot be fetched. Clearly an
# assumption, not a promise; override with --usd-idr.
FALLBACK_USD_IDR: float = 17_990.0

# Reference annual returns used to show what is *realistically* achievable
# rather than what the goal demands. 0.10 ~= long-run S&P 500 average;
# 0.20 ~= an exceptional, Buffett-like long-run record; 0.30 is already very
# optimistic for a diversified portfolio.
REFERENCE_ANNUAL_RETURNS: tuple[float, ...] = (0.07, 0.10, 0.15, 0.20, 0.30)

# Return assumption used when computing the monthly saving required to hit the
# goal. Deliberately conservative-but-plausible for an equity portfolio.
PLANNING_ANNUAL_RETURN: float = 0.12

# Weights for the sub-scores that make up the 0-100 buy score. Must sum to 1.
SCORE_WEIGHTS: dict[str, float] = {
    "value_in_range": 0.25,   # cheap within its own 52-week range
    "drawdown": 0.20,         # discount from the 52-week high (buy weakness)
    "rsi": 0.20,              # oversold vs overbought (mean reversion)
    "trend": 0.20,            # quality filter: avoid falling knives / froth
    "pullback": 0.15,         # short-term dip inside a longer-term uptrend
}

# Score thresholds -> action label. Read as "how attractive is buying now".
ACTION_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (78.0, "STRONG BUY"),
    (62.0, "BUY / ADD"),
    (48.0, "ACCUMULATE (DCA)"),
    (34.0, "HOLD / PATIENT"),
    (0.0, "WAIT / EXPENSIVE"),
)

# How many dollar-cost-averaging tranches to split idle cash into. Buffett's
# point: you cannot time the market, so feed money in steadily.
DEFAULT_DCA_TRANCHES: int = 12

# Network settings for the data layer.
HTTP_TIMEOUT_SECONDS: float = 15.0
HTTP_RETRIES: int = 3
USER_AGENT: str = "InvestmentAdvisor/1.0 (+educational; https://github.com)"
YAHOO_HOSTS: tuple[str, ...] = (
    "https://query1.finance.yahoo.com",
    "https://query2.finance.yahoo.com",
)
