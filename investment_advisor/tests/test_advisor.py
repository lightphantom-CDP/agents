import json
import unittest

from investment_advisor import config, report
from investment_advisor.advisor import build_report

from .helpers import declining_series, make_snapshot


def _fake_provider(symbol: str, name: str):
    presets = {
        "SPY": dict(price=747.0, high=760.0, low=625.0),
        "NVDA": dict(price=200.0, high=236.0, low=164.0),
        "AMZN": dict(price=271.0, high=278.0, low=196.0),
        "META": dict(price=556.0, high=796.0, low=520.0, closes=declining_series(260, 800.0, 1.0)),
    }
    kwargs = presets.get(symbol, dict(price=100.0))
    return make_snapshot(symbol, name=name, **kwargs)


def _fake_fx():
    return 17_990.0, True


class TestBuildReport(unittest.TestCase):
    def test_end_to_end_offline(self):
        rep = build_report(
            config.DEFAULT_ASSETS,
            cash_usd=4000.0,
            target_idr=1_000_000_000.0,
            snapshot_provider=_fake_provider,
            fx_provider=_fake_fx,
        )
        self.assertEqual(len(rep.scores), 4)
        self.assertEqual(rep.errors, [])
        self.assertIsNotNone(rep.goal)
        self.assertTrue(rep.goal.is_live_fx)
        self.assertIsNotNone(rep.allocation)
        self.assertEqual(len(rep.allocation.lines), 4)

    def test_provider_failure_is_captured(self):
        def flaky(symbol: str, name: str):
            if symbol == "NVDA":
                raise RuntimeError("boom")
            return _fake_provider(symbol, name)

        rep = build_report(
            config.DEFAULT_ASSETS, snapshot_provider=flaky, fx_provider=_fake_fx
        )
        self.assertEqual(len(rep.scores), 3)
        self.assertEqual(len(rep.errors), 1)
        self.assertEqual(rep.errors[0][0], "NVDA")

    def test_usd_idr_override_marks_not_live(self):
        rep = build_report(
            config.DEFAULT_ASSETS, usd_idr=16000.0, snapshot_provider=_fake_provider
        )
        self.assertEqual(rep.goal.usd_idr, 16000.0)
        self.assertFalse(rep.goal.is_live_fx)


class TestRenderers(unittest.TestCase):
    def setUp(self):
        self.report = build_report(
            config.DEFAULT_ASSETS, snapshot_provider=_fake_provider, fx_provider=_fake_fx
        )

    def test_text_render(self):
        text = report.render_text(self.report)
        self.assertIn("REAL-TIME INVESTMENT SCORES", text)
        self.assertIn("GOAL CHECK", text)
        self.assertIn("DISCLAIMER", text)

    def test_markdown_render(self):
        md = report.render_markdown(self.report)
        self.assertIn("# Real-time investment scores", md)
        self.assertIn("| Asset |", md)

    def test_json_render_is_valid(self):
        payload = json.loads(report.render_json(self.report))
        self.assertIn("scores", payload)
        self.assertIn("goal", payload)
        self.assertIn("allocation", payload)
        self.assertEqual(len(payload["scores"]), 4)


if __name__ == "__main__":
    unittest.main()
