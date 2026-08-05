"""Offline unit tests for the goal-planning math (no network)."""
import unittest

from investment_scorer.config import GoalConfig
from investment_scorer.goal import (
    future_value, required_cagr, required_monthly_contribution, plan_goal,
)


class TestGoalMath(unittest.TestCase):
    def test_future_value_lump_sum(self):
        # $1,000 at 10%/yr compounded monthly for 1 year.
        fv = future_value(1000, 0, 0.10, 1)
        self.assertAlmostEqual(fv, 1000 * (1 + 0.10 / 12) ** 12, places=6)

    def test_future_value_with_contributions(self):
        fv = future_value(0, 100, 0.0, 2)  # zero return, 24 months of $100
        self.assertAlmostEqual(fv, 2400, places=6)

    def test_required_cagr(self):
        self.assertAlmostEqual(required_cagr(4000, 8000, 1), 1.0, places=9)
        self.assertAlmostEqual(required_cagr(100, 100, 5), 0.0, places=9)

    def test_required_monthly_zero_when_already_reachable(self):
        # If the lump sum alone already exceeds the target, no saving is needed.
        pmt = required_monthly_contribution(100000, 1000, 0.10, 4)
        self.assertEqual(pmt, 0.0)

    def test_required_monthly_roundtrip(self):
        # The computed contribution should actually reach the target.
        pv, target, r, y = 4000, 60000, 0.10, 4
        pmt = required_monthly_contribution(pv, target, r, y)
        self.assertGreater(pmt, 0)
        self.assertAlmostEqual(future_value(pv, pmt, r, y), target, delta=1.0)


class TestPlanGoal(unittest.TestCase):
    def test_plan_goal_demo(self):
        goal = GoalConfig()  # $4k -> 1B IDR in 3-4 years
        plan = plan_goal(goal, demo=True)
        # Uses fallback FX in demo mode.
        self.assertFalse(plan.fx_is_live)
        self.assertAlmostEqual(plan.target_usd,
                               goal.target_amount_idr / goal.fallback_usd_idr, places=6)
        # Horizons should be [3, 3.5, 4].
        self.assertEqual(plan.horizons, [3.0, 3.5, 4.0])
        # This goal is wildly aggressive for a lump sum -> huge required CAGR.
        self.assertGreater(min(plan.lump_sum_cagr.values()), 0.5)
        self.assertIn("aggressive", plan.verdict.lower())
        # A scenario exists for every (horizon, return) combination.
        self.assertEqual(len(plan.scenarios),
                         len(plan.horizons) * len(goal.return_scenarios))

    def test_plan_goal_reasonable_case(self):
        goal = GoalConfig(starting_cash_usd=10000, target_amount_idr=200_000_000,
                          min_years=10, max_years=10)
        plan = plan_goal(goal, demo=True)
        # ~$12k target over 10 years from $10k is a gentle required return.
        self.assertLess(max(plan.lump_sum_cagr.values()), 0.15)


if __name__ == "__main__":
    unittest.main()
