"""Unit tests for the offline (no-network) logic: indicators, scoring, goal maths.

Run with:  python -m unittest discover -s invest_radar/tests
"""

from __future__ import annotations

import math
import unittest

from invest_radar.config import DEFAULT_WATCHLIST, GoalConfig, verdict_for
from invest_radar.datasource import Quote
from invest_radar.goal import (
    analyze_goal,
    future_value_lump_sum,
    required_cagr,
    required_monthly,
)
from invest_radar.indicators import compute_indicators, rsi, sma
from invest_radar.scoring import (
    build_portfolio,
    interpolate,
    score_asset,
    timing_score,
    valuation_score,
)


class TestIndicators(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(sma([1], 2))

    def test_rsi_bounds(self):
        rising = list(range(1, 40))
        self.assertAlmostEqual(rsi(rising, 14), 100.0)
        falling = list(range(40, 1, -1))
        self.assertLess(rsi(falling, 14), 5.0)
        self.assertIsNone(rsi([1, 2], 14))

    def test_compute_indicators(self):
        closes = [100 + i * 0.5 for i in range(260)]  # steady uptrend
        ind = compute_indicators(closes)
        self.assertGreater(ind.sma50, 0)
        self.assertGreater(ind.sma200, 0)
        self.assertAlmostEqual(ind.price, closes[-1])
        self.assertTrue(0 <= ind.range_position_pct <= 100)
        self.assertLessEqual(ind.drawdown_from_high_pct, 0.01)


class TestScoring(unittest.TestCase):
    def test_interpolate(self):
        anchors = ((0, 0), (10, 100))
        self.assertEqual(interpolate(anchors, -5), 0)
        self.assertEqual(interpolate(anchors, 15), 100)
        self.assertAlmostEqual(interpolate(anchors, 5), 50)

    def test_valuation_prefers_metric(self):
        asset = DEFAULT_WATCHLIST[1]  # NVDA, forward metric
        cheap = Quote(symbol="NVDA", name="NVIDIA", ok=True, forward_pe=18)
        rich = Quote(symbol="NVDA", name="NVIDIA", ok=True, forward_pe=60)
        s_cheap, _, _ = valuation_score(asset, cheap)
        s_rich, _, _ = valuation_score(asset, rich)
        self.assertGreater(s_cheap, s_rich)

    def test_timing_monotonic(self):
        self.assertGreater(timing_score(_fake_ind(rsi=25)), timing_score(_fake_ind(rsi=75)))

    def test_score_asset_end_to_end(self):
        asset = DEFAULT_WATCHLIST[0]
        closes = [200 + math.sin(i / 20) * 8 + i * 0.1 for i in range(260)]
        quote = Quote(
            symbol="SPY", name="S&P 500", ok=True, closes=closes,
            price=closes[-1], trailing_pe=20,
        )
        scored = score_asset(asset, quote)
        self.assertIsNotNone(scored)
        self.assertTrue(0 <= scored.overall <= 100)
        self.assertIn("valuation", scored.components)
        self.assertTrue(scored.verdict)

    def test_score_asset_without_fundamentals(self):
        asset = DEFAULT_WATCHLIST[0]
        closes = [200 + i * 0.1 for i in range(260)]
        quote = Quote(symbol="SPY", name="S&P 500", ok=True, closes=closes, price=closes[-1])
        scored = score_asset(asset, quote)
        self.assertIsNotNone(scored)
        self.assertNotIn("valuation", scored.components)  # weight redistributed
        self.assertTrue(0 <= scored.overall <= 100)

    def test_build_portfolio_allocation(self):
        scores = []
        for asset in DEFAULT_WATCHLIST:
            closes = [100 + i * 0.2 for i in range(260)]
            q = Quote(symbol=asset.symbol, name=asset.name, ok=True, closes=closes,
                      price=closes[-1], forward_pe=25, trailing_pe=20)
            s = score_asset(asset, q)
            if s:
                scores.append(s)
        pf = build_portfolio(scores)
        self.assertTrue(0 <= pf.overall <= 100)
        self.assertAlmostEqual(sum(pf.allocation.values()), 100.0, delta=0.5)


class TestGoal(unittest.TestCase):
    def test_required_cagr(self):
        self.assertAlmostEqual(required_cagr(100, 200, 1), 1.0)  # doubling in 1y = 100%
        self.assertAlmostEqual(required_cagr(100, 100, 5), 0.0)

    def test_required_monthly_reaches_target(self):
        start, target, years, r = 4000.0, 55000.0, 4.0, 0.10
        c = required_monthly(start, target, years, r)
        i = r / 12
        n = years * 12
        fv = future_value_lump_sum(start, years, r) + c * (((1 + i) ** n - 1) / i)
        self.assertAlmostEqual(fv, target, delta=1.0)

    def test_required_monthly_zero_when_lump_enough(self):
        self.assertEqual(required_monthly(100000, 50000, 3, 0.10), 0.0)

    def test_analyze_goal(self):
        g = analyze_goal(GoalConfig(), fx_usd_idr=17955.0)
        self.assertIsNotNone(g.target_usd)
        self.assertGreater(len(g.rows), 0)
        self.assertIn("IDR", g.headline)

    def test_analyze_goal_no_fx(self):
        g = analyze_goal(GoalConfig(), fx_usd_idr=None)
        self.assertIsNone(g.target_usd)


def _fake_ind(rsi):
    from invest_radar.indicators import Indicators
    return Indicators(
        price=100, sma50=100, sma200=100, rsi14=rsi, high_52w=110, low_52w=90,
        drawdown_from_high_pct=-5, range_position_pct=50, dist_sma50_pct=0,
        dist_sma200_pct=0, mom_3m_pct=1, mom_6m_pct=2,
    )


class TestVerdict(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(verdict_for(90)[0], "STRONG BUY")
        self.assertEqual(verdict_for(10)[0], "AVOID / TRIM")


if __name__ == "__main__":
    unittest.main()
