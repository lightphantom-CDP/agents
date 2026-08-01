"""Turn a price snapshot into a 0-100 "good time to buy right now" score.

The philosophy is deliberately Buffett-flavoured rather than day-trading:

* Be greedy when others are fearful -> reward discounts from the highs and
  oversold conditions.
* Insist on a margin of safety -> reward cheapness within the 52-week range.
* Avoid falling knives and froth -> a trend/quality filter tempers both deep
  downtrends and wildly extended prices.
* You cannot time the market -> the score tilts *how much* to add via
  dollar-cost-averaging, it is never a promise or a trading signal.

A high score means "today looks like a relatively good entry", not "this will
go up". For a broad index the right long-run action is almost always to keep
buying; the score mostly matters for sizing single-stock additions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config, indicators
from .data import AssetSnapshot


@dataclass
class AssetScore:
    symbol: str
    name: str
    kind: str
    currency: str
    price: float
    score: float
    action: str
    subscores: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, float | None] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def linmap(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linearly map ``x`` from range [x0, x1] onto [y0, y1], then clamp."""
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    t = max(0.0, min(1.0, t))
    return y0 + t * (y1 - y0)


def _pick_moving_averages(closes: list[float]) -> tuple[float | None, int, float | None, int]:
    """Choose the best available long/short moving averages for the data length."""
    long_window = next((w for w in (200, 150, 100, 50) if len(closes) >= w), 0)
    short_window = next((w for w in (50, 20, 10) if len(closes) >= w and w < long_window), 0)
    sma_long = indicators.simple_moving_average(closes, long_window) if long_window else None
    sma_short = indicators.simple_moving_average(closes, short_window) if short_window else None
    return sma_long, long_window, sma_short, short_window


def _value_in_range_score(price: float, low: float | None, high: float | None) -> tuple[float, float | None]:
    rp = indicators.range_position(price, low, high) if (low and high) else None
    if rp is None:
        return 50.0, None
    return clamp((1.0 - rp) * 100.0), rp


def _drawdown_score(price: float, high: float | None) -> tuple[float, float | None]:
    dd = indicators.drawdown_from_high(price, high) if high else None
    if dd is None:
        return 50.0, None
    if dd >= 0:  # at or above the prior high -> no discount on offer
        return clamp(linmap(dd, 0.0, 0.05, 35.0, 22.0), 20.0, 35.0), dd
    return clamp(linmap(dd, 0.0, -0.35, 35.0, 100.0), 35.0, 100.0), dd


def _rsi_score(value: float | None) -> float:
    if value is None:
        return 50.0
    if value <= 30.0:
        return clamp(linmap(value, 10.0, 30.0, 100.0, 90.0), 88.0, 100.0)
    if value <= 50.0:
        return linmap(value, 30.0, 50.0, 90.0, 55.0)
    if value <= 70.0:
        return linmap(value, 50.0, 70.0, 55.0, 18.0)
    return clamp(linmap(value, 70.0, 85.0, 18.0, 5.0), 5.0, 18.0)


def _trend_score(price: float, sma_long: float | None) -> tuple[float, float | None]:
    if sma_long is None:
        return 55.0, None
    dist = indicators.pct_distance(price, sma_long)
    if dist is None:
        return 55.0, None
    if dist >= 0:  # in a long-term uptrend; far above == extended/expensive
        return clamp(linmap(dist, 0.0, 0.40, 100.0, 50.0), 45.0, 100.0), dist
    # below the long-term trend: could be value, could be a falling knife
    return clamp(linmap(dist, 0.0, -0.30, 65.0, 20.0), 20.0, 65.0), dist


