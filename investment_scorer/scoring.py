"""The scoring engine.

Two independent 0-100 sub-scores are produced and then blended:

* **Timing** - "is *now* a decent price?" (RSI, position in the 52-week range,
  discount to the 200-day trend, drawdown from the high).
* **Quality / value** - the Buffett lens: durable returns on equity, fat
  margins, low debt, real free cash flow, a fair multiple, ongoing growth.

Every factor maps its raw metric through a transparent piece-wise-linear curve
so the reasoning is auditable, and any missing input is dropped with the
remaining weights renormalised (never silently treated as zero).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import (
    COMPOSITE_BLEND,
    QUALITY_WEIGHTS,
    TIMING_WEIGHTS,
    VERDICT_BANDS,
    Holding,
    VerdictBand,
)
from .indicators import TechnicalSnapshot


@dataclass
class FactorScore:
    name: str
    score: float | None
    detail: str


@dataclass
class HoldingScore:
    holding: Holding
    price: float | None = None
    currency: str = "USD"
    timing_score: float | None = None
    quality_score: float | None = None
    composite: float | None = None
    verdict: VerdictBand | None = None
    timing_factors: list[FactorScore] = field(default_factory=list)
    quality_factors: list[FactorScore] = field(default_factory=list)
    snapshot: TechnicalSnapshot | None = None
    fundamentals: dict[str, float] = field(default_factory=dict)
    analyst_upside: float | None = None
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def good_price_now(self) -> str:
        if self.composite is None:
            return "unknown"
        if self.composite >= 62:
            return "yes"
        if self.composite >= 46:
            return "okay (keep DCAing)"
        return "not really (be patient)"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def interp(x: float, points: list[tuple[float, float]]) -> float:
    """Piece-wise-linear interpolation, clamped at both ends.

    ``points`` must be sorted ascending by x.
    """
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


def _weighted(components: list[tuple[float, float | None]]) -> float | None:
    """Weighted mean over the components whose score is not ``None``.

    Each component is ``(weight, score)``. Weights of present components are
    renormalised so a couple of missing inputs don't drag the result to zero.
    """
    present = [(w, s) for w, s in components if s is not None]
    total_w = sum(w for w, _ in present)
    if total_w <= 0:
        return None
    return sum(w * s for w, s in present) / total_w


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


# --------------------------------------------------------------------------- #
# timing
# --------------------------------------------------------------------------- #
def score_timing(snap: TechnicalSnapshot) -> tuple[float | None, list[FactorScore]]:
    factors: list[FactorScore] = []

    rsi_score = None
    if snap.rsi14 is not None:
        rsi_score = interp(
            snap.rsi14,
            [(20, 100), (30, 90), (45, 68), (55, 50), (70, 25), (80, 8)],
        )
    factors.append(FactorScore("RSI(14)", rsi_score, f"RSI {_fmt_num(snap.rsi14, 1)}"))

    range_score = None
    if snap.range_position is not None:
        range_score = interp(
            snap.range_position,
            [(0.0, 100), (0.2, 88), (0.4, 70), (0.6, 50), (0.8, 28), (1.0, 10)],
        )
    factors.append(
        FactorScore(
            "52w range position",
            range_score,
            f"{_fmt_pct(snap.range_position)} of 52w range",
        )
    )

    sma_score = None
    if snap.vs_sma200 is not None:
        sma_score = interp(
            snap.vs_sma200,
            [(0.80, 100), (0.90, 92), (0.97, 75), (1.0, 62), (1.10, 42), (1.25, 22), (1.5, 8)],
        )
    factors.append(
        FactorScore(
            "Price vs 200d avg",
            sma_score,
            f"{_fmt_num(snap.vs_sma200)}x the 200-day average" if snap.vs_sma200 else "n/a",
        )
    )

    dd_score = None
    if snap.drawdown_from_high is not None:
        dd_score = interp(
            snap.drawdown_from_high,
            [(0.0, 25), (0.05, 40), (0.12, 60), (0.20, 78), (0.30, 92), (0.45, 100)],
        )
    factors.append(
        FactorScore(
            "Drawdown from 52w high",
            dd_score,
            f"{_fmt_pct(snap.drawdown_from_high)} below high",
        )
    )

    score = _weighted(
        [
            (TIMING_WEIGHTS["rsi"], rsi_score),
            (TIMING_WEIGHTS["range_position"], range_score),
            (TIMING_WEIGHTS["vs_sma200"], sma_score),
            (TIMING_WEIGHTS["drawdown"], dd_score),
        ]
    )
    return score, factors


# --------------------------------------------------------------------------- #
# quality / value (the Buffett lens)
# --------------------------------------------------------------------------- #
def score_quality(
    f: dict[str, float], kind: str
) -> tuple[float | None, list[FactorScore]]:
    factors: list[FactorScore] = []

    # -- Return on equity ------------------------------------------------- #
    roe = f.get("roe")
    roe_score = (
        interp(roe, [(0.0, 10), (0.08, 35), (0.12, 55), (0.15, 70), (0.20, 85), (0.30, 97), (0.45, 100)])
        if roe is not None
        else None
    )
    factors.append(FactorScore("Return on equity", roe_score, _fmt_pct(roe)))

    # -- Margins ---------------------------------------------------------- #
    margin = f.get("profit_margin")
    margin_score = (
        interp(margin, [(0.0, 15), (0.05, 40), (0.10, 58), (0.15, 72), (0.25, 90), (0.35, 100)])
        if margin is not None
        else None
    )
    factors.append(FactorScore("Net profit margin", margin_score, _fmt_pct(margin)))

    # -- Leverage --------------------------------------------------------- #
    dte = f.get("debt_to_equity")
    dte_norm = dte
    if dte is not None and dte < 5:  # occasionally reported as a raw ratio
        dte_norm = dte * 100
    dte_score = (
        interp(dte_norm, [(0, 100), (30, 90), (60, 74), (100, 55), (150, 38), (200, 22), (300, 8)])
        if dte_norm is not None
        else None
    )
    factors.append(
        FactorScore(
            "Debt / equity",
            dte_score,
            f"{_fmt_num(dte_norm, 0)}%" if dte_norm is not None else "n/a",
        )
    )

    # -- Free cash flow --------------------------------------------------- #
    fcf = f.get("free_cashflow")
    mcap = f.get("market_cap")
    fcf_score = None
    fcf_detail = "n/a"
    if fcf is not None and mcap and mcap > 0:
        fcf_yield = fcf / mcap
        fcf_detail = f"FCF yield {_fmt_pct(fcf_yield)}"
        if fcf_yield <= 0:
            fcf_score = 12.0
        else:
            fcf_score = interp(fcf_yield, [(0.0, 30), (0.02, 55), (0.04, 75), (0.06, 90), (0.08, 100)])
    elif fcf is not None:
        fcf_score = 100.0 if fcf > 0 else 12.0
        fcf_detail = "positive" if fcf > 0 else "negative"
    factors.append(FactorScore("Free cash flow", fcf_score, fcf_detail))

    # -- Valuation (P/E, PEG, P/B) --------------------------------------- #
    pe = f.get("forward_pe") or f.get("trailing_pe")
    pe_score = (
        interp(pe, [(10, 100), (15, 88), (20, 72), (25, 58), (30, 45), (40, 28), (60, 12), (100, 5)])
        if pe is not None
        else None
    )
    peg = f.get("peg_ratio")
    peg_score = (
        interp(peg, [(0.5, 100), (1.0, 85), (1.5, 62), (2.0, 45), (3.0, 22), (4.0, 10)])
        if peg is not None and peg > 0
        else None
    )
    pb = f.get("price_to_book")
    pb_score = (
        interp(pb, [(1, 95), (2, 80), (4, 60), (6, 45), (10, 25), (20, 10)])
        if pb is not None and pb > 0
        else None
    )
    valuation_score = _weighted([(0.5, pe_score), (0.3, peg_score), (0.2, pb_score)])
    val_bits = []
    if pe is not None:
        val_bits.append(f"P/E {_fmt_num(pe, 1)}")
    if peg is not None and peg > 0:
        val_bits.append(f"PEG {_fmt_num(peg, 2)}")
    if pb is not None and pb > 0:
        val_bits.append(f"P/B {_fmt_num(pb, 1)}")
    factors.append(
        FactorScore("Valuation", valuation_score, ", ".join(val_bits) if val_bits else "n/a")
    )

    # -- Growth ----------------------------------------------------------- #
    growth_inputs = [f.get("revenue_growth"), f.get("earnings_growth")]
    growth_vals = [g for g in growth_inputs if g is not None]
    growth = sum(growth_vals) / len(growth_vals) if growth_vals else None
    growth_score = (
        interp(growth, [(-0.10, 15), (0.0, 40), (0.05, 58), (0.10, 70), (0.20, 88), (0.35, 100)])
        if growth is not None
        else None
    )
    factors.append(FactorScore("Growth", growth_score, _fmt_pct(growth)))

    if kind == "index":
        # A broad fund has no single ROE/margin/debt story - lean on how richly
        # the whole market is priced.
        score = _weighted([(0.7, valuation_score), (0.3, growth_score)])
    else:
        score = _weighted(
            [
                (QUALITY_WEIGHTS["roe"], roe_score),
                (QUALITY_WEIGHTS["margins"], margin_score),
                (QUALITY_WEIGHTS["debt"], dte_score),
                (QUALITY_WEIGHTS["fcf"], fcf_score),
                (QUALITY_WEIGHTS["valuation"], valuation_score),
                (QUALITY_WEIGHTS["growth"], growth_score),
            ]
        )
    return score, factors


# --------------------------------------------------------------------------- #
# composite + verdict
# --------------------------------------------------------------------------- #
def verdict_for(score: float) -> VerdictBand:
    for band in VERDICT_BANDS:
        if score >= band.floor:
            return band
    return VERDICT_BANDS[-1]


def build_score(
    holding: Holding,
    snapshot: TechnicalSnapshot,
    fundamentals: dict[str, float],
) -> HoldingScore:
    result = HoldingScore(holding=holding, snapshot=snapshot, fundamentals=fundamentals)
    result.price = snapshot.price

    timing_score, timing_factors = score_timing(snapshot)
    quality_score, quality_factors = score_quality(fundamentals, holding.kind)
    result.timing_score = timing_score
    result.quality_score = quality_score
    result.timing_factors = timing_factors
    result.quality_factors = quality_factors

    blend = COMPOSITE_BLEND[holding.kind if holding.kind in COMPOSITE_BLEND else "stock"]
    composite = _weighted(
        [(blend["quality"], quality_score), (blend["timing"], timing_score)]
    )
    result.composite = composite
    if composite is not None:
        result.verdict = verdict_for(composite)

    # Analyst-implied margin of safety (context only, not a core factor).
    target = fundamentals.get("target_mean_price")
    if target and result.price:
        result.analyst_upside = (target - result.price) / result.price

    # Human-friendly notes.
    if holding.kind == "index":
        result.notes.append(
            "Buffett's advice for a broad index is to buy steadily over time - "
            "regular contributions matter far more than perfect timing."
        )
    if snapshot.drawdown_from_high is not None and snapshot.drawdown_from_high >= 0.20:
        result.notes.append(
            f"Trading {snapshot.drawdown_from_high * 100:.0f}% below its 52-week high - "
            "a fearful market can be a friend to patient buyers of quality."
        )
    if quality_score is not None and quality_score >= 75 and (composite or 0) < 46:
        result.notes.append(
            "High-quality business but the price looks full - a great company is "
            "not always a great buy today."
        )
    return result
