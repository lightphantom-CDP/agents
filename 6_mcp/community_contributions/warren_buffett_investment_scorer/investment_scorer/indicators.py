"""Pure-Python technical indicators.

These operate on plain lists of floats (oldest first, newest last) so the whole
toolkit stays dependency-free. Every function guards against short/degenerate
inputs and returns ``None`` when it cannot be computed, which the scoring layer
handles gracefully.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple


def _clean(values: Sequence[Optional[float]]) -> List[float]:
    """Drop ``None`` gaps that Yahoo occasionally returns for holidays."""
    return [float(v) for v in values if v is not None]


def sma(values: Sequence[float], period: int) -> Optional[float]:
    """Simple moving average of the last ``period`` values."""
    vals = _clean(values)
    if len(vals) < period or period <= 0:
        return None
    return sum(vals[-period:]) / period


def ema_series(values: Sequence[float], period: int) -> List[float]:
    """Full exponential moving average series (seeded with an SMA)."""
    vals = _clean(values)
    if len(vals) < period or period <= 0:
        return []
    k = 2.0 / (period + 1.0)
    seed = sum(vals[:period]) / period
    out = [seed]
    for price in vals[period:]:
        out.append(price * k + out[-1] * (1.0 - k))
    return out


def ema(values: Sequence[float], period: int) -> Optional[float]:
    series = ema_series(values, period)
    return series[-1] if series else None


def rsi(values: Sequence[float], period: int = 14) -> Optional[float]:
    """Wilder's Relative Strength Index (0-100)."""
    vals = _clean(values)
    if len(vals) <= period:
        return None
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = vals[i] - vals[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    # Wilder smoothing for the remainder of the series.
    for i in range(period + 1, len(vals)):
        delta = vals[i] - vals[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Optional[Tuple[float, float, float]]:
    """Return the latest (macd_line, signal_line, histogram)."""
    vals = _clean(values)
    if len(vals) < slow + signal:
        return None
    fast_series = ema_series(vals, fast)
    slow_series = ema_series(vals, slow)
    # Align the two EMA series to the same (shorter) length.
    n = min(len(fast_series), len(slow_series))
    macd_line = [f - s for f, s in zip(fast_series[-n:], slow_series[-n:])]
    if len(macd_line) < signal:
        return None
    signal_series = ema_series(macd_line, signal)
    if not signal_series:
        return None
    latest_macd = macd_line[-1]
    latest_signal = signal_series[-1]
    return latest_macd, latest_signal, latest_macd - latest_signal


def current_drawdown(values: Sequence[float]) -> Optional[float]:
    """Percent below the trailing peak (0 at highs, negative in a drawdown)."""
    vals = _clean(values)
    if len(vals) < 2:
        return None
    peak = max(vals)
    if peak == 0:
        return None
    return (vals[-1] - peak) / peak


def range_position(price: float, low: float, high: float) -> Optional[float]:
    """Where ``price`` sits inside [low, high] as 0 (at low) .. 1 (at high)."""
    if high <= low:
        return None
    return max(0.0, min(1.0, (price - low) / (high - low)))


def daily_returns(values: Sequence[float]) -> List[float]:
    vals = _clean(values)
    out = []
    for i in range(1, len(vals)):
        prev = vals[i - 1]
        if prev:
            out.append((vals[i] - prev) / prev)
    return out


def annualized_volatility(values: Sequence[float]) -> Optional[float]:
    """Annualised stdev of daily returns (~252 trading days)."""
    rets = daily_returns(values)
    if len(rets) < 20:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


def pct_change(values: Sequence[float], lookback: int) -> Optional[float]:
    """Percent change over the last ``lookback`` bars."""
    vals = _clean(values)
    if len(vals) <= lookback or vals[-1 - lookback] == 0:
        return None
    return (vals[-1] - vals[-1 - lookback]) / vals[-1 - lookback]


def slope_pct(values: Sequence[float], lookback: int) -> Optional[float]:
    """Percentage slope of a value series over ``lookback`` bars.

    Used to judge whether the 200-day average itself is rising (trend intact).
    """
    vals = _clean(values)
    if len(vals) <= lookback:
        return None
    start = vals[-1 - lookback]
    if start == 0:
        return None
    return (vals[-1] - start) / start
