"""Offline unit tests for the scoring engine (no network)."""
import unittest

from investment_scorer.data import PriceSeries, synthetic_series
from investment_scorer.scoring import (
    clamp, linear_map, piecewise, _pe_to_score,
    _valuation_pillar, _momentum_pillar, score_series,
)


def make_series(closes, symbol="TST", name="Test"):
    return PriceSeries(
        symbol=symbol,
        name=name,
        closes=list(closes),
        highs=[c * 1.01 for c in closes],
        lows=[c * 0.99 for c in closes],
        volumes=[1_000_000] * len(closes),
        price=closes[-1],
        previous_close=closes[-2] if len(closes) > 1 else closes[-1],
        fifty_two_week_high=max(closes),
        fifty_two_week_low=min(closes),
    )


class TestHelpers(unittest.TestCase):
    def test_linear_map_clamps(self):
        self.assertEqual(linear_map(-5, 0, 0, 10, 100), 0)     # below domain
        self.assertEqual(linear_map(15, 0, 0, 10, 100), 100)   # above domain
        self.assertEqual(linear_map(5, 0, 0, 10, 100), 50)     # midpoint

    def test_piecewise_endpoints_and_interp(self):
        pts = [(0, 0), (10, 100)]
        self.assertEqual(piecewise(-1, pts), 0)
        self.assertEqual(piecewise(11, pts), 100)
        self.assertEqual(piecewise(5, pts), 50)

    def test_pe_score_monotonic(self):
        cheap = _pe_to_score(10)
        fair = _pe_to_score(25)
        rich = _pe_to_score(60)
        self.assertGreater(cheap, fair)
        self.assertGreater(fair, rich)
        self.assertIsNone(_pe_to_score(None))
        self.assertIsNone(_pe_to_score(-5))

    def test_clamp(self):
        self.assertEqual(clamp(150), 100)
        self.assertEqual(clamp(-10), 0)
        self.assertEqual(clamp(42), 42)


class TestPillars(unittest.TestCase):
    def test_valuation_cheaper_scores_higher(self):
        base = list(range(100, 300))
        near_low = make_series(base + [110])
        near_high = make_series(base + [290])
        v_low, _ = _valuation_pillar(near_low)
        v_high, _ = _valuation_pillar(near_high)
        self.assertGreater(v_low, v_high)

    def test_momentum_prefers_healthy_dip_over_highs(self):
        up = [100 * (1.004 ** i) for i in range(220)]
        at_highs = make_series(up)
        # Same trend then a ~12% pullback over the final stretch.
        dip = make_series(up + [up[-1] * (1 - 0.12 * i / 15) for i in range(1, 16)])
        m_high, _, _ = _momentum_pillar(at_highs)
        m_dip, _, _ = _momentum_pillar(dip)
        self.assertGreater(m_dip, m_high)

    def test_valuation_blends_pe_when_present(self):
        base = list(range(100, 300)) + [290]
        s = make_series(base)
        v_no_pe, _ = _valuation_pillar(s)
        s.fundamentals.trailing_pe = 10  # very cheap
        v_cheap_pe, _ = _valuation_pillar(s)
        self.assertGreater(v_cheap_pe, v_no_pe)


class TestScoreSeries(unittest.TestCase):
    def test_score_bounds_and_structure(self):
        r = score_series(make_series([100 + i for i in range(210)]))
        self.assertTrue(0 <= r.composite <= 100)
        d = r.as_dict()
        for key in ("symbol", "composite_score", "recommendation", "components",
                    "signals", "rationale"):
            self.assertIn(key, d)
        self.assertEqual(len(r.components), 4)

    def test_strong_uptrend_has_strong_trend_weak_valuation(self):
        # Strictly rising to fresh highs: great trend, poor margin of safety.
        r = score_series(make_series([100 * (1.01 ** i) for i in range(220)]))
        comp = {c.name: c.score for c in r.components}
        self.assertGreater(comp["Trend / quality"], 80)
        self.assertLess(comp["Valuation (margin of safety)"], 45)
        self.assertNotEqual(r.label, "STRONG BUY")

    def test_deterministic_demo(self):
        a = score_series(synthetic_series("NVDA", "NVIDIA"))
        b = score_series(synthetic_series("NVDA", "NVIDIA"))
        self.assertAlmostEqual(a.composite, b.composite, places=9)

    def test_demo_confidence_flag(self):
        r = score_series(synthetic_series("SPY", "S&P 500"))
        self.assertEqual(r.source, "demo")
        self.assertEqual(r.confidence, "demo data")


if __name__ == "__main__":
    unittest.main()
