"""Command-line entry point.

    python -m investment_scorer                 # pretty console report
    python -m investment_scorer --snapshot      # also write SNAPSHOT.md
    python -m investment_scorer --markdown out.md
    python -m investment_scorer --json out.json
    python -m investment_scorer --no-fundamentals   # price/timing only (faster)

Designed to be safe to run on a schedule (e.g. hourly): every network call is
best-effort, and a single failing holding degrades to an ERROR row instead of
crashing the run.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config, report
from .goal import GoalAnalysis, analyse
from .indicators import build_snapshot
from .scoring import HoldingScore, build_score
from .yahoo import YahooClient

DEFAULT_SNAPSHOT = Path(__file__).resolve().parent / "SNAPSHOT.md"


def _gather(no_fundamentals: bool) -> tuple[list[HoldingScore], GoalAnalysis, float | None]:
    client = YahooClient()

    usd_idr = client.usd_idr()
    goal_analysis = analyse(usd_idr)

    market_price: float | None = None
    ctx = client.history(config.MARKET_CONTEXT_SYMBOL, rng="5d", interval="1d")
    if ctx:
        market_price = ctx.price

    scores: list[HoldingScore] = []
    for holding in config.HOLDINGS:
        try:
            hist = client.history(holding.symbol)
            if hist is None or not hist.closes:
                scores.append(HoldingScore(holding=holding, error="no price data"))
                continue
            fundamentals = {} if no_fundamentals else client.fundamentals(holding.symbol)
            snap = build_snapshot(
                hist.closes, hist.price, hist.fifty_two_week_high, hist.fifty_two_week_low
            )
            score = build_score(holding, snap, fundamentals)
            score.currency = hist.currency or "USD"
            scores.append(score)
        except Exception as exc:  # noqa: BLE001 - never let one name kill the run
            scores.append(HoldingScore(holding=holding, error=f"{type(exc).__name__}: {exc}"))
    return scores, goal_analysis, market_price


def _to_jsonable(scores: list[HoldingScore], goal: GoalAnalysis, market_price, generated_at):
    def clean(obj):
        if dataclasses.is_dataclass(obj):
            return {k: clean(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj

    return {
        "generated_at": generated_at.isoformat(),
        "market_sp500_index": market_price,
        "goal": clean(goal),
        "holdings": [
            {
                "symbol": s.holding.symbol,
                "name": s.holding.name,
                "kind": s.holding.kind,
                "price": s.price,
                "currency": s.currency,
                "composite": s.composite,
                "timing_score": s.timing_score,
                "quality_score": s.quality_score,
                "verdict": s.verdict.label if s.verdict else None,
                "action": s.verdict.action if s.verdict else None,
                "good_price_now": s.good_price_now,
                "analyst_upside": s.analyst_upside,
                "timing_factors": [clean(f) for f in s.timing_factors],
                "quality_factors": [clean(f) for f in s.quality_factors],
                "notes": s.notes,
                "error": s.error,
            }
            for s in scores
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="investment_scorer",
        description="Score whether now is an attractive price to add to your holdings.",
    )
    parser.add_argument("--json", nargs="?", const="-", metavar="PATH",
                        help="emit JSON (to stdout if no path given)")
    parser.add_argument("--markdown", nargs="?", const=str(DEFAULT_SNAPSHOT), metavar="PATH",
                        help="write a Markdown report (default: SNAPSHOT.md)")
    parser.add_argument("--snapshot", action="store_true",
                        help="shortcut for --markdown SNAPSHOT.md")
    parser.add_argument("--no-fundamentals", action="store_true",
                        help="skip fundamentals; score on price/timing only")
    parser.add_argument("--quiet", action="store_true",
                        help="do not print the console report")
    args = parser.parse_args(argv)

    generated_at = datetime.now(timezone.utc)
    scores, goal_analysis, market_price = _gather(args.no_fundamentals)

    if not args.quiet:
        print(report.render_console(scores, goal_analysis, market_price, generated_at))

    md_target: str | None = args.markdown
    if args.snapshot and not md_target:
        md_target = str(DEFAULT_SNAPSHOT)
    if md_target:
        md = report.render_markdown(scores, goal_analysis, market_price, generated_at)
        Path(md_target).write_text(md + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"\n[wrote Markdown report -> {md_target}]")

    if args.json is not None:
        payload = json.dumps(
            _to_jsonable(scores, goal_analysis, market_price, generated_at), indent=2
        )
        if args.json == "-":
            print(payload)
        else:
            Path(args.json).write_text(payload + "\n", encoding="utf-8")
            if not args.quiet:
                print(f"[wrote JSON -> {args.json}]")

    # For CI: also surface the summary in the GitHub Actions job summary.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            md = report.render_markdown(scores, goal_analysis, market_price, generated_at)
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(md + "\n")
        except OSError:
            pass

    # Exit non-zero only if we got nothing useful at all.
    if all(s.error for s in scores):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
