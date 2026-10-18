"""Render a run as a console summary and a Markdown report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .goal import GoalAnalysis
from .scoring import AssetScore, Portfolio


@dataclass
class RunResult:
    """Everything produced by one hourly run, ready to render or persist."""

    generated_at: datetime
    scores: list[AssetScore]
    portfolio: Portfolio
    goal: GoalAnalysis
    fx_usd_idr: float | None
    market_note: str = ""

    @property
    def stamp(self) -> str:
        return self.generated_at.strftime("%Y-%m-%d %H:%M UTC")

    @property
    def file_stamp(self) -> str:
        return self.generated_at.strftime("%Y%m%d-%H%M")


def _bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "#" * filled + "-" * (width - filled)


def render_console(run: RunResult) -> str:
    """A compact, dependency-free terminal summary."""
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append(f" InvestRadar  |  {run.stamp}")
    lines.append("=" * 64)
    p = run.portfolio
    lines.append(f" OVERALL: {p.overall:5.1f}/100  ->  {p.verdict}")
    if run.market_note:
        lines.append(f" {run.market_note}")
    lines.append("-" * 64)
    for s in run.scores:
        px = f"${s.quote.price:,.2f}" if s.quote.price else "n/a"
        lines.append(f" {s.asset.symbol:<5} {px:>11}  {s.overall:5.1f} [{_bar(s.overall)}] {s.verdict}")
        if s.reasons:
            lines.append(f"        {'; '.join(s.reasons[:3])}")
    lines.append("-" * 64)
    if p.allocation:
        alloc = ", ".join(f"{k} {v:g}%" for k, v in p.allocation.items() if v > 0)
        lines.append(f" New-money split: {alloc or 'hold cash / DCA into SPY'}")
    lines.append("-" * 64)
    lines.append(" GOAL: " + run.goal.headline)
    lines.append("=" * 64)
    return "\n".join(lines)


def _fmt_pct(v: float | None) -> str:
    return f"{v:+.1f}%" if v is not None else "-"


def render_markdown(run: RunResult) -> str:
    """A rich Markdown report suitable for committing to the repo."""
    p = run.portfolio
    g = run.goal
    md: list[str] = []
    md.append("# InvestRadar - Hourly Investment Score")
    md.append("")
    md.append(
        f"_Generated {run.stamp} · source: Yahoo Finance · "
        "educational tool, **not financial advice**._"
    )
    md.append("")
    md.append(f"## Overall: **{p.overall}/100 - {p.verdict}**")
    if run.market_note:
        md.append("")
        md.append(f"> {run.market_note}")
    md.append("")

    md.append("### Watchlist")
    md.append("")
    md.append("| Asset | Price | Score | Verdict | Val | Dip | Trend | Timing |")
    md.append("|---|---:|---:|---|---:|---:|---:|---:|")
    for s in run.scores:
        c = s.components
        px = f"${s.quote.price:,.2f}" if s.quote.price else "n/a"
        md.append(
            f"| {s.asset.name} | {px} | **{s.overall}** | {s.verdict} | "
            f"{c.get('valuation', float('nan')):.0f} | {c['dip']:.0f} | "
            f"{c['trend']:.0f} | {c['timing']:.0f} |"
        )
    md.append("")

    if p.allocation:
        parts = [f"**{k} {v:g}%**" for k, v in p.allocation.items() if v > 0]
        alloc_txt = ", ".join(parts) if parts else "hold cash / drip into SPY"
        md.append(f"**Suggested split of any new contribution:** {alloc_txt}.")
        md.append("")

    md.append("### Why - per-asset signals")
    md.append("")
    for s in run.scores:
        i = s.ind
        md.append(f"- **{s.asset.name} - {s.overall}/100 ({s.verdict})**")
        if s.reasons:
            md.append(f"  - " + "; ".join(s.reasons))
        md.append(
            "  - RSI {rsi}, {ddd} below 52w high, vs 50d {d50}, vs 200d {d200}, "
            "3m {m3}, 6m {m6}".format(
                rsi=f"{i.rsi14:.0f}" if i.rsi14 is not None else "-",
                ddd=f"{abs(i.drawdown_from_high_pct):.0f}%",
                d50=_fmt_pct(i.dist_sma50_pct),
                d200=_fmt_pct(i.dist_sma200_pct),
                m3=_fmt_pct(i.mom_3m_pct),
                m6=_fmt_pct(i.mom_6m_pct),
            )
        )
        if s.asset.note:
            md.append(f"  - _{s.asset.note}_")
    md.append("")

    md.append(f"## Goal check - ${g.start_cash_usd:,.0f} -> 1,000,000,000 IDR")
    md.append("")
    if g.fx_usd_idr:
        md.append(f"_USD/IDR {g.fx_usd_idr:,.0f} · target ~= ${g.target_usd:,.0f}_")
        md.append("")
    md.append(f"{g.headline}")
    md.append("")
    if g.rows:
        md.append("| Horizon | Scenario | Return/yr | $4k grows to | Monthly needed |")
        md.append("|---|---|---:|---:|---:|")
        for r in g.rows:
            md.append(
                f"| {r.horizon_years}y | {r.scenario} | {r.annual_return * 100:.0f}% | "
                f"${r.lump_sum_fv_usd:,.0f} | ${r.monthly_usd:,.0f} |"
            )
        md.append("")
        md.append(
            "_'Monthly needed' = the deposit each month, on top of the initial "
            "cash, to reach the target at that return (contributions compounded)._"
        )
        md.append("")

    md.append("---")
    md.append(
        "**How to read this:** a higher score means valuation, pullback, trend and "
        "momentum currently line up as a *better-than-average* moment to add. It is a "
        "disciplined nudge for dollar-cost-averaging into quality - not a trading "
        "signal or a promise of returns. Score components are each 0-100; overall is a "
        "weighted blend (valuation 35%, dip 30%, trend 20%, timing 15%)."
    )
    return "\n".join(md)
