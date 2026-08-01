import unittest

from investment_advisor import config, scoring

from .helpers import declining_series, make_snapshot, rising_series


class TestScoringHelpers(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(scoring.clamp(150), 100.0)
        self.assertEqual(scoring.clamp(-5), 0.0)
        self.assertEqual(scoring.clamp(50), 50.0)

    def test_linmap(self):
        self.assertEqual(scoring.linmap(0, 0, 10, 0, 100), 0.0)
        self.assertEqual(scoring.linmap(10, 0, 10, 0, 100), 100.0)
        self.assertEqual(scoring.linmap(5, 0, 10, 0, 100), 50.0)
        self.assertEqual(scoring.linmap(20, 0, 10, 0, 100), 100.0)  # clamped

    def test_action_thresholds(self):
        self.assertEqual(scoring.action_for(90), "STRONG BUY")
        self.assertEqual(scoring.action_for(65), "BUY / ADD")
        self.assertEqual(scoring.action_for(50), "ACCUMULATE (DCA)")
        self.assertEqual(scoring.action_for(40), "HOLD / PATIENT")
        self.assertEqual(scoring.action_for(10), "WAIT / EXPENSIVE")


class TestScoreAsset(unittest.TestCase):
    def test_cheap_scores_higher_than_rich(self):
        cheap = make_snapshot(
            "CHEAP", price=70.5, closes=declining_series(260, 200.0, 0.5),
            high=200.0, low=70.0,
        )
        rich = make_snapshot(
            "RICH", price=229.5, closes=rising_series(260, 100.0, 0.5),
            high=230.0, low=100.0,
        )
        cheap_score = scoring.score_asset(cheap)
        rich_score = scoring.score_asset(rich)

        for s in (cheap_score, rich_score):
            self.assertGreaterEqual(s.score, 0.0)
            self.assertLessEqual(s.score, 100.0)
            self.assertEqual(set(s.subscores), set(config.SCORE_WEIGHTS))
            self.assertIn("rsi", s.metrics)

        self.assertGreater(cheap_score.score, rich_score.score + 20)
        self.assertIn(
            cheap_score.action, {"STRONG BUY", "BUY / ADD", "ACCUMULATE (DCA)"}
        )
        self.assertIn(rich_score.action, {"WAIT / EXPENSIVE", "HOLD / PATIENT"})

    def test_short_history_does_not_crash(self):
        snap = make_snapshot("SHORT", price=100.0, closes=[95.0, 96.0, 97.0, 98.0, 100.0])
        result = scoring.score_asset(snap)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 100.0)

    def test_uses_asset_metadata(self):
        snap = make_snapshot("SPY")
        asset = config.Asset("SPY", "S&P 500 (SPY ETF)", "index", 0.55)
        result = scoring.score_asset(snap, asset)
        self.assertEqual(result.name, "S&P 500 (SPY ETF)")
        self.assertEqual(result.kind, "index")


if __name__ == "__main__":
    unittest.main()
