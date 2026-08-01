import unittest

from investment_advisor import config, planner, scoring

from .helpers import make_snapshot


class TestGoalMath(unittest.TestCase):
    def test_required_cagr(self):
        self.assertAlmostEqual(planner.required_cagr(100, 200, 1), 1.0)
        self.assertAlmostEqual(planner.required_cagr(100, 100, 5), 0.0)

    def test_future_value(self):
        self.assertAlmostEqual(planner.future_value(100, 0.10, 2), 121.0)

    def test_contributions_zero_return(self):
        self.assertAlmostEqual(
            planner.future_value_with_contributions(0, 100, 0.0, 1), 1200.0
        )

    def test_required_monthly_roundtrip(self):
        start, target, ret, years = 4000.0, 55000.0, 0.12, 4.0
        monthly = planner.required_monthly_contribution(start, target, ret, years)
        self.assertGreater(monthly, 0)
        achieved = planner.future_value_with_contributions(start, monthly, ret, years)
        self.assertAlmostEqual(achieved, target, delta=1.0)

    def test_required_monthly_zero_when_already_met(self):
        monthly = planner.required_monthly_contribution(10000, 100, 0.10, 5)
        self.assertEqual(monthly, 0.0)


class TestGoalAnalysis(unittest.TestCase):
    def test_target_conversion_and_unrealistic_verdict(self):
        analysis = planner.goal_analysis(
            start_usd=4000.0, target_idr=1_000_000_000.0, usd_idr=17_990.0,
            is_live_fx=True, horizons_years=(3.0, 4.0),
        )
        self.assertAlmostEqual(analysis.target_usd, 1_000_000_000.0 / 17_990.0, places=2)
        self.assertIn("UNREALISTIC", analysis.verdict)
        self.assertEqual(len(analysis.horizons), 2)
        for h in analysis.horizons:
            self.assertGreater(h.required_cagr, 0.30)

    def test_realistic_verdict(self):
        analysis = planner.goal_analysis(
            start_usd=100_000.0, target_idr=1_000_000_000.0, usd_idr=17_990.0,
            is_live_fx=False, horizons_years=(4.0,),
        )
        self.assertIn("REALISTIC", analysis.verdict)


class TestAllocation(unittest.TestCase):
    def _scores(self):
        assets = config.DEFAULT_ASSETS
        out = []
        for i, a in enumerate(assets):
            snap = make_snapshot(a.symbol, price=100.0 + i * 10)
            s = scoring.score_asset(snap, a)
            s.score = 40.0 + i * 15  # deterministic spread of scores
            out.append(s)
        return out

    def test_allocation_weights_and_dollars(self):
        scores = self._scores()
        plan = planner.suggest_allocation(4000.0, scores, config.DEFAULT_ASSETS, tranches=12)
        self.assertAlmostEqual(plan.tranche_usd, 4000.0 / 12)
        total_weight = sum(ln.final_weight for ln in plan.lines)
        self.assertAlmostEqual(total_weight, 1.0, places=6)
        total_dollars = sum(ln.dollars for ln in plan.lines)
        self.assertAlmostEqual(total_dollars, plan.suggested_deploy_usd, places=6)
        self.assertEqual(len(plan.lines), len(scores))

    def test_higher_score_gets_more_than_policy_share(self):
        # Two identical-policy stocks, different scores -> higher score gets more.
        assets = (
            config.Asset("A", "A", "stock", 1.0),
            config.Asset("B", "B", "stock", 1.0),
        )
        sa = scoring.score_asset(make_snapshot("A", price=100), assets[0])
        sb = scoring.score_asset(make_snapshot("B", price=100), assets[1])
        sa.score, sb.score = 80.0, 40.0
        plan = planner.suggest_allocation(1200.0, [sa, sb], assets, tranches=12)
        weights = {ln.symbol: ln.final_weight for ln in plan.lines}
        self.assertGreater(weights["A"], weights["B"])


if __name__ == "__main__":
    unittest.main()
