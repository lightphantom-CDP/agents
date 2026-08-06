"""Rendering: turn scored holdings + the goal analysis into a console report
and an equivalent Markdown snapshot.
"""

from __future__ import annotations

from datetime import datetime

from .goal import GoalAnalysis
from .scoring import FactorScore, HoldingScore

DISCLAIMER = (
    "Educational tool, NOT financial advice. Scores are mechanical signals from "
    "public data (delayed up to ~15 min), not a recommendation to buy or sell. "
    "Markets carry risk of loss; do your own research."
)


# --------------------------------------------------------------------------- #
# formatting helpers
# --------------------------------------------------------------------------- #
def _money(value: float | None, symbol: str = "$", digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{symbol}{value:,.{digits}f}"


def _score(value: float | None) -> str:
    return "  -" if value is None else f"{value:3.0f}"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.1f}%"


def _factor_line(f: FactorScore) -> str:
    return f"      - {f.name:<24} {_score(f.score)}   ({f.detail})"


# --------------------------------------------------------------------------- #
# console
# --------------------------------------------------------------------------- #
def render_console(
    scores: list[HoldingScore],
    goal: GoalAnalysis,
    market_price: float | None,
    generated_at: datetime,
) -> str:
    lines: list[str] = []
    add = lines.append

    add("=" * 78)
    add("  REAL-TIME INVESTMENT TIMING SCORES  (Warren Buffett lens)")
    add(f"  Generated: {generated_at:%Y-%m-%d %H:%M UTC}")
    if market_price:
        add(f"  S&P 500 index level (context): {market_price:,.2f}")
    add("=" * 78)
    add("")
    add(f"  !! {DISCLAIMER}")
    add("")

    # summary table
    header = f"  {'HOLDING':<20}{'PRICE':>12}  {'COMP':>4} {'TIME':>4} {'QUAL':>4}  {'VERDICT':<16} GOOD NOW?"
    add(header)
    add("  " + "-" * (len(header) - 2))
    for s in scores:
        if s.error:
            add(f"  {s.holding.name:<20}{'ERROR':>12}  {s.error}")
            continue
        verdict = s.verdict.label if s.verdict else "n/a"
        add(
            f"  {s.holding.name:<20}"
            f"{_money(s.price):>12}  "
            f"{_score(s.composite):>4} "
            f"{_score(s.timing_score):>4} "
            f"{_score(s.quality_score):>4}  "
            f"{verdict:<16} {s.good_price_now}"
        )
    add("")

    # per-holding detail
    for s in scores:
        if s.error:
            continue
        add("-" * 78)
        add(f"  {s.holding.name} ({s.holding.symbol})   {_money(s.price)}")
        if s.verdict:
            add(f"    Composite {_score(s.composite)}/100 -> {s.verdict.label}: {s.verdict.action}")
        add("    Timing factors (is the price attractive now?):")
        for f in s.timing_factors:
            add(_factor_line(f))
        if s.holding.kind != "index":
            add("    Quality / value factors (Buffett lens):")
            for f in s.quality_factors:
                add(_factor_line(f))
        if s.analyst_upside is not None:
            add(f"    Analyst mean-target upside: {_pct(s.analyst_upside)} (context only)")
        for note in s.notes:
            add(f"    * {note}")
        add("")

    # goal section
    add("=" * 78)
    add("  GOAL REALITY CHECK")
    add("=" * 78)
    add(
        f"  Start: {_money(goal.start_usd)}   Target: {goal.target_idr:,.0f} IDR "
        f"(~{_money(goal.target_usd)} at {goal.usd_idr:,.0f} IDR/USD)"
    )
    add(
        f"  Required return (lump sum only): "
        f"{_pct(goal.required_cagr_high)}/yr over {goal.years_high:.0f}y  |  "
        f"{_pct(goal.required_cagr_low)}/yr over {goal.years_low:.0f}y"
    )
    add(f"  Feasibility: {goal.feasibility}")
    add("")
    add(f"  Projections over {goal.years_high:.0f} years "
        f"(start {_money(goal.start_usd)}, +{_money(goal.monthly_contribution_usd)}/mo):")
    add(f"    {'Scenario':<32}{'End value':>14}{'To hit target: $/mo':>22}")
    add("    " + "-" * 66)
    for p in goal.projections:
        hit = "already there" if p.final_value_usd >= goal.target_usd else ""
        add(
            f"    {p.label:<32}{_money(p.final_value_usd, digits=0):>14}"
            f"{_money(p.required_monthly_usd, digits=0):>22} {hit}"
        )
    add("")
    add("  Takeaway: with a lump sum alone this goal needs a very high return.")
    add("  Adding steady monthly contributions is the realistic lever - the table")
    add("  above shows the $/month needed at each assumed return.")
    add("")
    add("=" * 78)
    add(f"  {DISCLAIMER}")
    add("=" * 78)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# markdown
