"""Market data access using only the Python standard library.

Data comes from Yahoo Finance's public chart endpoint, which needs no API
key. The network call (:func:`fetch_chart`) is kept separate from the pure
parsing logic (:func:`parse_chart`) so the parsing and everything downstream
can be unit tested offline with synthetic payloads.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import config


class DataError(RuntimeError):
    """Raised when market data cannot be fetched or parsed."""


@dataclass
class AssetSnapshot:
    """A point-in-time view of one instrument plus its recent price history."""

    symbol: str
    name: str
    currency: str
    price: float
    previous_close: float | None
    market_time: datetime | None
    market_state: str
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    closes: list[float] = field(default_factory=list)

    @property
    def last_change_pct(self) -> float | None:
        """Percent change of the latest price vs the prior close."""
        if self.previous_close in (None, 0):
            return None
        return (self.price - self.previous_close) / self.previous_close * 100.0


def _build_url(host: str, symbol: str, rng: str, interval: str) -> str:
    # Yahoo tickers such as ^GSPC or IDR=X need URL-encoding.
    safe_symbol = urllib.parse.quote(symbol, safe="")
    return (
        f"{host}/v8/finance/chart/{safe_symbol}"
        f"?range={rng}&interval={interval}&includePrePost=false"
    )


def fetch_chart(
    symbol: str,
    *,
    rng: str = "1y",
    interval: str = "1d",
    timeout: float | None = None,
    retries: int | None = None,
) -> dict:
    """Fetch the raw Yahoo chart JSON for ``symbol``.

    Tries both Yahoo hosts and retries with exponential backoff. Returns the
    decoded JSON payload; raises :class:`DataError` on repeated failure.
    """
    timeout = config.HTTP_TIMEOUT_SECONDS if timeout is None else timeout
    retries = config.HTTP_RETRIES if retries is None else retries

    last_error: Exception | None = None
    for attempt in range(retries):
        for host in config.YAHOO_HOSTS:
            url = _build_url(host, symbol, rng, interval)
            request = urllib.request.Request(
                url, headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_error = exc
            except json.JSONDecodeError as exc:
                last_error = exc
        if attempt < retries - 1:
            time.sleep(2.0 * (2**attempt))
    raise DataError(f"Could not fetch data for {symbol!r}: {last_error}")


def parse_chart(payload: dict, *, name: str | None = None) -> AssetSnapshot:
    """Turn a Yahoo chart JSON payload into an :class:`AssetSnapshot`.

    Pure function: no network, fully testable with a synthetic ``payload``.
    """
    try:
        chart = payload["chart"]
    except (KeyError, TypeError) as exc:
        raise DataError(f"Malformed payload: {exc}") from exc

    if chart.get("error"):
        raise DataError(f"Yahoo returned an error: {chart['error']}")

    results = chart.get("result") or []
    if not results:
        raise DataError("Payload contained no results")

    result = results[0]
    meta = result.get("meta", {})
    symbol = meta.get("symbol", "?")

    price = meta.get("regularMarketPrice")
    if price is None:
        raise DataError(f"No regularMarketPrice for {symbol}")

    raw_closes = []
    indicators = result.get("indicators", {})
    quote_blocks = indicators.get("quote") or [{}]
    for close in quote_blocks[0].get("close", []) or []:
        if close is not None:
            raw_closes.append(float(close))

    market_time = None
    if meta.get("regularMarketTime"):
        market_time = datetime.fromtimestamp(meta["regularMarketTime"], tz=timezone.utc)

    return AssetSnapshot(
        symbol=symbol,
        name=name or meta.get("shortName") or meta.get("longName") or symbol,
        currency=meta.get("currency", "USD"),
        price=float(price),
        # Prefer the true prior close, then the prior daily bar. Only fall back
        # to chartPreviousClose (the pre-window close, which for a 1y range is
        # ~a year old) as a last resort.
        previous_close=_coerce_float(meta.get("previousClose"))
        or (raw_closes[-2] if len(raw_closes) >= 2 else None)
        or _coerce_float(meta.get("chartPreviousClose")),
        market_time=market_time,
        market_state=meta.get("marketState", "UNKNOWN"),
        fifty_two_week_high=_coerce_float(meta.get("fiftyTwoWeekHigh"))
        or (max(raw_closes) if raw_closes else None),
        fifty_two_week_low=_coerce_float(meta.get("fiftyTwoWeekLow"))
        or (min(raw_closes) if raw_closes else None),
        closes=raw_closes,
    )


def get_snapshot(symbol: str, *, name: str | None = None) -> AssetSnapshot:
    """Fetch and parse a one-year daily snapshot for ``symbol``."""
    return parse_chart(fetch_chart(symbol, rng="1y", interval="1d"), name=name)


def get_usd_idr(*, fallback: float = config.FALLBACK_USD_IDR) -> tuple[float, bool]:
    """Return ``(rate, is_live)`` for USD -> IDR.

    Falls back to a static assumption if the live quote is unavailable so the
    goal math never crashes offline.
    """
    try:
        snapshot = parse_chart(fetch_chart("IDR=X", rng="5d", interval="1d"))
        if snapshot.price > 0:
            return snapshot.price, True
    except DataError:
        pass
    return fallback, False


def _coerce_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
