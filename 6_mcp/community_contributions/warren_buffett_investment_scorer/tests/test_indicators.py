"""Offline unit tests for the technical indicators (no network)."""
import unittest

from investment_scorer import indicators as ind


class TestIndicators(unittest.TestCase):
    def test_sma_basic(self):
        self.assertEqual(ind.sma([1, 2, 3, 4, 5], 5), 3.0)
        self.assertEqual(ind.sma([2, 4, 6, 8], 2), 7.0)

    def test_sma_insufficient(self):
        self.assertIsNone(ind.sma([1, 2], 5))

    def test_sma_skips_none_gaps(self):
        # Holiday gaps (None) should be dropped, not crash.
        self.assertEqual(ind.sma([2, None, 4], 2), 3.0)

    def test_ema_finite_and_reactive(self):
        rising = list(range(1, 60))
        e = ind.ema(rising, 10)
        self.assertIsNotNone(e)
        # EMA of a rising series trails the last value but stays below it.
        self.assertLess(e, rising[-1])
        self.assertGreater(e, rising[0])

    def test_rsi_extremes(self):
        up = [float(i) for i in range(1, 40)]
        down = [float(i) for i in range(40, 1, -1)]
        self.assertAlmostEqual(ind.rsi(up), 100.0, places=6)
        self.assertAlmostEqual(ind.rsi(down), 0.0, places=6)

    def test_rsi_midrange(self):
        # Alternating small moves -> RSI near the middle of its range.
        seq, price = [], 100.0
        for i in range(40):
            price += 1 if i % 2 == 0 else -1
            seq.append(price)
        r = ind.rsi(seq)
        self.assertTrue(30 < r < 70)

    def test_macd_shape(self):
        series = [100 + i * 0.5 for i in range(80)]
        macd = ind.macd(series)
        self.assertIsNotNone(macd)
        self.assertEqual(len(macd), 3)

    def test_current_drawdown(self):
        self.assertAlmostEqual(ind.current_drawdown([10, 12, 6]), (6 - 12) / 12)
        self.assertAlmostEqual(ind.current_drawdown([1, 2, 3, 4]), 0.0)

    def test_range_position(self):
        self.assertAlmostEqual(ind.range_position(5, 0, 10), 0.5)
        self.assertEqual(ind.range_position(-5, 0, 10), 0.0)  # clamped
        self.assertEqual(ind.range_position(50, 0, 10), 1.0)  # clamped
        self.assertIsNone(ind.range_position(5, 10, 10))      # degenerate

    def test_annualized_volatility_positive(self):
        seq, price = [100.0], 100.0
        for i in range(60):
            price *= 1 + (0.01 if i % 2 == 0 else -0.008)
            seq.append(price)
        vol = ind.annualized_volatility(seq)
        self.assertIsNotNone(vol)
        self.assertGreater(vol, 0)

    def test_pct_change(self):
        self.assertAlmostEqual(ind.pct_change([100, 110], 1), 0.1)
        self.assertIsNone(ind.pct_change([100], 5))


if __name__ == "__main__":
    unittest.main()
