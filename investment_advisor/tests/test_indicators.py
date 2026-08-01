import unittest

from investment_advisor import indicators


class TestIndicators(unittest.TestCase):
    def test_sma_basic(self):
        self.assertEqual(indicators.simple_moving_average([1, 2, 3, 4, 5], 3), 4.0)
        self.assertEqual(indicators.simple_moving_average([1, 2, 3, 4, 5], 5), 3.0)

    def test_sma_insufficient(self):
        self.assertIsNone(indicators.simple_moving_average([1, 2], 3))
        self.assertIsNone(indicators.simple_moving_average([1, 2, 3], 0))

    def test_rsi_all_gains_is_100(self):
        prices = [float(i) for i in range(1, 40)]
        self.assertAlmostEqual(indicators.rsi(prices, 14), 100.0)

    def test_rsi_all_losses_is_0(self):
        prices = [float(i) for i in range(40, 1, -1)]
        self.assertAlmostEqual(indicators.rsi(prices, 14), 0.0)

    def test_rsi_bounds(self):
        prices = [100 + (i % 5) - 2 for i in range(60)]
        value = indicators.rsi([float(p) for p in prices], 14)
        self.assertIsNotNone(value)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 100.0)

    def test_rsi_insufficient(self):
        self.assertIsNone(indicators.rsi([1, 2, 3], 14))

    def test_range_position(self):
        self.assertAlmostEqual(indicators.range_position(80, 80, 120), 0.0)
        self.assertAlmostEqual(indicators.range_position(120, 80, 120), 1.0)
        self.assertAlmostEqual(indicators.range_position(100, 80, 120), 0.5)

    def test_range_position_bad_bounds(self):
        self.assertIsNone(indicators.range_position(100, 120, 80))
        self.assertIsNone(indicators.range_position(100, None, 120))

    def test_drawdown_from_high(self):
        self.assertAlmostEqual(indicators.drawdown_from_high(120, 120), 0.0)
        self.assertAlmostEqual(indicators.drawdown_from_high(96, 120), -0.2)
        self.assertIsNone(indicators.drawdown_from_high(96, 0))

    def test_pct_distance(self):
        self.assertAlmostEqual(indicators.pct_distance(110, 100), 0.1)
        self.assertIsNone(indicators.pct_distance(110, None))

    def test_volatility(self):
        self.assertEqual(indicators.annualized_volatility([100.0] * 100), 0.0)
        self.assertIsNone(indicators.annualized_volatility([100.0, 101.0]))
        vol = indicators.annualized_volatility([100 + (i % 3) for i in range(100)])
        self.assertIsNotNone(vol)
        self.assertGreater(vol, 0.0)


if __name__ == "__main__":
    unittest.main()
