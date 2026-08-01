"""Command-line entry point: fetch -> score -> render -> persist.

Typical use (run this hourly)::

    python -m invest_radar                 # print scores + write reports
    python -m invest_radar --serve         # also serve the dashboard locally
    python -m invest_radar --cash 4000     # override starting cash for the goal

Outputs are written under ``invest_radar/reports/`` and an ``index.html`` shortcut
is written next to the package for one double-click access.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import DEFAULT_WATCHLIST, GoalConfig
from .dashboard import render_dashboard
from .datasource import YahooClient
from .goal import analyze_goal
from .report import RunResult, render_console, render_markdown
from .scoring import build_portfolio, score_asset

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
HISTORY_DIR = REPORTS_DIR / "history"


def _market_note(now: datetime, scores) -> str:
    last_ts = max((s.quote.market_time for s in scores if s.quote.market_time), default=None)
    when = ""
    if last_ts:
        dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        when = f" Last trade data ~ {dt.strftime('%a %d %b %Y')}."
    if now.weekday() >= 5:
        return "US markets are closed for the weekend - scores reflect the last close." + when
    return "Scores reflect the latest available price." + when


def run_once(goal_cfg: GoalConfig, watchlist=DEFAULT_WATCHLIST) -> RunResult:
    """Fetch data for the whole watchlist and build a :class:`RunResult`."""
    client = YahooClient()
    scores = []
    for asset in watchlist:
        quote = client.fetch_quote(asset)
        scored = score_asset(asset, quote)
        if scored is not None:
            scores.append(scored)
        else:
            print(f"  ! {asset.symbol}: no usable data ({quote.error})", file=sys.stderr)

    fx = client.fetch_fx("IDR=X")
    portfolio = build_portfolio(scores)
    goal = analyze_goal(goal_cfg, fx)
    now = datetime.now(timezone.utc)
    return RunResult(
        generated_at=now,
        scores=scores,
        portfolio=portfolio,
        goal=goal,
        fx_usd_idr=fx,
        market_note=_market_note(now, scores),
    )


def _append_csv(run: RunResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    symbols = [s.asset.symbol for s in run.scores]
    header = ["timestamp_utc", "fx_usd_idr", "target_usd", "overall"]
    for sym in symbols:
        header += [f"{sym}_price", f"{sym}_score"]
    row = {
        "timestamp_utc": run.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fx_usd_idr": f"{run.fx_usd_idr:.2f}" if run.fx_usd_idr else "",
        "target_usd": f"{run.goal.target_usd:.2f}" if run.goal.target_usd else "",
        "overall": run.portfolio.overall,
    }
    for s in run.scores:
        row[f"{s.asset.symbol}_price"] = f"{s.quote.price:.2f}" if s.quote.price else ""
        row[f"{s.asset.symbol}_score"] = s.overall
    exists = path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def persist(run: RunResult) -> None:
    """Write markdown, HTML dashboard, dated snapshot and the CSV log."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    md = render_markdown(run)
    html = render_dashboard(run)
    (REPORTS_DIR / "latest.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / "dashboard.html").write_text(html, encoding="utf-8")
    (BASE_DIR / "index.html").write_text(html, encoding="utf-8")
    (HISTORY_DIR / f"{run.file_stamp}.md").write_text(md, encoding="utf-8")
    _append_csv(run, HISTORY_DIR / "scores_log.csv")


def serve(port: int = 8000) -> None:
    """Serve the dashboard directory over HTTP for local viewing."""
    import functools
    import http.server
    import socketserver

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(BASE_DIR))
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving InvestRadar dashboard at http://localhost:{port}/index.html")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="InvestRadar - hourly investment scores")
    parser.add_argument("--cash", type=float, default=None, help="starting cash in USD for the goal")
    parser.add_argument("--target-idr", type=float, default=None, help="goal amount in IDR")
    parser.add_argument("--no-write", action="store_true", help="print only, do not write files")
    parser.add_argument("--serve", action="store_true", help="serve the dashboard after running")
    parser.add_argument("--port", type=int, default=8000, help="port for --serve")
    args = parser.parse_args(argv)

    goal_cfg = GoalConfig()
    overrides = {}
    if args.cash is not None:
        overrides["start_cash_usd"] = args.cash
    if args.target_idr is not None:
        overrides["target_idr"] = args.target_idr
    if overrides:
        goal_cfg = GoalConfig(**{**goal_cfg.__dict__, **overrides})

    run = run_once(goal_cfg)
    if not run.scores:
        print("No market data could be fetched this run.", file=sys.stderr)
        return 1

    print(render_console(run))
    if not args.no_write:
        persist(run)
        print(f"\nWrote reports to {REPORTS_DIR} and {BASE_DIR / 'index.html'}")
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