def _pullback_score(
    price: float, sma_short: float | None, sma_long: float | None
) -> tuple[float, float | None]:
    if sma_short is None:
        return 50.0, None
    dist = indicators.pct_distance(price, sma_short)
    if dist is None:
        return 50.0, None
    uptrend = (sma_long is not None and price >= sma_long) or (
        sma_long is not None and sma_short >= sma_long
    )
    if uptrend:
        if dist < 0:  # a dip inside an uptrend -> the classic "buy the dip"
            return clamp(linmap(dist, 0.0, -0.12, 70.0, 100.0), 70.0, 100.0), dist
        return clamp(linmap(dist, 0.0, 0.15, 65.0, 40.0), 40.0, 65.0), dist
    if dist < 0:  # weak, and below its short-term average: risky
        return clamp(linmap(dist, 0.0, -0.15, 50.0, 30.0), 30.0, 50.0), dist
    return 45.0, dist


def action_for(score: float) -> str:
    for threshold, label in config.ACTION_THRESHOLDS:
        if score >= threshold:
            return label
    return config.ACTION_THRESHOLDS[-1][1]


def score_asset(snapshot: AssetSnapshot, asset: config.Asset | None = None) -> AssetScore:
    """Compute the buy score and supporting metrics for one asset."""
    closes = snapshot.closes
    high = snapshot.fifty_two_week_high
    low = snapshot.fifty_two_week_low
    price = snapshot.price

    sma_long, long_window, sma_short, short_window = _pick_moving_averages(closes)
    rsi_value = indicators.rsi(closes, 14)
    volatility = indicators.annualized_volatility(closes)

    value_score, range_pos = _value_in_range_score(price, low, high)
    drawdown_score, drawdown = _drawdown_score(price, high)
    rsi_sub = _rsi_score(rsi_value)
    trend_sub, dist_long = _trend_score(price, sma_long)
    pullback_sub, dist_short = _pullback_score(price, sma_short, sma_long)

    subscores = {
        "value_in_range": value_score,
        "drawdown": drawdown_score,
        "rsi": rsi_sub,
        "trend": trend_sub,
        "pullback": pullback_sub,
    }
    total = clamp(sum(config.SCORE_WEIGHTS[k] * v for k, v in subscores.items()))

    metrics: dict[str, float | None] = {
        "range_position": range_pos,
        "drawdown_from_high": drawdown,
        "rsi": rsi_value,
        "sma_long": sma_long,
        "sma_long_window": float(long_window) if long_window else None,
        "sma_short": sma_short,
        "sma_short_window": float(short_window) if short_window else None,
        "dist_from_sma_long": dist_long,
        "dist_from_sma_short": dist_short,
        "annualized_volatility": volatility,
        "change_pct": snapshot.last_change_pct,
    }

    return AssetScore(
        symbol=snapshot.symbol,
        name=asset.name if asset else snapshot.name,
        kind=asset.kind if asset else "stock",
        currency=snapshot.currency,
        price=price,
        score=round(total, 1),
        action=action_for(total),
        subscores={k: round(v, 1) for k, v in subscores.items()},
        metrics=metrics,
        rationale=_rationale(price, high, drawdown, range_pos, rsi_value, dist_long, long_window, volatility),
    )


def _rationale(
    price: float,
    high: float | None,
    drawdown: float | None,
    range_pos: float | None,
    rsi_value: float | None,
    dist_long: float | None,
    long_window: int,
    volatility: float | None,
) -> list[str]:
    notes: list[str] = []
    if drawdown is not None:
        if drawdown <= -0.005:
            notes.append(f"{abs(drawdown) * 100:.0f}% below its 52-week high (a discount)")
        else:
            notes.append("at/near its 52-week high (little discount on offer)")
    if range_pos is not None:
        notes.append(f"sits at {range_pos * 100:.0f}% of its 52-week range")
    if rsi_value is not None:
        if rsi_value < 30:
            tag = "oversold"
        elif rsi_value > 70:
            tag = "overbought"
        else:
            tag = "neutral"
        notes.append(f"RSI {rsi_value:.0f} ({tag})")
    if dist_long is not None and long_window:
        direction = "above" if dist_long >= 0 else "below"
        notes.append(f"{abs(dist_long) * 100:.0f}% {direction} its {long_window}-day average")
    if volatility is not None:
        notes.append(f"~{volatility * 100:.0f}% annualised volatility")
    return notes
