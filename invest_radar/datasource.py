"""Real-time-ish market data via Yahoo Finance public endpoints.

Only ``requests`` is required. Three things are fetched:

* ``/v8/finance/chart``      -> latest price + ~1y of daily closes (always works).
* ``/v10/finance/quoteSummary`` -> fundamentals (P/E, yield, analyst target).
  This needs a Yahoo "crumb" obtained from a cookie handshake; if that fails we
  degrade gracefully and simply omit valuation-derived signals.
* ``IDR=X`` chart            -> live USD/IDR exchange rate for the goal maths.

The module never raises for a single bad symbol - it returns a :class:`Quote`
with ``ok=False`` so the hourly job keeps running.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from .config import Asset

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")


@dataclass
class Quote:
    """Everything InvestRadar knows about one instrument after a fetch."""

    symbol: str
    name: str
    ok: bool = False
    error: str | None = None
    price: float | None = None
    currency: str = "USD"
    closes: list[float] = field(default_factory=list)
    trailing_pe: float | None = None
    forward_pe: float | None = None
    dividend_yield_pct: float | None = None
    price_to_book: float | None = None
    peg_ratio: float | None = None
    target_mean: float | None = None
    recommendation: str | None = None
    market_time: int | None = None


class YahooClient:
    """Small session-backed client with retries and a lazy crumb handshake."""

    def __init__(self, timeout: float = 20.0, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        # NB: use a permissive Accept - the getcrumb endpoint returns text/plain
        # and 406s if we demand application/json.
        self.session.headers.update({"User-Agent": _UA, "Accept": "*/*"})
        self._crumb: str | None = None
        self._crumb_tried = False

    # -- low level ---------------------------------------------------------
    def _get_json(self, path: str, params: dict | None = None) -> dict | None:
        """GET ``path`` (host is prepended) as JSON, trying both Yahoo hosts."""
        last_err: Exception | None = None
        for attempt in range(self.retries):
            for host in _HOSTS:
                url = f"https://{host}{path}"
                try:
                    resp = self.session.get(url, params=params, timeout=self.timeout)
                    if resp.status_code == 200:
                        return resp.json()
                    last_err = RuntimeError(f"HTTP {resp.status_code}")
                except requests.RequestException as exc:  # network hiccup
                    last_err = exc
            time.sleep(1.5 * (attempt + 1))
        if last_err:
            self._last_err = str(last_err)
        return None

    def _ensure_crumb(self) -> str | None:
        """Perform the cookie + crumb handshake once; cache the result."""
        if self._crumb_tried:
            return self._crumb
        self._crumb_tried = True
        try:
            # This 404s but sets the consent cookie we need.
            self.session.get("https://fc.yahoo.com/", timeout=self.timeout)
            for host in _HOSTS:
                resp = self.session.get(
                    f"https://{host}/v1/test/getcrumb", timeout=self.timeout
                )
                if resp.status_code == 200 and resp.text and "<" not in resp.text:
                    self._crumb = resp.text.strip()
                    break
        except requests.RequestException:
            self._crumb = None
        return self._crumb

    # -- public ------------------------------------------------------------
    def fetch_fx(self, pair: str = "IDR=X") -> float | None:
        """Return the latest USD/<ccy> rate (``IDR=X`` -> Indonesian rupiah)."""
        data = self._get_json(f"/v8/finance/chart/{pair}", {"range": "5d", "interval": "1d"})
        try:
            return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
        except (TypeError, KeyError, IndexError, ValueError):
            return None

    def _fetch_chart(self, symbol: str) -> tuple[list[float], dict] | None:
        data = self._get_json(
            f"/v8/finance/chart/{symbol}", {"range": "1y", "interval": "1d"}
        )
        try:
            result = data["chart"]["result"][0]
        except (TypeError, KeyError, IndexError):
            return None
        meta = result.get("meta", {})
        raw = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [float(c) for c in raw if c is not None]
        return closes, meta

    def _fetch_fundamentals(self, symbol: str) -> dict:
        crumb = self._ensure_crumb()
        if not crumb:
            return {}
        modules = "summaryDetail,defaultKeyStatistics,financialData"
        data = self._get_json(
            f"/v10/finance/quoteSummary/{symbol}",
            {"modules": modules, "crumb": crumb},
        )
        try:
            return data["quoteSummary"]["result"][0]
        except (TypeError, KeyError, IndexError):
            return {}

    def fetch_quote(self, asset: Asset) -> Quote:
        """Fetch price + history + fundamentals for one asset."""
        quote = Quote(symbol=asset.symbol, name=asset.name)
        chart = self._fetch_chart(asset.symbol)
        if not chart or not chart[0]:
            quote.error = getattr(self, "_last_err", "no chart data")
            return quote
        closes, meta = chart
        quote.closes = closes
        quote.currency = meta.get("currency", "USD")
        quote.market_time = meta.get("regularMarketTime")
        price = meta.get("regularMarketPrice")
        quote.price = float(price) if price is not None else closes[-1]
        quote.ok = True

        fund = self._fetch_fundamentals(asset.symbol)
        if fund:
            summary = fund.get("summaryDetail", {})
            stats = fund.get("defaultKeyStatistics", {})
            fin = fund.get("financialData", {})
            quote.trailing_pe = _raw(summary.get("trailingPE"))
            quote.forward_pe = _raw(summary.get("forwardPE")) or _raw(stats.get("forwardPE"))
            dy = _raw(summary.get("dividendYield"))
            # Yahoo reports yield as a fraction (0.012) for most feeds.
            quote.dividend_yield_pct = (dy * 100.0) if dy is not None and dy < 1 else dy
            quote.price_to_book = _raw(stats.get("priceToBook"))
            quote.peg_ratio = _raw(stats.get("pegRatio"))
            quote.target_mean = _raw(fin.get("targetMeanPrice"))
            quote.recommendation = fin.get("recommendationKey")
        return quote


def _raw(node) -> float | None:
    """Yahoo wraps numbers as ``{"raw": 1.2, "fmt": "1.20"}`` - unwrap safely."""
    if node is None:
        return None
    if isinstance(node, dict):
        node = node.get("raw")
    try:
        val = float(node)
    except (TypeError, ValueError):
        return None
    return val if val != 0 else None
