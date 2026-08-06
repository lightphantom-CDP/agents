"""Plain-Python technical indicators.

All functions operate on a list of closing prices (oldest first) and return
``None`` when there is not enough data, so the scorer can skip a factor cleanly
rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TechnicalSnapshot:
    price: float | None = None
    rsi14: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    range_position: float | None = None   # 0 = at 52w low, 1 = at 52w high
    drawdown_from_high: float | None = None  # positive fraction below 52w high
    return_1m: float | None = None
    return_3m: float | None = None
    vs_sma200: float | None = None  # price / sma200


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    return sum(values[-window:]) / window


def rsi(values: list[float], period: int = 14) -> float | None:
    """Wilder's RSI. Returns 0-100, or ``None`` if the series is too short."""
    if len(values) <= period:
        return None
    gains = 0.0
    losses = 0.0
    # Seed with the first ``period`` deltas.
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    # Wilder smoothing across the remainder.
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def pct_return(values: list[float], lookback: int) -> float | None:
    if len(values) <= lookback or lookback <= 0:
        return None
    past = values[-(lookback + 1)]
    if past == 0:
        return None
    return (values[-1] - past) / past


def build_snapshot(
    closes: list[float],
    price: float | None,
    high_52w: float | None,
    low_52w: float | None,
) -> TechnicalSnapshot:
    snap = TechnicalSnapshot(price=price)
    if not closes:
        snap.high_52w = high_52w
        snap.low_52w = low_52w
        return snap

    last = price if price is not None else closes[-1]
    snap.price = last

    # Fall back to the series extremes if Yahoo's meta lacked 52w figures.
    snap.high_52w = high_52w if high_52w else max(closes)
    snap.low_52w = low_52w if low_52w else min(closes)

    snap.rsi14 = rsi(closes, 14)
    snap.sma50 = sma(closes, 50)
    snap.sma200 = sma(closes, 200)

    if snap.high_52w and snap.low_52w and snap.high_52w > snap.low_52w:
        snap.range_position = (last - snap.low_52w) / (snap.high_52w - snap.low_52w)
        snap.range_position = max(0.0, min(1.0, snap.range_position))
    if snap.high_52w and snap.high_52w > 0:
        snap.drawdown_from_high = max(0.0, (snap.high_52w - last) / snap.high_52w)
    if snap.sma200 and snap.sma200 > 0:
        snap.vs_sma200 = last / snap.sma200

    # ~21 trading days per month, ~63 per quarter.
    snap.return_1m = pct_return(closes, 21)
    snap.return_3m = pct_return(closes, 63)
    return snap
