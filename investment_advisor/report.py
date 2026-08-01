"""Render a :class:`~investment_advisor.advisor.Report` as text, markdown or JSON."""

from __future__ import annotations

import json

from .advisor import Report


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}" if abs(value) < 1000 else f"${value:,.0f}"


def _fmt_idr(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"Rp {value:,.0f}"


def _pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def _bar(score: float, width: int = 10) -> str:
    filled = int(round(score / 100.0 * width))
    return "#" * filled + "-" * (width - filled)


def _dt(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC") if value else "n/a"


def to_dict(report: Report) -> dict:
    """Serialise the report to plain JSON-safe data."""
    goal = report.goal
    alloc = report.allocation
    return {
        "generated_at": report.generated_at.isoformat(),
        "data_asof": report.data_asof.isoformat() if report.data_asof else None,
        "market_state": report.market_state,
        "scores": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "kind": s.kind,
                "currency": s.currency,
                "price": s.price,
                "score": s.score,
                "action": s.action,
                "subscores": s.subscores,
                "metrics": s.metrics,
                "rationale": s.rationale,
            }
            for s in report.scores
        ],
        "goal": None
        if goal is None
        else {
            "start_usd": goal.start_usd,
            "target_idr": goal.target_idr,
            "usd_idr": goal.usd_idr,
            "is_live_fx": goal.is_live_fx,
            "target_usd": goal.target_usd,
            "verdict": goal.verdict,
            "horizons": [
                {
                    "years": h.years,
                    "required_cagr": h.required_cagr,
                    "planning_return": h.planning_return,
                    "required_monthly_usd": h.required_monthly_usd,
                    "lump_sum_projections": {str(k): v for k, v in h.lump_sum_projections.items()},
                }
                for h in goal.horizons
            ],
        },
        "allocation": None
        if alloc is None
        else {
            "cash_usd": alloc.cash_usd,
            "tranche_usd": alloc.tranche_usd,
            "tranches": alloc.tranches,
            "deploy_multiplier": alloc.deploy_multiplier,
            "suggested_deploy_usd": alloc.suggested_deploy_usd,
            "market_temperature": alloc.market_temperature,
            "lines": [
                {
                    "symbol": ln.symbol,
                    "name": ln.name,
                    "kind": ln.kind,
                    "score": ln.score,
                    "action": ln.action,
                    "price": ln.price,
                    "final_weight": ln.final_weight,
                    "dollars": ln.dollars,
                    "approx_shares": ln.approx_shares,
                }
                for ln in alloc.lines
            ],
            "notes": alloc.notes,
        },
        "errors": [{"symbol": sym, "error": msg} for sym, msg in report.errors],
        "disclaimer": report.disclaimer,
    }


def render_json(report: Report) -> str:
    return json.dumps(to_dict(report), indent=2)


def render_text(report: Report) -> str:
    lines: list[str] = []
    rule = "=" * 66
    thin = "-" * 66
    lines.append(rule)
    lines.append("  REAL-TIME INVESTMENT SCORES  -  Warren-Buffett-style DCA plan")
    lines.append(
        f"  Generated {_dt(report.generated_at)}  |  Data as of {_dt(report.data_asof)}"
        f"  |  Market: {report.market_state}"
    )
    lines.append(rule)

    lines.append("")
    lines.append("BUY SCORES  (0-100: how attractive an entry looks right now)")
    lines.append(thin)
    lines.append(f"{'Asset':<24}{'Price':>11}  {'Score':>5}  {'Signal':<10} Action")
    for s in sorted(report.scores, key=lambda x: x.score, reverse=True):
        lines.append(
            f"{s.name[:23]:<24}{_fmt_usd(s.price):>11}  {s.score:>5.1f}  "
            f"[{_bar(s.score)}] {s.action}"
        )
    for s in sorted(report.scores, key=lambda x: x.score, reverse=True):
        if s.rationale:
            lines.append(f"   - {s.name}: " + "; ".join(s.rationale))
    for sym, msg in report.errors:
        lines.append(f"   ! {sym}: data unavailable ({msg})")

    goal = report.goal
    if goal is not None:
        lines.append("")
        lines.append("GOAL CHECK  (the honest maths)")
        lines.append(thin)
        fx_tag = "live" if goal.is_live_fx else "assumed"
        lines.append(
            f"Target {_fmt_idr(goal.target_idr)}  =  {_fmt_usd(goal.target_usd)}"
            f"   (USD/IDR {goal.usd_idr:,.0f}, {fx_tag})"
        )
        lines.append(f"Starting pot: {_fmt_usd(goal.start_usd)}")
        lines.append(f"Verdict: {goal.verdict}")
        for h in goal.horizons:
            lines.append("")
            lines.append(
                f"  Over {h.years:g} years -> required return "
                f"{_pct(h.required_cagr, 0)} per year on the starting pot alone"
            )
            proj = "   ".join(
                f"{_pct(r, 0)}->{_fmt_usd(v)}" for r, v in sorted(h.lump_sum_projections.items())
            )
            lines.append(f"    Lump-sum only: {proj}")
            lines.append(
                f"    To actually reach the goal at {_pct(h.planning_return, 0)}/yr, save "
                f"~{_fmt_usd(h.required_monthly_usd)}/month"
            )

    alloc = report.allocation
    if alloc is not None and alloc.lines:
        lines.append("")
        lines.append("SUGGESTED DCA PLAN  (how to feed cash in)")
        lines.append(thin)
        lines.append(
            f"Cash {_fmt_usd(alloc.cash_usd)} -> {alloc.tranches} tranches of "
            f"~{_fmt_usd(alloc.tranche_usd)}"
        )
        lines.append(
            f"Market temperature: {alloc.market_temperature}  "
            f"(deploy x{alloc.deploy_multiplier:.2f} = {_fmt_usd(alloc.suggested_deploy_usd)} this tranche)"
        )
        lines.append(f"{'Asset':<24}{'Weight':>8}{'This tranche':>14}{'~Shares':>10}")
        for ln in alloc.lines:
            lines.append(
                f"{ln.name[:23]:<24}{_pct(ln.final_weight, 0):>8}"
                f"{_fmt_usd(ln.dollars):>14}{ln.approx_shares:>10.3f}"
            )
        for note in alloc.notes:
            lines.append(f"   - {note}")

    lines.append("")
    lines.append(thin)
    lines.append("DISCLAIMER: " + report.disclaimer)
    return "\n".join(lines)


