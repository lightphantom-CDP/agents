"""Central configuration for the investment scorer.

Everything that a user might reasonably want to tweak (which holdings to
track, how each factor is weighted, the savings goal, etc.) lives here so the
rest of the codebase stays declarative.

This module is intentionally dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Holding:
    """A single thing we score.

    ``kind`` controls how it is scored:
      * ``"stock"`` -> full Buffett-style quality + timing blend.
      * ``"index"`` -> broad-market fund (e.g. an S&P 500 ETF). We lean on
        timing/valuation only and add a "just keep buying" reminder, because
        for a diversified index Buffett's own advice is steady accumulation
        rather than market timing.
    """

    symbol: str
    name: str
    kind: str = "stock"  # "stock" | "index"


# The user's actual portfolio: the S&P 500 (tracked via the SPY ETF, which is a
# tradable proxy that also exposes a P/E and yield), plus three individual names.
HOLDINGS: list[Holding] = [
    Holding("SPY", "S&P 500 (SPY ETF)", kind="index"),
    Holding("NVDA", "NVIDIA", kind="stock"),
    Holding("AMZN", "Amazon", kind="stock"),
    Holding("META", "Meta Platforms", kind="stock"),
]

# The broad index level itself, shown only as market context (not scored as a
# tradable holding).
MARKET_CONTEXT_SYMBOL = "^GSPC"

# USD -> IDR is fetched live from this FX symbol; this value is only a fallback
# used when the network lookup fails so the report can still render.
FX_SYMBOL = "IDR=X"
FX_USD_IDR_FALLBACK = 16_500.0


# --------------------------------------------------------------------------- #
# Scoring weights
# --------------------------------------------------------------------------- #
# How the "is this a good price right now?" timing sub-score is built.
TIMING_WEIGHTS: dict[str, float] = {
    "rsi": 0.30,            # oversold = opportunity, overbought = wait
    "range_position": 0.25,  # where price sits in its 52-week range
    "vs_sma200": 0.25,      # discount/premium to the long-term trend line
    "drawdown": 0.20,       # "be greedy when others are fearful"
}

# How the Buffett-style business-quality + valuation sub-score is built.
QUALITY_WEIGHTS: dict[str, float] = {
    "roe": 0.20,            # durable, high returns on equity = a moat
    "margins": 0.18,        # fat, stable margins = pricing power
    "debt": 0.15,           # low leverage = survives bad years
    "fcf": 0.10,            # real cash, not just accounting earnings
    "valuation": 0.25,      # pay a fair price (P/E, PEG, P/B)
    "growth": 0.12,         # the business is still compounding
}

# Final blend of the two sub-scores.
COMPOSITE_BLEND = {
    "stock": {"quality": 0.55, "timing": 0.45},
    # For an index we mostly care about timing, but a rich market P/E should
    # still temper enthusiasm, so valuation gets a slice too.
    "index": {"quality": 0.30, "timing": 0.70},
}


# --------------------------------------------------------------------------- #
# Verdict bands (composite score 0-100 -> label)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VerdictBand:
    floor: float
    label: str
    action: str


VERDICT_BANDS: list[VerdictBand] = [
    VerdictBand(78, "STRONG BUY ZONE", "Attractive entry - deploy on the higher end of your plan."),
    VerdictBand(62, "ACCUMULATE", "Good entry - a solid time to add on your schedule."),
    VerdictBand(46, "FAIR", "Reasonable - keep dollar-cost averaging, no urgency."),
    VerdictBand(32, "PATIENCE", "A little rich - prefer smaller buys / wait for a dip."),
    VerdictBand(0, "EXPENSIVE", "Stretched - wait for a better price or trim buys."),
]


# --------------------------------------------------------------------------- #
# The savings goal
# --------------------------------------------------------------------------- #
@dataclass
class Goal:
    start_capital_usd: float = 4_000.0
    target_idr: float = 1_000_000_000.0  # 1 billion IDR
    horizon_years_low: float = 3.0
    horizon_years_high: float = 4.0
    # Optional recurring contribution used by the "how do I actually get there?"
    # planner. Zero by default (lump-sum only) but easily overridden.
    monthly_contribution_usd: float = 0.0
    # Reference returns for planning (annualised, decimal).
    reference_returns: dict[str, float] = field(
        default_factory=lambda: {
            "S&P 500 long-run (~10%)": 0.10,
            "Strong-but-realistic (~15%)": 0.15,
            "Exceptional / high-risk (~25%)": 0.25,
        }
    )


GOAL = Goal()

# History window (days) pulled for indicator calculations.
HISTORY_RANGE = "1y"
HISTORY_INTERVAL = "1d"

# Network behaviour.
HTTP_TIMEOUT_SECONDS = 20
HTTP_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
