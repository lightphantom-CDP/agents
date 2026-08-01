import unittest

from investment_advisor import data

from .helpers import yahoo_payload


class TestParseChart(unittest.TestCase):
    def test_parses_core_fields(self):
        payload = yahoo_payload("NVDA", price=200.75, high=236.54, low=164.07,
                                closes=[170.0, 180.0, 190.0, 200.75])
        snap = data.parse_chart(payload)
        self.assertEqual(snap.symbol, "NVDA")
        self.assertEqual(snap.price, 200.75)
        self.assertEqual(snap.fifty_two_week_high, 236.54)
        self.assertEqual(snap.fifty_two_week_low, 164.07)
        self.assertEqual(snap.currency, "USD")
        self.assertEqual(len(snap.closes), 4)
        self.assertIsNotNone(snap.market_time)

    def test_previous_close_fallback_to_series(self):
        payload = yahoo_payload("X", price=100.0, closes=[95.0, 98.0])
        meta = payload["chart"]["result"][0]["meta"]
        meta.pop("previousClose")
        meta.pop("chartPreviousClose")
        snap = data.parse_chart(payload)
        self.assertEqual(snap.previous_close, 95.0)

    def test_previous_close_prefers_prior_daily_bar_over_chart_prev(self):
        # A 1y daily fetch: chartPreviousClose is ~a year old and must not win.
        payload = yahoo_payload("X", price=110.0, closes=[80.0, 100.0, 108.0, 110.0])
        payload["chart"]["result"][0]["meta"].pop("previousClose")
        payload["chart"]["result"][0]["meta"]["chartPreviousClose"] = 70.0
        snap = data.parse_chart(payload)
        self.assertEqual(snap.previous_close, 108.0)

    def test_last_change_pct(self):
        payload = yahoo_payload("X", price=110.0, prev_close=100.0)
        snap = data.parse_chart(payload)
        self.assertAlmostEqual(snap.last_change_pct, 10.0)

    def test_missing_price_raises(self):
        payload = yahoo_payload("X")
        payload["chart"]["result"][0]["meta"].pop("regularMarketPrice")
        with self.assertRaises(data.DataError):
            data.parse_chart(payload)

    def test_empty_results_raises(self):
        with self.assertRaises(data.DataError):
            data.parse_chart({"chart": {"result": [], "error": None}})

    def test_error_payload_raises(self):
        with self.assertRaises(data.DataError):
            data.parse_chart({"chart": {"result": None, "error": {"code": "Not Found"}}})

    def test_malformed_payload_raises(self):
        with self.assertRaises(data.DataError):
            data.parse_chart({"unexpected": True})


if __name__ == "__main__":
    unittest.main()