def render_markdown(report: Report) -> str:
    md: list[str] = []
    md.append("# Real-time investment scores - Warren-Buffett-style DCA plan")
    md.append(
        f"_Generated {_dt(report.generated_at)} - data as of {_dt(report.data_asof)} "
        f"- market: **{report.market_state}**_"
    )

    md.append("\n## Buy scores")
    md.append("Higher = a more attractive entry right now (0-100).\n")
    md.append("| Asset | Price | Score | Action | Why |")
    md.append("|---|---:|---:|---|---|")
    for s in sorted(report.scores, key=lambda x: x.score, reverse=True):
        why = "; ".join(s.rationale)
        md.append(
            f"| {s.name} | {_fmt_usd(s.price)} | **{s.score:.1f}** | {s.action} | {why} |"
        )
    for sym, msg in report.errors:
        md.append(f"| {sym} | n/a | n/a | data error | {msg} |")

    goal = report.goal
    if goal is not None:
        md.append("\n## Goal check")
        fx_tag = "live" if goal.is_live_fx else "assumed"
        md.append(
            f"- **Target:** {_fmt_idr(goal.target_idr)} = {_fmt_usd(goal.target_usd)} "
            f"(USD/IDR {goal.usd_idr:,.0f}, {fx_tag})"
        )
        md.append(f"- **Starting pot:** {_fmt_usd(goal.start_usd)}")
        md.append(f"- **Verdict:** {goal.verdict}")
        md.append("\n| Horizon | Required return/yr | Save/month at "
                  f"{_pct(goal.horizons[0].planning_return, 0) if goal.horizons else 'n/a'} | ")
        md.append("|---|---:|---:|")
        for h in goal.horizons:
            md.append(
                f"| {h.years:g} years | {_pct(h.required_cagr, 0)} | "
                f"{_fmt_usd(h.required_monthly_usd)}/mo |"
            )

    alloc = report.allocation
    if alloc is not None and alloc.lines:
        md.append("\n## Suggested DCA plan")
        md.append(
            f"- Cash **{_fmt_usd(alloc.cash_usd)}** split into **{alloc.tranches}** tranches "
            f"of ~{_fmt_usd(alloc.tranche_usd)}."
        )
        md.append(
            f"- Market temperature: **{alloc.market_temperature}** "
            f"(deploy x{alloc.deploy_multiplier:.2f} = {_fmt_usd(alloc.suggested_deploy_usd)} this tranche)."
        )
        md.append("\n| Asset | Weight | This tranche | ~Shares |")
        md.append("|---|---:|---:|---:|")
        for ln in alloc.lines:
            md.append(
                f"| {ln.name} | {_pct(ln.final_weight, 0)} | {_fmt_usd(ln.dollars)} | "
                f"{ln.approx_shares:.3f} |"
            )
        md.append("")
        for note in alloc.notes:
            md.append(f"- {note}")

    md.append(f"\n> **Disclaimer:** {report.disclaimer}")
    return "\n".join(md)
