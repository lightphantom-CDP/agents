"""Static configuration: the watchlist, valuation profiles and the savings goal.

Everything a user is likely to tweak lives here so the rest of the package can
stay generic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Asset:
    """A single instrument on the watchlist.

    Attributes:
        symbol: Yahoo Finance ticker used for data lookups.
        name: Human friendly display name.
        kind: ``"index"`` or ``"growth"`` - only affects default valuation bands.
        pe_metric: Which P/E to prefer for valuation (``"forward"`` or ``"trailing"``).
        pe_anchors: Monotonically increasing ``(pe, score)`` points used to map a
            P/E ratio to a 0-100 valuation score via linear interpolation. Lower
            P/E -> higher score (cheaper = better entry for a quality name).
        note: Short qualitative reminder about the business (Buffett-style moat note).
    """

    symbol: str
    name: str
    kind: str
    pe_metric: str
    pe_anchors: tuple[tuple[float, float], ...]
    note: str = ""


# Valuation "anchors" encode a pragmatic, Buffett-leaning view: pay up only so far
# even for great businesses. They are deliberately conservative for richly valued
# growth names and stricter still for the broad index.
DEFAULT_WATCHLIST: tuple[Asset, ...] = (
    Asset(
        symbol="SPY",
        name="S&P 500 (SPY)",
        kind="index",
        pe_metric="trailing",
        pe_anchors=((15, 95), (18, 80), (21, 62), (24, 45), (28, 30), (34, 12)),
        note="The default core holding Buffett recommends for most people.",
    ),
    Asset(
        symbol="NVDA",
        name="NVIDIA (NVDA)",
        kind="growth",
        pe_metric="forward",
        pe_anchors=((18, 96), (25, 82), (32, 64), (40, 46), (50, 30), (65, 12)),
        note="Dominant AI compute franchise; superb economics, cyclical demand.",
    ),
    Asset(
        symbol="AMZN",
        name="Amazon (AMZN)",
        kind="growth",
        pe_metric="forward",
        pe_anchors=((20, 93), (28, 80), (35, 62), (45, 45), (58, 28), (75, 12)),
        note="Retail + AWS + ads flywheel; owner-operator culture, wide moat.",
    ),
    Asset(
        symbol="META",
        name="Meta (META)",
        kind="growth",
        pe_metric="forward",
        pe_anchors=((15, 96), (20, 84), (26, 66), (33, 47), (42, 30), (55, 12)),
        note="3B+ user network effect; huge cash flow, disciplined on buybacks.",
    ),
)


@dataclass(frozen=True)
class GoalConfig:
    """The user's savings goal, used for the honest 'can I get there?' analysis."""

    start_cash_usd: float = 4000.0
    target_idr: float = 1_000_000_000.0
    horizons_years: tuple[int, ...] = (3, 4)
    # Return scenarios to sanity-check the goal against (annualised, nominal).
    return_scenarios: tuple[tuple[str, float], ...] = (
        ("Index-like", 0.10),
        ("Aggressive", 0.15),
        ("Very aggressive", 0.20),
    )


# Scoring weights (must sum to ~1.0). Buffett order: value first, then a margin of
# safety on price, then trend/quality, then short-term timing.
SCORE_WEIGHTS: dict[str, float] = {
    "valuation": 0.35,
    "dip": 0.30,
    "trend": 0.20,
    "timing": 0.15,
}


# Verdict bands keyed by the lower bound of the score range (inclusive).
VERDICT_BANDS: tuple[tuple[float, str, str], ...] = (
    (78, "STRONG BUY", "#16a34a"),
    (66, "BUY / ADD", "#22c55e"),
    (56, "ACCUMULATE (DCA)", "#84cc16"),
    (46, "HOLD / WAIT", "#eab308"),
    (36, "PATIENT / LIGHT", "#f97316"),
    (0, "AVOID / TRIM", "#ef4444"),
)


def verdict_for(score: float) -> tuple[str, str]:
    """Return the ``(label, hex_color)`` verdict for a 0-100 score."""
    for lower, label, color in VERDICT_BANDS:
        if score >= lower:
            return label, color
    return VERDICT_BANDS[-1][1], VERDICT_BANDS[-1][2]
