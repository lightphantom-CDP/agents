"""Command-line entry point: ``python -m investment_advisor``.

Examples:
    python -m investment_advisor                     # default watchlist & goal
    python -m investment_advisor --format markdown   # for a GitHub summary
    python -m investment_advisor --format json --save out.json
    python -m investment_advisor --cash 4000 --target-idr 1e9 --tickers SPY,NVDA
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, config, report
from .advisor import build_report

_INDEX_SYMBOLS = {"SPY", "VOO", "IVV", "VTI", "^GSPC", "QQQ", "DIA"}


def _assets_from_tickers(raw: str) -> tuple[config.Asset, ...]:
    symbols = [t.strip().upper() for t in raw.split(",") if t.strip()]
    assets = []
    for symbol in symbols:
        is_index = symbol in _INDEX_SYMBOLS
        assets.append(
            config.Asset(
                symbol=symbol,
                name=symbol,
                kind="index" if is_index else "stock",
                # Relative weights; suggest_allocation normalises them. The
                # index gets a larger core share, Buffett style.
                policy_weight=3.0 if is_index else 1.0,
            )
        )
    return tuple(assets)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="investment_advisor",
        description="Real-time buy scores + a Buffett-style DCA plan measured against your goal.",
    )
    parser.add_argument("--cash", type=float, default=config.DEFAULT_CASH_USD,
                        help="Available cash in USD (default: %(default)s).")
    parser.add_argument("--target-idr", type=float, default=config.DEFAULT_TARGET_IDR,
                        help="Savings goal in IDR (default: %(default)s).")
    parser.add_argument("--usd-idr", type=float, default=None,
                        help="Override USD/IDR rate (default: fetch live, fall back to assumption).")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated watchlist, e.g. SPY,NVDA,AMZN,META.")
    parser.add_argument("--horizons", type=str, default=None,
                        help="Comma-separated horizons in years, e.g. 3,4.")
    parser.add_argument("--tranches", type=int, default=config.DEFAULT_DCA_TRANCHES,
                        help="Number of DCA tranches to split cash into (default: %(default)s).")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text",
                        help="Output format (default: %(default)s).")
    parser.add_argument("--save", type=str, default=None,
                        help="Also write the rendered output to this file path.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    assets = _assets_from_tickers(args.tickers) if args.tickers else config.DEFAULT_ASSETS
    if args.horizons:
        horizons = tuple(float(h) for h in args.horizons.split(",") if h.strip())
    else:
        horizons = config.DEFAULT_HORIZONS_YEARS

    result = build_report(
        assets,
        cash_usd=args.cash,
        target_idr=args.target_idr,
        usd_idr=args.usd_idr,
        horizons_years=horizons,
        tranches=args.tranches,
    )

    renderers = {
        "text": report.render_text,
        "markdown": report.render_markdown,
        "json": report.render_json,
    }
    rendered = renderers[args.format](result)
    print(rendered)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
        print(f"\n[saved to {args.save}]", file=sys.stderr)

    if not result.scores:
        print("\n[warning] no market data could be fetched", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
