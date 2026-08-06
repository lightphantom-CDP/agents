"""A tiny, dependency-free Yahoo Finance client.

Uses only the Python standard library so the scorer runs anywhere Python 3.12
is available - no ``pip install`` required.

Two public data sources are used:

* ``/v8/finance/chart``      -> OHLC history + a rich ``meta`` block. No auth.
* ``/v10/finance/quoteSummary`` -> fundamentals. Needs a cookie + "crumb",
  which we obtain transparently and cache for the process lifetime.

Every network call is defensive: on failure the functions return partial data
or ``None`` rather than raising, so a flaky endpoint degrades the report
instead of crashing it.
"""

from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from . import config

_BASES = ("https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com")


@dataclass
class PriceHistory:
    symbol: str
    currency: str | None
    price: float | None
    previous_close: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    market_time: int | None
    closes: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    timestamps: list[int] = field(default_factory=list)

    @property
    def has_series(self) -> bool:
        return len(self.closes) >= 30


class YahooClient:
    """Fetches quotes, history and fundamentals, reusing one cookie/crumb."""

    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
        self._crumb: str | None = None
        self._crumb_tried = False

    # ------------------------------------------------------------------ #
    # low-level HTTP
    # ------------------------------------------------------------------ #
    def _get(self, url: str, quiet: bool = False) -> bytes | None:
        headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json, text/plain, */*"}
        last_err: Exception | None = None
        for attempt in range(config.HTTP_RETRIES):
            try:
                req = urllib.request.Request(url, headers=headers)
                with self._opener.open(req, timeout=config.HTTP_TIMEOUT_SECONDS) as resp:
                    return resp.read()
            except urllib.error.HTTPError as exc:  # 4xx/5xx
                last_err = exc
                # A 401 usually means our crumb went stale - drop it so the
                # next fundamentals call re-primes.
                if exc.code in (401, 403):
                    self._crumb = None
                    self._crumb_tried = False
                if exc.code in (400, 404):
                    break  # not going to fix itself by retrying
            except Exception as exc:  # noqa: BLE001 - network is best-effort
                last_err = exc
            time.sleep(1.5 * (attempt + 1))
        if last_err is not None and not quiet:
            print(f"  [yahoo] request failed for {url.split('?')[0]}: {last_err}")
        return None

    def _get_json(self, path: str, query: dict[str, Any]) -> dict[str, Any] | None:
        qs = urllib.parse.urlencode(query)
        for base in _BASES:
            raw = self._get(f"{base}{path}?{qs}")
            if raw is None:
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
        return None

    # ------------------------------------------------------------------ #
    # crumb handshake
    # ------------------------------------------------------------------ #
    def _ensure_crumb(self) -> str | None:
        if self._crumb or self._crumb_tried:
            return self._crumb
        self._crumb_tried = True
        # Priming request sets the consent/session cookie. It legitimately
        # returns 404 but still hands us a usable cookie, so stay quiet.
        self._get("https://fc.yahoo.com/", quiet=True)
        raw = self._get("https://query1.finance.yahoo.com/v1/test/getcrumb", quiet=True)
        if raw:
            crumb = raw.decode("utf-8", "ignore").strip()
            # A valid crumb is short and non-HTML.
            if crumb and "<" not in crumb and len(crumb) < 40:
                self._crumb = crumb
        return self._crumb

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def history(
        self,
        symbol: str,
        rng: str = config.HISTORY_RANGE,
        interval: str = config.HISTORY_INTERVAL,
    ) -> PriceHistory | None:
        data = self._get_json(
            f"/v8/finance/chart/{urllib.parse.quote(symbol)}",
            {"range": rng, "interval": interval, "includePrePost": "false"},
        )
        try:
            result = data["chart"]["result"][0]  # type: ignore[index]
        except (TypeError, KeyError, IndexError):
            return None

        meta = result.get("meta", {})
        timestamps = result.get("timestamp", []) or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes_raw = quote.get("close", []) or []
        highs_raw = quote.get("high", []) or []
        lows_raw = quote.get("low", []) or []

        # Drop any None gaps while keeping series aligned to timestamps.
        closes, highs, lows, ts = [], [], [], []
        for i, c in enumerate(closes_raw):
            if c is None:
                continue
            closes.append(float(c))
            highs.append(float(highs_raw[i]) if i < len(highs_raw) and highs_raw[i] is not None else float(c))
            lows.append(float(lows_raw[i]) if i < len(lows_raw) and lows_raw[i] is not None else float(c))
            if i < len(timestamps):
                ts.append(int(timestamps[i]))

        return PriceHistory(
            symbol=meta.get("symbol", symbol),
            currency=meta.get("currency"),
            price=_as_float(meta.get("regularMarketPrice")),
            previous_close=_as_float(meta.get("chartPreviousClose") or meta.get("previousClose")),
            fifty_two_week_high=_as_float(meta.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_as_float(meta.get("fiftyTwoWeekLow")),
            market_time=meta.get("regularMarketTime"),
            closes=closes,
            highs=highs,
            lows=lows,
            timestamps=ts,
        )

    def fundamentals(self, symbol: str) -> dict[str, float]:
        """Return a flat dict of the fundamental metrics we score on.

        Missing fields are simply omitted; callers must treat every key as
        optional.
        """
        crumb = self._ensure_crumb()
        query: dict[str, Any] = {
            "modules": "financialData,defaultKeyStatistics,summaryDetail,price",
        }
        if crumb:
            query["crumb"] = crumb
        data = self._get_json(f"/v10/finance/quoteSummary/{urllib.parse.quote(symbol)}", query)
        try:
            result = data["quoteSummary"]["result"][0]  # type: ignore[index]
        except (TypeError, KeyError, IndexError):
            return {}

        fin = result.get("financialData", {}) or {}
        stats = result.get("defaultKeyStatistics", {}) or {}
        summ = result.get("summaryDetail", {}) or {}

        out: dict[str, float] = {}

        def take(dest: str, node: dict[str, Any], key: str) -> None:
            val = _raw(node.get(key))
            if val is not None:
                out[dest] = val

        take("current_price", fin, "currentPrice")
        take("roe", fin, "returnOnEquity")
        take("profit_margin", fin, "profitMargins")
        take("operating_margin", fin, "operatingMargins")
        take("gross_margin", fin, "grossMargins")
        take("debt_to_equity", fin, "debtToEquity")
        take("free_cashflow", fin, "freeCashflow")
        take("operating_cashflow", fin, "operatingCashflow")
        take("total_debt", fin, "totalDebt")
        take("total_cash", fin, "totalCash")
        take("current_ratio", fin, "currentRatio")
        take("revenue_growth", fin, "revenueGrowth")
        take("earnings_growth", fin, "earningsGrowth")
        take("target_mean_price", fin, "targetMeanPrice")
        take("num_analysts", fin, "numberOfAnalystOpinions")
        rec = fin.get("recommendationKey")
        if isinstance(rec, str):
            out["recommendation_key_is_buy"] = 1.0 if rec in ("buy", "strong_buy") else 0.0

        take("trailing_pe", summ, "trailingPE")
        take("forward_pe", summ, "forwardPE")
        take("dividend_yield", summ, "dividendYield")
        take("market_cap", summ, "marketCap")
        take("price_to_sales", summ, "priceToSalesTrailing12Months")
        take("beta", summ, "beta")
        take("fifty_day_avg", summ, "fiftyDayAverage")
        take("two_hundred_day_avg", summ, "twoHundredDayAverage")

        take("peg_ratio", stats, "pegRatio")
        take("price_to_book", stats, "priceToBook")
        take("forward_eps", stats, "forwardEps")
        take("trailing_eps", stats, "trailingEps")
        take("ev_to_ebitda", stats, "enterpriseToEbitda")
        take("earnings_q_growth", stats, "earningsQuarterlyGrowth")

        return out

    def usd_idr(self) -> float:
        hist = self.history(config.FX_SYMBOL, rng="5d", interval="1d")
        if hist and hist.price:
            return hist.price
        return config.FX_USD_IDR_FALLBACK


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _raw(node: Any) -> float | None:
    """Yahoo wraps numbers as ``{"raw": x, "fmt": "..."}``; unwrap safely."""
    if node is None:
        return None
    if isinstance(node, dict):
        return _as_float(node.get("raw"))
    return _as_float(node)