# --------------------------------------------------------------------------- #
def render_markdown(
    scores: list[HoldingScore],
    goal: GoalAnalysis,
    market_price: float | None,
    generated_at: datetime,
) -> str:
    md: list[str] = []
    add = md.append

    add("# Real-Time Investment Timing Scores")
    add("")
    add("_Warren Buffett lens: quality businesses at fair prices, bought patiently._")
    add("")
    add(f"**Generated:** {generated_at:%Y-%m-%d %H:%M UTC}  ")
    if market_price:
        add(f"**S&P 500 index level (context):** {market_price:,.2f}  ")
    add(f"**USD/IDR:** {goal.usd_idr:,.0f}")
    add("")
    add(f"> **Disclaimer.** {DISCLAIMER}")
    add("")

    add("## Summary")
    add("")
    add("| Holding | Price | Composite | Timing | Quality | Verdict | Good price now? |")
    add("|---|---:|---:|---:|---:|---|---|")
    for s in scores:
        if s.error:
            add(f"| {s.holding.name} | ERROR | | | | {s.error} | |")
            continue
        verdict = s.verdict.label if s.verdict else "n/a"
        add(
            f"| {s.holding.name} | {_money(s.price)} | "
            f"**{_score(s.composite).strip()}** | {_score(s.timing_score).strip()} | "
            f"{_score(s.quality_score).strip()} | {verdict} | {s.good_price_now} |"
        )
    add("")
    add("_Composite 0-100: higher = more attractive entry. 78+ strong buy zone, "
        "62-77 accumulate, 46-61 fair, 32-45 patience, <32 expensive._")
    add("")

    add("## Detail")
    for s in scores:
        if s.error:
            add(f"\n### {s.holding.name} ({s.holding.symbol})\n\n_Data unavailable: {s.error}_")
            continue
        add(f"\n### {s.holding.name} ({s.holding.symbol}) - {_money(s.price)}")
        if s.verdict:
            add("")
            add(f"**Composite {_score(s.composite).strip()}/100 -> {s.verdict.label}.** {s.verdict.action}")
        add("")
        add("| Factor | Score | Detail |")
        add("|---|---:|---|")
        add("| _Timing_ | | |")
        for f in s.timing_factors:
            add(f"| {f.name} | {_score(f.score).strip()} | {f.detail} |")
        if s.holding.kind != "index":
            add("| _Quality / value_ | | |")
            for f in s.quality_factors:
                add(f"| {f.name} | {_score(f.score).strip()} | {f.detail} |")
        if s.analyst_upside is not None:
            add("")
            add(f"Analyst mean-target upside: **{_pct(s.analyst_upside)}** (context only).")
        for note in s.notes:
            add(f"\n> {note}")
    add("")

    add("## Goal reality check")
    add("")
    add(f"- **Start:** {_money(goal.start_usd)}")
    add(f"- **Target:** {goal.target_idr:,.0f} IDR (~{_money(goal.target_usd)} at {goal.usd_idr:,.0f} IDR/USD)")
    add(f"- **Required return (lump sum):** {_pct(goal.required_cagr_high)}/yr over "
        f"{goal.years_high:.0f}y, {_pct(goal.required_cagr_low)}/yr over {goal.years_low:.0f}y")
    add(f"- **Feasibility:** {goal.feasibility}")
    add("")
    add(f"Projections over {goal.years_high:.0f} years "
        f"(start {_money(goal.start_usd)}, +{_money(goal.monthly_contribution_usd)}/mo):")
    add("")
    add("| Scenario | End value | Monthly needed to hit target |")
    add("|---|---:|---:|")
    for p in goal.projections:
        note = " (already there)" if p.final_value_usd >= goal.target_usd else ""
        add(
            f"| {p.label} | {_money(p.final_value_usd, digits=0)} | "
            f"{_money(p.required_monthly_usd, digits=0)}{note} |"
        )
    add("")
    add("**Takeaway:** a lump sum alone implies a very high required return for this "
        "target and horizon. Steady monthly contributions are the realistic lever; the "
        "table shows the amount per month needed under each assumed return.")
    add("")
    add(f"---\n\n_{DISCLAIMER}_")
    return "\n".join(md)
