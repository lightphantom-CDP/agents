"""Turn raw data into a 0-100 "is this a good price to add?" score.

The philosophy is deliberately Buffett-leaning:

* **Valuation (35%)** - what you pay decides your return. Cheaper quality = higher.
* **Dip / margin of safety (30%)** - "be greedy when others are fearful"; buying
  below recent highs and below the 50-day line scores better than chasing.
* **Trend / quality (20%)** - a business above its 200-day line is compounding;
  a badly broken trend is a yellow flag (value trap risk), not a bargain.
* **Timing (15%)** - RSI keeps us from buying something wildly overbought.

Valuation is the only component that can be missing (if fundamentals fail to
load); when that happens its weight is redistributed across the others.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Asset, SCORE_WEIGHTS, verdict_for
from .datasource import Quote
from .indicators import Indicators, compute_indicators


def interpolate(anchors: tuple[tuple[float, float], ...], x: float) -> float:
    """Piecewise-linear interpolation over ``(x, y)`` anchors, clamped at the ends."""
    if x <= anchors[0][0]:
        return anchors[0][1]
    if x >= anchors[-1][0]:
        return anchors[-1][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= x <= x1:
            span = x1 - x0
            if span == 0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / span
    return anchors[-1][1]


_DIP_ANCHORS = ((0, 35), (5, 50), (10, 66), (15, 78), (22, 88), (30, 94), (45, 88))
_TREND_ANCHORS = ((-30, 28), (-15, 40), (-5, 54), (0, 66), (8, 79), (15, 71), (25, 60), (40, 50))
_RSI_ANCHORS = ((20, 95), (30, 88), (40, 74), (50, 60), (60, 46), (70, 32), (80, 18))


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def valuation_score(asset: Asset, quote: Quote) -> tuple[float | None, float | None, str]:
    """Return ``(score, pe_used, label)``; score is ``None`` when no P/E is available."""
    if asset.pe_metric == "forward":
        pe = quote.forward_pe or quote.trailing_pe
        label = "Fwd P/E" if quote.forward_pe else "P/E"
    else:
        pe = quote.trailing_pe or quote.forward_pe
        label = "P/E" if quote.trailing_pe else "Fwd P/E"
    if pe is None or pe <= 0:
        return None, None, label
    return _clamp(interpolate(asset.pe_anchors, pe)), pe, label


def dip_score(ind: Indicators) -> float:
    """Reward pullbacks from the 52w high and price sitting below the 50-day line."""
    drawdown = -ind.drawdown_from_high_pct  # positive % below the high
    base = interpolate(_DIP_ANCHORS, drawdown)
    if ind.dist_sma50_pct is not None:
        # Below the 50-day -> bonus (dip); stretched above it -> small penalty.
        adj = _clamp(-ind.dist_sma50_pct * 0.6, -8, 10)
        base += adj
    return _clamp(base)


def trend_score(ind: Indicators) -> float:
    """Healthy long-term uptrend is good; a broken 200-day trend is a caution."""
    if ind.dist_sma200_pct is None:
        return 60.0
    base = interpolate(_TREND_ANCHORS, ind.dist_sma200_pct)
    if ind.sma50 is not None and ind.sma200 is not None:
        base += 5 if ind.sma50 >= ind.sma200 else -6
    return _clamp(base)


def timing_score(ind: Indicators) -> float:
    """Lower RSI (oversold) scores higher; overbought scores lower."""
    if ind.rsi14 is None:
        return 55.0
    return _clamp(interpolate(_RSI_ANCHORS, ind.rsi14))


@dataclass
class AssetScore:
    """The scored result for one instrument."""

    asset: Asset
    quote: Quote
    ind: Indicators
    components: dict[str, float]
    overall: float
    verdict: str
    color: str
    pe_used: float | None
    pe_label: str
    reasons: list[str] = field(default_factory=list)


def _reasons(asset: Asset, quote: Quote, ind: Indicators, comps: dict, pe, pe_label) -> list[str]:
    out: list[str] = []
    if pe is not None:
        tag = "cheap" if comps["valuation"] >= 66 else ("fair" if comps["valuation"] >= 46 else "rich")
        out.append(f"{pe_label} {pe:.1f} - {tag}")
    dd = ind.drawdown_from_high_pct
    if dd <= -3:
        out.append(f"{abs(dd):.0f}% below 52w high - room to add")
    elif dd > -1.5:
        out.append("near 52w highs - less margin of safety")
    if ind.dist_sma200_pct is not None:
        if ind.dist_sma200_pct >= 0:
            out.append("above 200-day trend (healthy)")
        else:
            out.append(f"{abs(ind.dist_sma200_pct):.0f}% below 200-day (caution)")
    if ind.rsi14 is not None:
        if ind.rsi14 <= 40:
            out.append(f"RSI {ind.rsi14:.0f} - oversold")
        elif ind.rsi14 >= 70:
            out.append(f"RSI {ind.rsi14:.0f} - overbought")
    if quote.target_mean and quote.price:
        upside = (quote.target_mean / quote.price - 1.0) * 100.0
        out.append(f"analyst target ${quote.target_mean:,.0f} ({upside:+.0f}%)")
    return out


def score_asset(asset: Asset, quote: Quote) -> AssetScore | None:
    """Compute the full :class:`AssetScore`, or ``None`` if data is unusable."""
    if not quote.ok or not quote.closes:
        return None
    ind = compute_indicators(quote.closes, quote.price)
    val, pe_used, pe_label = valuation_score(asset, quote)
    comps: dict[str, float] = {
        "dip": dip_score(ind),
        "trend": trend_score(ind),
        "timing": timing_score(ind),
    }
    weights = dict(SCORE_WEIGHTS)
    if val is None:
        # Redistribute the valuation weight across the remaining components.
        missing = weights.pop("valuation")
        total = sum(weights.values())
        for k in weights:
            weights[k] += missing * weights[k] / total
    else:
        comps["valuation"] = val

    overall = sum(weights[k] * comps[k] for k in comps)
    verdict, color = verdict_for(overall)
    return AssetScore(
        asset=asset,
        quote=quote,
        ind=ind,
        components=comps,
        overall=round(overall, 1),
        verdict=verdict,
        color=color,
        pe_used=pe_used,
        pe_label=pe_label,
        reasons=_reasons(asset, quote, ind, comps, pe_used, pe_label),
    )


@dataclass
class Portfolio:
    """Aggregate view across the whole watchlist."""

    scores: list[AssetScore]
    overall: float
    verdict: str
    color: str
    allocation: dict[str, float]  # suggested split of a *new* contribution (%)


def build_portfolio(scores: list[AssetScore]) -> Portfolio:
    """Aggregate scores and suggest how to split a fresh contribution."""
    if not scores:
        return Portfolio([], 0.0, "NO DATA", "#6b7280", {})
    overall = sum(s.overall for s in scores) / len(scores)
    verdict, color = verdict_for(overall)

    # Only names scoring above HOLD (46) earn fresh money, weighted by how far
    # above the line they are. If none qualify, steer everything to the core (SPY).
    weights = {s.asset.symbol: max(s.overall - 46, 0.0) for s in scores}
    total = sum(weights.values())
    if total <= 0:
        alloc = {s.asset.symbol: (100.0 if s.asset.symbol == "SPY" else 0.0) for s in scores}
    else:
        alloc = {k: round(v / total * 100.0, 1) for k, v in weights.items()}
    return Portfolio(scores, round(overall, 1), verdict, color, alloc)
