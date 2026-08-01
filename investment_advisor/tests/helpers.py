"""Synthetic data factories shared across the offline tests."""

from __future__ import annotations

from datetime import datetime, timezone

from investment_advisor.data import AssetSnapshot


def make_snapshot(
    symbol: str = "TEST",
    *,
    price: float = 100.0,
    closes: list[float] | None = None,
    high: float | None = 120.0,
    low: float | None = 80.0,
    previous_close: float | None = 99.0,
    name: str | None = None,
) -> AssetSnapshot:
    if closes is None:
        closes = [90.0 + (i % 10) for i in range(260)]
    return AssetSnapshot(
        symbol=symbol,
        name=name or symbol,
        currency="USD",
        price=price,
        previous_close=previous_close,
        market_time=datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc),
        market_state="CLOSED",
        fifty_two_week_high=high,
        fifty_two_week_low=low,
        closes=closes,
    )


def declining_series(n: int = 260, start: float = 200.0, step: float = 0.5) -> list[float]:
    """A steadily falling series -> pushes RSI low and price toward the lows."""
    return [start - step * i for i in range(n)]


def rising_series(n: int = 260, start: float = 100.0, step: float = 0.5) -> list[float]:
    """A steadily rising series -> pushes RSI high and price toward the highs."""
    return [start + step * i for i in range(n)]


def yahoo_payload(
    symbol: str = "TEST",
    *,
    price: float = 100.0,
    closes: list[float] | None = None,
    high: float = 120.0,
    low: float = 80.0,
    prev_close: float = 99.0,
    market_time: int = 1_785_528_000,
) -> dict:
    closes = closes if closes is not None else [95.0, 96.0, 97.0, 98.0, 100.0]
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "shortName": f"{symbol} Inc",
                        "currency": "USD",
                        "regularMarketPrice": price,
                        "previousClose": prev_close,
                        "chartPreviousClose": prev_close,
                        "fiftyTwoWeekHigh": high,
                        "fiftyTwoWeekLow": low,
                        "regularMarketTime": market_time,
                        "marketState": "CLOSED",
                    },
                    "timestamp": list(range(len(closes))),
                    "indicators": {"quote": [{"close": closes}]},
                }
            ],
        }
    }
