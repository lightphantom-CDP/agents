"""Central configuration and light-weight data structures.

Everything here can be overridden from the CLI or environment variables so the
tool can be reused for a different portfolio without editing code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Dict, List


@dataclass(frozen=True)
class Holding:
    """A single instrument the user cares about."""

    symbol: str          # Yahoo Finance symbol, e.g. "SPY"
    name: str            # Human friendly name
    target_weight: float  # Intended portfolio allocation (0-1); used for the blended verdict


# The portfolio described by the user: the S&P 500 plus three high-conviction
# large-cap compounders. SPY is used as the investable proxy for "the S&P 500".
DEFAULT_HOLDINGS: List[Holding] = [
    Holding("SPY", "S&P 500 (SPY ETF)", 0.40),
    Holding("NVDA", "NVIDIA", 0.20),
    Holding("AMZN", "Amazon", 0.20),
    Holding("META", "Meta Platforms", 0.20),
]


@dataclass(frozen=True)
class ScoreWeights:
    """How much each pillar contributes to the composite 0-100 buy score.

    The four pillars intentionally pull against each other so the *highest*
    scores land on "a pullback inside a healthy long-term uptrend" - which is
    exactly the kind of fat pitch a patient, value-minded investor waits for.
    """

    valuation: float = 0.35   # Margin of safety: are we buying on sale?
    technical: float = 0.30   # Entry timing: RSI / distance from 200DMA / MACD
    trend: float = 0.20       # Is the durable long-term uptrend intact?
    momentum: float = 0.15    # Is there a healthy (not catastrophic) pullback to buy?

    def as_dict(self) -> Dict[str, float]:
        return {
            "valuation": self.valuation,
            "technical": self.technical,
            "trend": self.trend,
            "momentum": self.momentum,
        }


@dataclass(frozen=True)
class GoalConfig:
    """The user's savings goal, expressed in their own terms."""

    starting_cash_usd: float = 4000.0
    target_amount_idr: float = 1_000_000_000.0   # 1 billion Indonesian Rupiah
    min_years: float = 3.0
    max_years: float = 4.0
    # Fallback FX used only if a live USD/IDR quote cannot be fetched.
    fallback_usd_idr: float = 16_500.0
    # Long-run return scenarios used to size required monthly contributions.
    # 0.10 ~ historical S&P 500 nominal; 0.20 ~ a Buffett-like great decade.
    return_scenarios: tuple = (0.08, 0.10, 0.15, 0.20)


@dataclass
class AppConfig:
    holdings: List[Holding] = field(default_factory=lambda: list(DEFAULT_HOLDINGS))
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    goal: GoalConfig = field(default_factory=GoalConfig)
    history_range: str = "1y"     # Yahoo range for daily bars
    cache_ttl_seconds: int = 900  # Re-use fetched data for 15 min (hourly cron friendly)
    demo: bool = False            # Use synthetic offline data instead of the network

    def with_overrides(self, **kwargs) -> "AppConfig":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


# Recommendation bands for the composite score. Ordered high -> low.
SCORE_BANDS = [
    (80, "STRONG BUY", "Fat pitch - quality on sale inside an intact uptrend."),
    (66, "BUY / ACCUMULATE", "Attractive entry; add to the position."),
    (50, "NEUTRAL - DCA", "Fairly valued; keep dollar-cost averaging on schedule."),
    (35, "HOLD / WAIT", "Not compelling right now; wait for a better price."),
    (0, "EXPENSIVE - AVOID ADDING", "Stretched; patience beats chasing."),
]


def label_for_score(score: float) -> tuple[str, str]:
    """Map a 0-100 score to a (label, one-line reason)."""
    for threshold, label, reason in SCORE_BANDS:
        if score >= threshold:
            return label, reason
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]


def holdings_from_env_or_default() -> List[Holding]:
    """Allow overriding the watch-list via the SCORER_TICKERS env var.

    Format: "SPY:S&P 500:0.4,NVDA:NVIDIA:0.2" (weight optional -> equal weight).
    """
    raw = os.getenv("SCORER_TICKERS", "").strip()
    if not raw:
        return list(DEFAULT_HOLDINGS)
    parsed: List[Holding] = []
    for chunk in raw.split(","):
        parts = [p.strip() for p in chunk.split(":") if p.strip()]
        if not parts:
            continue
        symbol = parts[0].upper()
        name = parts[1] if len(parts) > 1 else symbol
        weight = float(parts[2]) if len(parts) > 2 else 0.0
        parsed.append(Holding(symbol, name, weight))
    # Normalise weights if none/partial provided.
    total = sum(h.target_weight for h in parsed)
    if total <= 0:
        equal = 1.0 / len(parsed)
        parsed = [replace(h, target_weight=equal) for h in parsed]
    return parsed
