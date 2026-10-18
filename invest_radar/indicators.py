"""Pure-Python technical indicators computed from a list of daily closes.

No numpy/pandas: the watchlist is tiny and the series are short, so plain lists
keep the dependency footprint at zero beyond the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass


def sma(values: list[float], window: int) -> float | None:
    """Simple moving average of the last ``window`` values, or ``None`` if short."""
    if window <= 0 or len(values) < window:
        return None
    return sum(values[-window:]) / window


def rsi(values: list[float], period: int = 14) -> float | None:
    """Wilder's Relative Strength Index over ``period`` closes (0-100)."""
    if len(values) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def pct_return(values: list[float], lookback: int) -> float | None:
    """Percentage return over ``lookback`` sessions (e.g. 63 ~= 3 months)."""
    if len(values) <= lookback or values[-1 - lookback] == 0:
        return None
    return (values[-1] / values[-1 - lookback] - 1.0) * 100.0


@dataclass
class Indicators:
    """Snapshot of technical readings for one instrument."""

    price: float
    sma50: float | None
    sma200: float | None
    rsi14: float | None
    high_52w: float
    low_52w: float
    drawdown_from_high_pct: float
    range_position_pct: float  # 0 = at 52w low, 100 = at 52w high
    dist_sma50_pct: float | None
    dist_sma200_pct: float | None
    mom_3m_pct: float | None
    mom_6m_pct: float | None


def compute_indicators(closes: list[float], price: float | None = None) -> Indicators:
    """Compute the full :class:`Indicators` snapshot from a series of closes.

    Args:
        closes: Daily closing prices, oldest first.
        price: Optional latest (intraday) price; defaults to the last close.
    """
    if not closes:
        raise ValueError("closes must not be empty")
    px = float(price if price is not None else closes[-1])
    window = closes[-252:] if len(closes) >= 252 else closes
    high_52w = max(window)
    low_52w = min(window)
    drawdown = (px / high_52w - 1.0) * 100.0 if high_52w else 0.0
    rng = high_52w - low_52w
    range_pos = ((px - low_52w) / rng * 100.0) if rng > 0 else 50.0
    s50 = sma(closes, 50)
    s200 = sma(closes, 200)
    return Indicators(
        price=px,
        sma50=s50,
        sma200=s200,
        rsi14=rsi(closes, 14),
        high_52w=high_52w,
        low_52w=low_52w,
        drawdown_from_high_pct=drawdown,
        range_position_pct=range_pos,
        dist_sma50_pct=((px / s50 - 1.0) * 100.0) if s50 else None,
        dist_sma200_pct=((px / s200 - 1.0) * 100.0) if s200 else None,
        mom_3m_pct=pct_return(closes, 63),
        mom_6m_pct=pct_return(closes, 126),
    )
