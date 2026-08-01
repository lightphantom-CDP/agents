"""Technical indicators implemented in pure Python (no numpy/pandas).

All functions take a chronological list of prices (oldest first) and return
``None`` when there is not enough data, so callers can degrade gracefully.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def simple_moving_average(prices: Sequence[float], window: int) -> float | None:
    """Average of the most recent ``window`` prices."""
    if window <= 0 or len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def rsi(prices: Sequence[float], period: int = 14) -> float | None:
    """Wilder's Relative Strength Index over ``period`` days.

    Returns a value in [0, 100]; < 30 is commonly "oversold", > 70
    "overbought".
    """
    if len(prices) < period + 1:
        return None

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def range_position(price: float, low: float, high: float) -> float | None:
    """Where ``price`` sits within [low, high], as a fraction in [0, 1].

    0 == at the 52-week low (cheap), 1 == at the high (expensive).
    """
    if high is None or low is None or high <= low:
        return None
    return _clamp((price - low) / (high - low), 0.0, 1.0)


def drawdown_from_high(price: float, high: float) -> float | None:
    """Fractional distance below the high (e.g. -0.20 == 20% below the high)."""
    if not high:
        return None
    return (price - high) / high


def pct_distance(price: float, reference: float | None) -> float | None:
    """Fractional distance of ``price`` from ``reference``."""
    if not reference:
        return None
    return (price - reference) / reference


def annualized_volatility(prices: Sequence[float], lookback: int = 63) -> float | None:
    """Annualised volatility from daily returns over ``lookback`` days."""
    window = prices[-(lookback + 1):]
    if len(window) < 3:
        return None
    returns = [
        (window[i] - window[i - 1]) / window[i - 1]
        for i in range(1, len(window))
        if window[i - 1]
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
