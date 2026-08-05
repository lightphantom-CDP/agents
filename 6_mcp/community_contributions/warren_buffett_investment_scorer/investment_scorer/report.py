"""Rendering: turn scores + a goal plan into console text, Markdown and JSON."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .config import AppConfig, label_for_score
from .goal import GoalPlan
from .scoring import ScoreResult


def _bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100.0 * width))
    return "#" * filled + "-" * (width - filled)


def us_market_session(now: Optional[datetime] = None) -> str:
    """Rough US-equities session label (ignores holidays) for context only."""
    now = now or datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return "weekend (US market closed)"
    minutes = now.hour * 60 + now.minute
    # Regular session ~13:30-20:00 UTC (09:30-16:00 ET, standard time approx).
    if 13 * 60 + 30 <= minutes <= 20 * 60:
        return "US regular session (approx) - live intraday prices"
    return "US market closed (approx) - prices are last close"


@dataclass
class Report:
    timestamp: datetime
    results: List[ScoreResult]
    plan: GoalPlan
    portfolio_score: float
    overall_label: str
    overall_reason: str
    best_symbol: Optional[str]
    session: str

    @property
    def stale_count(self) -> int:
        return sum(1 for r in self.results if r.stale)

    @property
    def data_warning(self) -> Optional[str]:
        n = self.stale_count
        if n == 0:
            return None
        if n == len(self.results):
            return ("Live market data was unavailable (rate-limited/offline); ALL "
                    "figures below use offline fallback data - do not trade on them.")
        return (f"{n} of {len(self.results)} holdings used offline fallback data - "
                "treat those scores with caution.")

    # ---- JSON ---------------------------------------------------------- #
    def to_json(self) -> dict:
        return {
            "generated_at_utc": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "market_session": self.session,
            "data_warning": self.data_warning,
            "portfolio_score": round(self.portfolio_score, 1),
            "overall_recommendation": self.overall_label,
            "overall_reason": self.overall_reason,
            "best_opportunity": self.best_symbol,
            "holdings": [r.as_dict() for r in self.results],
            "goal_plan": self.plan.as_dict(),
            "disclaimer": DISCLAIMER,
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), indent=2)

    # ---- Console ------------------------------------------------------- #
    def to_console(self) -> str:
        L: List[str] = []
        L.append("=" * 68)
        L.append("  WARREN BUFFETT INVESTMENT SCORER  -  hourly entry-price check")
        L.append("=" * 68)
        L.append(f"  {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}   |   {self.session}")
        if self.data_warning:
            L.append("")
            L.append(f"  !! {self.data_warning}")
        L.append("")
        L.append(f"  PORTFOLIO SIGNAL: {self.portfolio_score:5.1f}/100  ->  {self.overall_label}")
        L.append(f"  [{_bar(self.portfolio_score)}]")
        L.append(f"  {self.overall_reason}")
        L.append("")
        L.append("  " + "-" * 64)
        L.append(f"  {'TICKER':<7}{'PRICE':>11}  {'SCORE':>6}  {'BAR':<22}{'CALL'}")
        L.append("  " + "-" * 64)
        for r in sorted(self.results, key=lambda x: x.composite, reverse=True):
            price = f"{r.currency[:3]} {r.price:,.2f}"
            L.append(
                f"  {r.symbol:<7}{price:>11}  {r.composite:>5.1f}  "
                f"[{_bar(r.composite, 16)}]  {r.label}"
            )
        L.append("  " + "-" * 64)
        L.append("")
        for r in sorted(self.results, key=lambda x: x.composite, reverse=True):
            L.append(f"  * {r.headline}")
            for comp in r.components:
                L.append(f"      - {comp.name}: {comp.score:4.0f}  ({comp.detail})")
            if r.stale or r.source == "demo":
                L.append(f"      ! data source: {r.source}{' (stale fallback)' if r.stale else ''}")
            L.append("")

        L.append("  " + "=" * 64)
        L.append("  GOAL CHECK")
        L.append("  " + "=" * 64)
        p = self.plan
        L.append(
            f"  Target: {p.target_idr / 1e9:.2f}B IDR  ~=  ${p.target_usd:,.0f} USD"
            f"  (USD/IDR {p.fx_usd_idr:,.0f}{' live' if p.fx_is_live else ' fallback'})"
        )
        L.append(f"  Starting cash: ${p.starting_cash_usd:,.0f}")
        cagr = "   ".join(
            f"{y:g}y: {r * 100:.0f}%/yr" for y, r in sorted(p.lump_sum_cagr.items())
        )
        L.append(f"  Lump-sum-only return required -> {cagr}")
        L.append(f"  Verdict: {p.verdict}")
        L.append("")
        L.append("  Monthly saving needed to reach the goal:")
        # Show a compact table for the longest horizon.
        long_h = max(p.horizons)
        for s in [s for s in p.scenarios if s.years == long_h]:
            L.append(
                f"      @ {s.annual_return * 100:>2.0f}%/yr over {s.years:.0f}y: "
                f"~${s.required_monthly_usd:,.0f}/month  "
                f"(lump sum alone grows to ${s.fv_lump_only_usd:,.0f})"
            )
        L.append("")
        for n in p.notes:
            L.append(f"  - {n}")
        L.append("")
        L.append("  " + "-" * 64)
        L.append("  " + DISCLAIMER)
        L.append("  " + "-" * 64)
        return "\n".join(L)

    # ---- Markdown ------------------------------------------------------ #
    def to_markdown(self) -> str:
        M: List[str] = []
        M.append("# Warren Buffett Investment Scorer - Hourly Report")
        M.append("")
        M.append(f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}  ")
        M.append(f"**Market session:** {self.session}")
        M.append("")
        if self.data_warning:
            M.append(f"> **Data warning:** {self.data_warning}")
            M.append("")
        M.append(f"## Portfolio signal: {self.portfolio_score:.1f}/100 - {self.overall_label}")
        M.append("")
        M.append(f"> {self.overall_reason}")
        M.append("")
        M.append("| Ticker | Price | Score | Recommendation | Confidence |")
        M.append("|--------|------:|------:|----------------|------------|")
        for r in sorted(self.results, key=lambda x: x.composite, reverse=True):
            M.append(
                f"| {r.symbol} ({r.name}) | {r.currency[:3]} {r.price:,.2f} | "
                f"{r.composite:.1f} | {r.label} | {r.confidence} |"
            )
        M.append("")
        M.append("### Per-holding breakdown")
        M.append("")
        for r in sorted(self.results, key=lambda x: x.composite, reverse=True):
            M.append(f"#### {r.symbol} - {r.name}: {r.composite:.1f}/100 ({r.label})")
            M.append("")
            M.append("| Pillar | Score | Reading |")
            M.append("|--------|------:|---------|")
            for c in r.components:
                M.append(f"| {c.name} | {c.score:.0f} | {c.detail} |")
            M.append("")
        M.append("## Goal check")
        M.append("")
        p = self.plan
        M.append(
            f"- **Target:** {p.target_idr / 1e9:.2f} billion IDR "
            f"(~${p.target_usd:,.0f} at USD/IDR {p.fx_usd_idr:,.0f}"
            f"{' live' if p.fx_is_live else ' fallback'})"
        )
        M.append(f"- **Starting cash:** ${p.starting_cash_usd:,.0f}")
        M.append("- **Lump-sum-only return required:** " + ", ".join(
            f"{y:g}y -> {r * 100:.0f}%/yr" for y, r in sorted(p.lump_sum_cagr.items())))
        M.append(f"- **Verdict:** {p.verdict}")
        M.append("")
        M.append("**Monthly saving needed (longest horizon):**")
        M.append("")
        M.append("| Assumed return | Required monthly | Lump sum alone becomes |")
        M.append("|---------------:|-----------------:|-----------------------:|")
        long_h = max(p.horizons)
        for s in [s for s in p.scenarios if s.years == long_h]:
            M.append(
                f"| {s.annual_return * 100:.0f}%/yr | ${s.required_monthly_usd:,.0f} | "
                f"${s.fv_lump_only_usd:,.0f} |"
            )
        M.append("")
        for n in p.notes:
            M.append(f"- {n}")
        M.append("")
        M.append(f"> _{DISCLAIMER}_")
        return "\n".join(M)


DISCLAIMER = (
    "Educational decision-support only - NOT financial advice. Markets carry "
    "risk of loss. Do your own research and consider a licensed advisor."
)


def build_report(results: List[ScoreResult], plan: GoalPlan, cfg: AppConfig,
                 now: Optional[datetime] = None) -> Report:
    now = now or datetime.now(timezone.utc)
    weight_by_symbol: Dict[str, float] = {h.symbol: h.target_weight for h in cfg.holdings}
    total_w = sum(weight_by_symbol.get(r.symbol, 0.0) for r in results) or 1.0
    portfolio_score = sum(
        r.composite * weight_by_symbol.get(r.symbol, 0.0) for r in results
    ) / total_w

    label, _ = label_for_score(portfolio_score)
    best = max(results, key=lambda r: r.composite) if results else None
    overall_reason = _overall_reason(portfolio_score, best)

    return Report(
        timestamp=now,
        results=results,
        plan=plan,
        portfolio_score=portfolio_score,
        overall_label=label,
        overall_reason=overall_reason,
        best_symbol=best.symbol if best else None,
        session=us_market_session(now),
    )


def _overall_reason(portfolio_score: float, best: Optional[ScoreResult]) -> str:
    if portfolio_score >= 66:
        base = "Broadly attractive prices right now - a good hour to deploy fresh cash."
    elif portfolio_score >= 50:
        base = "Fair value overall - stick to your regular dollar-cost-averaging buy."
    else:
        base = "Prices look full - a smaller buy or patience is reasonable this hour."
    if best and best.composite >= 66:
        base += f" Best single opportunity: {best.symbol} ({best.composite:.0f}/100)."
    return base


def save_reports(report: Report, output_dir: str) -> Dict[str, str]:
    """Persist timestamped + 'latest' Markdown/JSON; return the file paths."""
    os.makedirs(output_dir, exist_ok=True)
    stamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
    paths = {
        "markdown": os.path.join(output_dir, f"report_{stamp}.md"),
        "json": os.path.join(output_dir, f"report_{stamp}.json"),
        "latest_md": os.path.join(output_dir, "latest.md"),
        "latest_json": os.path.join(output_dir, "latest.json"),
    }
    with open(paths["markdown"], "w") as fh:
        fh.write(report.to_markdown())
    with open(paths["json"], "w") as fh:
        fh.write(report.to_json_str())
    with open(paths["latest_md"], "w") as fh:
        fh.write(report.to_markdown())
    with open(paths["latest_json"], "w") as fh:
        fh.write(report.to_json_str())
    return paths
