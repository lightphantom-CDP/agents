"""Resilient, dependency-light market-data layer.

Primary source is Yahoo Finance's public ``v8/finance/chart`` endpoint, which
returns both a near-real-time quote and daily OHLCV history in one call and
needs no API key. Because these hourly jobs can share an egress IP and get rate
limited, every request retries with backoff and rotates between Yahoo hosts.

If the network is unavailable (or ``--demo`` is passed) a deterministic
synthetic series is generated instead, so the tool always produces output and
the test-suite can run fully offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "wb_investment_scorer_cache")


@dataclass
class Fundamentals:
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    peg_ratio: Optional[float] = None
    market_cap: Optional[float] = None


@dataclass
class PriceSeries:
    """Everything the scorer needs about one instrument."""

    symbol: str
    name: str
    currency: str = "USD"
    closes: List[float] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    volumes: List[float] = field(default_factory=list)
    price: float = 0.0
    previous_close: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    fundamentals: Fundamentals = field(default_factory=Fundamentals)
    source: str = "yahoo"          # "yahoo" | "demo"
    stale: bool = False            # true when we fell back to last cached/close

    @property
    def day_change_pct(self) -> Optional[float]:
        if self.previous_close:
            return (self.price - self.previous_close) / self.previous_close
        return None


# --------------------------------------------------------------------------- #
# Low-level HTTP
# --------------------------------------------------------------------------- #
def _http_get_json(url: str, timeout: float = 15.0) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _fetch_chart_json(symbol: str, rng: str, interval: str, retries: int = 3) -> Optional[dict]:
    """Fetch Yahoo chart JSON, rotating hosts and backing off on rate limits."""
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        host = _HOSTS[attempt % len(_HOSTS)]
        url = (
            f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol)}"
            f"?range={rng}&interval={interval}&includePrePost=false"
        )
        try:
            return _http_get_json(url)
        except urllib.error.HTTPError as err:  # 401/403/429 etc.
            last_err = err
            # Rate limited or transient - wait a bit longer each time.
            time.sleep(min(1.5 * (attempt + 1), 5.0))
        except Exception as err:  # network / parse issues
            last_err = err
            time.sleep(1.0 * (attempt + 1))
    if last_err:
        print(f"[data] live fetch failed for {symbol}: {type(last_err).__name__}: {last_err}")
    return None


# --------------------------------------------------------------------------- #
# Caching (so an hourly cron does not hammer the API within the same hour)
# --------------------------------------------------------------------------- #
def _cache_path(symbol: str, rng: str) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    key = hashlib.md5(f"{symbol}:{rng}".encode()).hexdigest()
    return os.path.join(_CACHE_DIR, f"{key}.json")


def _read_cache(symbol: str, rng: str, ttl: int) -> Optional[dict]:
    path = _cache_path(symbol, rng)
    try:
        if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < ttl:
            with open(path, "r") as fh:
                return json.load(fh)
    except Exception:
        pass
    return None


def _write_cache(symbol: str, rng: str, payload: dict) -> None:
    try:
        with open(_cache_path(symbol, rng), "w") as fh:
            json.dump(payload, fh)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _parse_chart(symbol: str, name: str, payload: dict) -> Optional[PriceSeries]:
    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        quote = result["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        return None

    def _series(key: str) -> List[float]:
        return [v for v in quote.get(key, []) if v is not None]

    closes = _series("close")
    if not closes:
        return None
    price = meta.get("regularMarketPrice") or closes[-1]
    # NB: on a 1y range Yahoo's ``chartPreviousClose`` is the close *before the
    # range* (~1yr ago), not yesterday's - so use the prior daily bar instead.
    prev_close = closes[-2] if len(closes) >= 2 else (
        meta.get("chartPreviousClose") or meta.get("previousClose"))
    return PriceSeries(
        symbol=symbol,
        name=name,
        currency=meta.get("currency", "USD"),
        closes=closes,
        highs=_series("high"),
        lows=_series("low"),
        volumes=_series("volume"),
        price=float(price),
        previous_close=prev_close,
        fifty_two_week_high=meta.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=meta.get("fiftyTwoWeekLow"),
        source="yahoo",
    )


# --------------------------------------------------------------------------- #
# Optional fundamentals enrichment (only if yfinance happens to be installed)
# --------------------------------------------------------------------------- #
def _enrich_fundamentals(series: PriceSeries) -> None:
    try:
        import yfinance  # type: ignore
    except Exception:
        return
    try:
        info = yfinance.Ticker(series.symbol).get_info()
        series.fundamentals = Fundamentals(
            trailing_pe=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            price_to_book=info.get("priceToBook"),
            peg_ratio=info.get("pegRatio") or info.get("trailingPegRatio"),
            market_cap=info.get("marketCap"),
        )
    except Exception:
        # Fundamentals are a bonus; the scorer works without them.
        pass


# --------------------------------------------------------------------------- #
# Deterministic synthetic data (offline demo / tests)
# --------------------------------------------------------------------------- #
def synthetic_series(symbol: str, name: str, days: int = 260) -> PriceSeries:
    """A realistic-looking but fully deterministic series seeded by the symbol.

    Builds an upward-drifting random walk and applies a modest recent pullback,
    so the scorer produces varied, interesting output with no network access.
    """
    seed = int(hashlib.md5(symbol.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)
    start = 50 + rng.random() * 250
    drift = 0.0004 + rng.random() * 0.0006          # gentle long-term uptrend
    vol = 0.012 + rng.random() * 0.012
    closes: List[float] = [start]
    for i in range(1, days):
        shock = rng.gauss(0, 1) * vol
        # Inject a pullback over the final ~15 sessions for a realistic "dip".
        pullback = -0.004 if i > days - 15 else 0.0
        closes.append(max(1.0, closes[-1] * (1 + drift + shock + pullback)))
    highs = [c * (1 + abs(rng.gauss(0, 0.004))) for c in closes]
    lows = [c * (1 - abs(rng.gauss(0, 0.004))) for c in closes]
    return PriceSeries(
        symbol=symbol,
        name=name,
        currency="USD",
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=[1_000_000 + rng.randint(0, 500_000) for _ in closes],
        price=closes[-1],
        previous_close=closes[-2],
        fifty_two_week_high=max(closes),
        fifty_two_week_low=min(closes),
        source="demo",
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_series(
    symbol: str,
    name: str,
    rng: str = "1y",
    interval: str = "1d",
    cache_ttl: int = 900,
    demo: bool = False,
    enrich: bool = True,
) -> PriceSeries:
    """Return a :class:`PriceSeries`, trying cache -> live -> synthetic."""
    if demo:
        return synthetic_series(symbol, name)

    cached = _read_cache(symbol, rng, cache_ttl)
    payload = cached or _fetch_chart_json(symbol, rng, interval)
    if payload is not None:
        series = _parse_chart(symbol, name, payload)
        if series is not None:
            if not cached:
                _write_cache(symbol, rng, payload)
            if enrich:
                _enrich_fundamentals(series)
            return series

    # Network unavailable -> deterministic offline fallback, clearly marked.
    fallback = synthetic_series(symbol, name)
    fallback.stale = True
    return fallback


def get_usd_idr(fallback: float = 16_500.0, demo: bool = False) -> tuple[float, bool]:
    """Return (USD->IDR rate, is_live)."""
    if demo:
        return fallback, False
    payload = _fetch_chart_json("USDIDR=X", "5d", "1d", retries=2)
    if payload:
        try:
            meta = payload["chart"]["result"][0]["meta"]
            rate = meta.get("regularMarketPrice")
            if rate and rate > 0:
                return float(rate), True
        except (KeyError, IndexError, TypeError):
            pass
    return fallback, False
