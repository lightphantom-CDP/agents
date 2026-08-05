"""The scoring engine.

Turns a :class:`~investment_scorer.data.PriceSeries` into a single 0-100
"is now a good price to add?" score, built from four transparent pillars:

* **Valuation (margin of safety)** - are we buying on sale? Uses the position
  inside the 52-week range and the discount from the 52-week high (a robust,
  always-available proxy for "be greedy when others are fearful"), optionally
  blended with the trailing/forward P/E when fundamentals are available.
* **Technical timing** - RSI, distance from the 200-day average and MACD.
* **Trend / quality** - is the durable long-term uptrend still intact? A great
  business in a healthy uptrend is what we want to buy the dips *of*.
* **Momentum / pullback** - rewards a healthy pullback (roughly 5-20% off the
  highs) over both "already at all-time highs" and "falling knife" extremes.

The pillars deliberately pull against each other, so the top scores land on a
pullback inside an intact uptrend - a patient investor's fat pitch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import indicators as ind
from .config import ScoreWeights, label_for_score
from .data import PriceSeries


# --------------------------------------------------------------------------- #
# Small numeric helpers
# --------------------------------------------------------------------------- #
def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def linear_map(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    """Map ``x`` from the [x0,x1] domain onto [y0,y1], clamped to that range."""
    if x1 == x0:
        return (y0 + y1) / 2.0
    t = (x - x0) / (x1 - x0)
    t = max(0.0, min(1.0, t))
    return y0 + t * (y1 - y0)


def piecewise(x: float, points: Sequence[Tuple[float, float]]) -> float:
    """Piecewise-linear interpolation across (x, y) control points."""
    pts = sorted(points)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return linear_map(x, x0, y0, x1, y1)
    return pts[-1][1]


def _pe_to_score(pe: Optional[float]) -> Optional[float]:
    """Map a price/earnings ratio to a 0-100 'cheapness' score."""
    if pe is None or pe <= 0:
        return None
    return clamp(piecewise(pe, [
        (10, 100), (15, 88), (20, 72), (25, 60),
        (30, 50), (40, 34), (55, 18), (80, 6),
    ]))


# --------------------------------------------------------------------------- #
# Result containers
# --------------------------------------------------------------------------- #
@dataclass
class ScoreComponent:
    name: str
    score: float           # 0-100
    weight: float          # 0-1
    detail: str            # human-readable reading


@dataclass
class ScoreResult:
    symbol: str
    name: str
    price: float
    currency: str
    composite: float
    label: str
    headline: str
    components: List[ScoreComponent] = field(default_factory=list)
    signals: Dict[str, Optional[float]] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)
    confidence: str = "high"
    source: str = "yahoo"
    stale: bool = False

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": round(self.price, 2),
            "currency": self.currency,
            "composite_score": round(self.composite, 1),
            "recommendation": self.label,
            "headline": self.headline,
            "components": [
                {
                    "name": c.name,
                    "score": round(c.score, 1),
                    "weight": c.weight,
                    "detail": c.detail,
                }
                for c in self.components
            ],
            "signals": {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in self.signals.items()
            },
            "rationale": self.rationale,
            "confidence": self.confidence,
            "source": self.source,
            "stale": self.stale,
        }


# --------------------------------------------------------------------------- #
# Individual pillars
# --------------------------------------------------------------------------- #
def _valuation_pillar(s: PriceSeries) -> Tuple[float, str]:
    closes = s.closes
    high = s.fifty_two_week_high or (max(closes) if closes else s.price)
    low = s.fifty_two_week_low or (min(closes) if closes else s.price)

    range_pos = ind.range_position(s.price, low, high)
    if range_pos is None:
        range_pos = 0.5
    # Cheaper inside the 52-week range -> higher score.
    v_range = linear_map(range_pos, 0.05, 92, 0.95, 18)

    discount = max(0.0, (high - s.price) / high) if high else 0.0
    v_discount = linear_map(discount, 0.0, 45, 0.30, 95)

    price_val = 0.6 * v_range + 0.4 * v_discount
    detail = (
        f"{range_pos * 100:.0f}% up its 52-wk range, "
        f"{discount * 100:.1f}% below the 52-wk high"
    )

    pe_score = _pe_to_score(s.fundamentals.trailing_pe or s.fundamentals.forward_pe)
    if pe_score is not None:
        price_val = 0.5 * price_val + 0.5 * pe_score
        pe_used = s.fundamentals.trailing_pe or s.fundamentals.forward_pe
        detail += f"; P/E {pe_used:.1f}"
    return clamp(price_val), detail


def _technical_pillar(s: PriceSeries) -> Tuple[float, str, Dict[str, Optional[float]]]:
    closes = s.closes
    rsi = ind.rsi(closes, 14)
    sma200 = ind.sma(closes, 200) or ind.sma(closes, min(len(closes), 150))
    macd = ind.macd(closes)

    rsi_score = 50.0 if rsi is None else linear_map(rsi, 20, 100, 80, 5)

    if sma200 and sma200 > 0:
        dist200 = s.price / sma200 - 1.0
        dist_score = linear_map(dist200, -0.12, 92, 0.25, 12)
    else:
        dist200 = None
        dist_score = 50.0

    if macd is not None:
        _, _, hist = macd
        macd_score = 68.0 if hist > 0 else 38.0
    else:
        hist = None
        macd_score = 50.0

    score = 0.45 * rsi_score + 0.40 * dist_score + 0.15 * macd_score
    detail_bits = []
    if rsi is not None:
        detail_bits.append(f"RSI {rsi:.0f}")
    if dist200 is not None:
        detail_bits.append(f"{dist200 * 100:+.1f}% vs 200DMA")
    if hist is not None:
        detail_bits.append("MACD up" if hist > 0 else "MACD down")
    signals = {"rsi": rsi, "sma200": sma200, "dist_200dma": dist200,
               "macd_hist": hist}
    return clamp(score), ", ".join(detail_bits) or "insufficient history", signals


def _trend_pillar(s: PriceSeries) -> Tuple[float, str, Dict[str, Optional[float]]]:
    closes = s.closes
    sma50 = ind.sma(closes, 50)
    sma200 = ind.sma(closes, 200) or ind.sma(closes, min(len(closes), 150))
    mom6 = ind.pct_change(closes, 126)

    above200 = sma200 is not None and s.price > sma200
    golden = (sma50 is not None and sma200 is not None and sma50 > sma200)

    score = 50.0
    score += 22 if above200 else -25
    if sma50 is not None and sma200 is not None:
        score += 12 if golden else -12
    if mom6 is not None:
        score += linear_map(mom6, -0.25, -15, 0.35, 15)

    detail = (
        f"{'above' if above200 else 'below'} 200DMA, "
        f"{'50>200 (golden)' if golden else '50<200 (weak)'}"
    )
    if mom6 is not None:
        detail += f", 6-mo {mom6 * 100:+.0f}%"
    signals = {"sma50": sma50, "above_200dma": 1.0 if above200 else 0.0,
               "golden_cross": 1.0 if golden else 0.0, "return_6m": mom6}
    return clamp(score), detail, signals


def _momentum_pillar(s: PriceSeries) -> Tuple[float, str, Dict[str, Optional[float]]]:
    closes = s.closes
    dd = ind.current_drawdown(closes)          # <= 0
    mom1 = ind.pct_change(closes, 21)

    if dd is None:
        return 50.0, "insufficient history", {"drawdown": None, "return_1m": mom1}

    magnitude = -dd  # positive depth of the pullback
    # Tent function: healthy 5-20% dips score best; extremes score lower.
    pull = piecewise(magnitude, [
        (0.00, 45), (0.05, 72), (0.12, 90), (0.20, 86),
        (0.30, 64), (0.45, 40), (0.60, 26),
    ])
    # A slightly negative 1-month move inside an uptrend is a classic entry.
    if mom1 is not None:
        pull += linear_map(mom1, -0.15, 8, 0.15, -8)
    detail = f"{dd * 100:.1f}% off highs"
    if mom1 is not None:
        detail += f", 1-mo {mom1 * 100:+.1f}%"
    return clamp(pull), detail, {"drawdown": dd, "return_1m": mom1}


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def score_series(series: PriceSeries, weights: Optional[ScoreWeights] = None) -> ScoreResult:
    weights = weights or ScoreWeights()

    val_score, val_detail = _valuation_pillar(series)
    tech_score, tech_detail, tech_sig = _technical_pillar(series)
    trend_score, trend_detail, trend_sig = _trend_pillar(series)
    mom_score, mom_detail, mom_sig = _momentum_pillar(series)

    components = [
        ScoreComponent("Valuation (margin of safety)", val_score, weights.valuation, val_detail),
        ScoreComponent("Technical timing", tech_score, weights.technical, tech_detail),
        ScoreComponent("Trend / quality", trend_score, weights.trend, trend_detail),
        ScoreComponent("Momentum / pullback", mom_score, weights.momentum, mom_detail),
    ]

    total_w = sum(c.weight for c in components) or 1.0
    composite = sum(c.score * c.weight for c in components) / total_w
    label, band_reason = label_for_score(composite)

    # Confidence reflects how much real data we had.
    if series.stale:
        confidence = "low (offline fallback data)"
    elif series.source == "demo":
        confidence = "demo data"
    elif len(series.closes) < 60:
        confidence = "medium (short history)"
    else:
        confidence = "high"

    signals: Dict[str, Optional[float]] = {}
    signals.update(tech_sig)
    signals.update(trend_sig)
    signals.update(mom_sig)
    if series.day_change_pct is not None:
        signals["day_change"] = series.day_change_pct

    rationale = _build_rationale(series, components, composite)
    headline = _headline(series, composite, label, components)

    return ScoreResult(
        symbol=series.symbol,
        name=series.name,
        price=series.price,
        currency=series.currency,
        composite=composite,
        label=label,
        headline=headline,
        components=components,
        signals=signals,
        rationale=rationale,
        confidence=confidence,
        source=series.source,
        stale=series.stale,
    )


def _headline(series: PriceSeries, composite: float, label: str,
              components: List[ScoreComponent]) -> str:
    strongest = max(components, key=lambda c: c.score)
    weakest = min(components, key=lambda c: c.score)
    return (
        f"{series.name} scores {composite:.0f}/100 -> {label}. "
        f"Strongest pillar: {strongest.name.split(' (')[0]} ({strongest.score:.0f}); "
        f"weakest: {weakest.name.split(' (')[0]} ({weakest.score:.0f})."
    )


def _build_rationale(series: PriceSeries, components: List[ScoreComponent],
                     composite: float) -> List[str]:
    lines = [f"{c.name}: {c.score:.0f}/100 - {c.detail}." for c in components]
    if composite >= 66:
        lines.append("Buffett lens: quality appears reasonably priced - a sensible place to add.")
    elif composite >= 50:
        lines.append("Buffett lens: fair value - keep dollar-cost averaging rather than timing it.")
    else:
        lines.append("Buffett lens: not a bargain today - patience is a position; wait for a better price.")
    if series.stale:
        lines.append("NOTE: live data was unavailable; these figures use offline fallback data.")
    return lines
