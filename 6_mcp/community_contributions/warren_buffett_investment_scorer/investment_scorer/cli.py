"""Command-line entry point.

Run once (ideal for an hourly cron job) or in a self-scheduling loop:

    python -m investment_scorer                 # score the default portfolio once
    python -m investment_scorer --demo          # offline synthetic data
    python -m investment_scorer --json          # machine-readable output
    python -m investment_scorer --loop --interval 3600   # check every hour
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional

from .config import AppConfig, GoalConfig, holdings_from_env_or_default
from .data import get_series
from .goal import plan_goal
from .report import Report, build_report, save_reports
from .notify import maybe_notify
from .scoring import score_series

_DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def run_once(cfg: AppConfig) -> Report:
    """Fetch, score and assemble a full report for the configured portfolio."""
    results = []
    for h in cfg.holdings:
        series = get_series(
            h.symbol, h.name,
            rng=cfg.history_range,
            cache_ttl=cfg.cache_ttl_seconds,
            demo=cfg.demo,
        )
        results.append(score_series(series, cfg.weights))
    plan = plan_goal(cfg.goal, demo=cfg.demo)
    return build_report(results, plan, cfg, now=datetime.now(timezone.utc))


def _build_config(args: argparse.Namespace) -> AppConfig:
    goal = GoalConfig()
    goal = dataclasses.replace(
        goal,
        starting_cash_usd=args.cash if args.cash is not None else goal.starting_cash_usd,
        target_amount_idr=args.target_idr if args.target_idr is not None else goal.target_amount_idr,
        min_years=args.min_years if args.min_years is not None else goal.min_years,
        max_years=args.max_years if args.max_years is not None else goal.max_years,
        fallback_usd_idr=args.fx if args.fx is not None else goal.fallback_usd_idr,
    )
    cfg = AppConfig(
        holdings=holdings_from_env_or_default(),
        goal=goal,
        demo=args.demo,
    )
    return cfg


def _emit(report: Report, args: argparse.Namespace) -> None:
    if args.json:
        print(report.to_json_str())
    elif args.markdown:
        print(report.to_markdown())
    else:
        print(report.to_console())

    if not args.no_save:
        try:
            paths = save_reports(report, args.output)
            if not args.quiet and not args.json:
                print(f"\n[saved] {paths['latest_md']}")
        except Exception as err:
            print(f"[warn] could not save reports: {err}", file=sys.stderr)

    if args.notify:
        sent = maybe_notify(report, threshold=args.notify_threshold)
        if not args.quiet and not args.json:
            print(f"[notify] {'sent' if sent else 'no alert / not configured'}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="investment_scorer",
        description="Hourly Warren-Buffett-style entry-price scorer for your portfolio.",
    )
    p.add_argument("--demo", action="store_true",
                   help="Use deterministic offline data (no network).")
    p.add_argument("--loop", action="store_true",
                   help="Keep running and re-score every --interval seconds.")
    p.add_argument("--interval", type=int, default=3600,
                   help="Seconds between checks in --loop mode (default 3600 = hourly).")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    p.add_argument("--markdown", action="store_true", help="Print a Markdown report.")
    p.add_argument("--output", default=_DEFAULT_OUTPUT,
                   help="Directory for saved reports (default: ./reports).")
    p.add_argument("--no-save", action="store_true", help="Do not write report files.")
    p.add_argument("--notify", action="store_true",
                   help="Send a Pushover alert on strong buy signals (needs env vars).")
    p.add_argument("--notify-threshold", type=float, default=66.0,
                   help="Score at/above which to alert (default 66).")
    p.add_argument("--quiet", action="store_true", help="Reduce incidental output.")
    # Goal overrides
    p.add_argument("--cash", type=float, help="Starting cash in USD (default 4000).")
    p.add_argument("--target-idr", type=float, dest="target_idr",
                   help="Target amount in IDR (default 1e9).")
    p.add_argument("--min-years", type=float, dest="min_years", help="Min horizon (default 3).")
    p.add_argument("--max-years", type=float, dest="max_years", help="Max horizon (default 4).")
    p.add_argument("--fx", type=float, help="Fallback USD/IDR if live FX is unavailable.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = _build_config(args)

    if not args.loop:
        report = run_once(cfg)
        _emit(report, args)
        return 0

    if not args.quiet:
        print(f"[loop] scoring every {args.interval}s - Ctrl+C to stop.")
    while True:
        try:
            report = run_once(cfg)
            _emit(report, args)
        except KeyboardInterrupt:
            print("\n[loop] stopped.")
            return 0
        except Exception as err:  # never let one bad hour kill the scheduler
            print(f"[loop] error this cycle: {err}", file=sys.stderr)
        try:
            time.sleep(max(5, args.interval))
        except KeyboardInterrupt:
            print("\n[loop] stopped.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
