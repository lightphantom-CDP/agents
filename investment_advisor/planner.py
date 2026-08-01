"""Goal feasibility maths and a disciplined dollar-cost-averaging plan.

Two responsibilities:

1. :func:`goal_analysis` -- honestly compare a savings goal (in IDR) against a
   starting pot (in USD) and show what return, or what monthly saving, would
   actually be required. This is where the tool refuses to over-promise.
2. :func:`suggest_allocation` -- split a periodic investment across the
   watchlist using Buffett-style policy weights, gently tilted toward whatever
   currently scores as the better value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .scoring import AssetScore


@dataclass
class HorizonProjection:
    years: float
    required_cagr: float
    lump_sum_projections: dict[float, float]  # annual_return -> future value (USD)
    required_monthly_usd: float
    planning_return: float


@dataclass
class GoalAnalysis:
    start_usd: float
    target_idr: float
    usd_idr: float
    is_live_fx: bool
    target_usd: float
    horizons: list[HorizonProjection] = field(default_factory=list)
    verdict: str = ""


@dataclass
class AllocationLine:
    symbol: str
    name: str
    kind: str
    score: float
    action: str
    price: float
    final_weight: float
    dollars: float
    approx_shares: float


@dataclass
class AllocationPlan:
    cash_usd: float
    tranche_usd: float
    tranches: int
    deploy_multiplier: float
    suggested_deploy_usd: float
    market_temperature: str
    lines: list[AllocationLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def required_cagr(start: float, target: float, years: float) -> float:
    if start <= 0 or years <= 0:
        return float("inf")
    return (target / start) ** (1.0 / years) - 1.0


def future_value(start: float, annual_return: float, years: float) -> float:
    return start * (1.0 + annual_return) ** years


def _monthly_rate(annual_return: float) -> float:
    return (1.0 + annual_return) ** (1.0 / 12.0) - 1.0


def future_value_with_contributions(
    start: float, monthly: float, annual_return: float, years: float
) -> float:
    """FV of a lump sum plus fixed monthly contributions, compounded monthly."""
    months = int(round(years * 12))
    mr = _monthly_rate(annual_return)
    fv_start = start * (1.0 + mr) ** months
    if mr == 0:
        fv_contrib = monthly * months
    else:
        fv_contrib = monthly * (((1.0 + mr) ** months - 1.0) / mr)
    return fv_start + fv_contrib


def required_monthly_contribution(
    start: float, target: float, annual_return: float, years: float
) -> float:
    """Monthly saving needed to reach ``target`` given a starting pot."""
    months = int(round(years * 12))
    mr = _monthly_rate(annual_return)
    fv_start = start * (1.0 + mr) ** months
    remaining = target - fv_start
    if remaining <= 0:
        return 0.0
    if mr == 0:
        return remaining / months
    annuity_factor = ((1.0 + mr) ** months - 1.0) / mr
    return remaining / annuity_factor


def goal_analysis(
    start_usd: float,
    target_idr: float,
    usd_idr: float,
    is_live_fx: bool,
    horizons_years: tuple[float, ...] = config.DEFAULT_HORIZONS_YEARS,
    reference_returns: tuple[float, ...] = config.REFERENCE_ANNUAL_RETURNS,
    planning_return: float = config.PLANNING_ANNUAL_RETURN,
) -> GoalAnalysis:
    target_usd = target_idr / usd_idr if usd_idr else float("inf")
    horizons: list[HorizonProjection] = []
    for years in horizons_years:
        horizons.append(
            HorizonProjection(
                years=years,
                required_cagr=required_cagr(start_usd, target_usd, years),
                lump_sum_projections={
                    r: future_value(start_usd, r, years) for r in reference_returns
                },
                required_monthly_usd=required_monthly_contribution(
                    start_usd, target_usd, planning_return, years
                ),
                planning_return=planning_return,
            )
        )

    worst_required = min((h.required_cagr for h in horizons), default=float("inf"))
    if worst_required <= 0.15:
        verdict = "REALISTIC: achievable with steady, disciplined investing."
    elif worst_required <= 0.30:
        verdict = "AMBITIOUS: needs excellent returns and/or extra contributions."
    else:
        verdict = (
            "UNREALISTIC on the starting pot alone: the required return far "
            "exceeds what even great long-term investors sustain. Add monthly "
            "contributions, extend the horizon, or moderate the target."
        )

    return GoalAnalysis(
        start_usd=start_usd,
        target_idr=target_idr,
        usd_idr=usd_idr,
        is_live_fx=is_live_fx,
        target_usd=target_usd,
        horizons=horizons,
        verdict=verdict,
    )


def _market_temperature(avg_score: float) -> tuple[str, float]:
    """Map the average buy score to a label and a deploy multiplier.

    Higher score == cheaper/more fearful market == deploy a little more of the
    dry powder; lower score == richer market == keep more in reserve. The
    multiplier stays close to 1 because timing is unreliable.
    """
    if avg_score >= 70:
        return "FEARFUL / CHEAP - lean in", 1.4
    if avg_score >= 58:
        return "CONSTRUCTIVE", 1.15
    if avg_score >= 46:
        return "NEUTRAL - stay on schedule", 1.0
    if avg_score >= 36:
        return "RICH - stay disciplined", 0.85
    return "EXPENSIVE / GREEDY - hold more dry powder", 0.6


def suggest_allocation(
    cash_usd: float,
    scores: list[AssetScore],
    assets: tuple[config.Asset, ...] = config.DEFAULT_ASSETS,
    tranches: int = config.DEFAULT_DCA_TRANCHES,
) -> AllocationPlan:
    """Split one DCA tranche across the watchlist, tilted by score."""
    policy = {a.symbol: a for a in assets}
    scored = [s for s in scores if s.symbol in policy]
    tranche_usd = cash_usd / tranches if tranches else cash_usd

    avg_score = sum(s.score for s in scored) / len(scored) if scored else 50.0
    temperature, deploy_multiplier = _market_temperature(avg_score)
    suggested_deploy = tranche_usd * deploy_multiplier

    raw_weights: dict[str, float] = {}
    for score in scored:
        base = policy[score.symbol].policy_weight
        tilt = _clamp(score.score / avg_score, 0.6, 1.4) if avg_score > 0 else 1.0
        raw_weights[score.symbol] = base * tilt
    total_weight = sum(raw_weights.values()) or 1.0

    lines: list[AllocationLine] = []
    for score in scored:
        final_weight = raw_weights[score.symbol] / total_weight
        dollars = suggested_deploy * final_weight
        approx_shares = dollars / score.price if score.price else 0.0
        lines.append(
            AllocationLine(
                symbol=score.symbol,
                name=score.name,
                kind=score.kind,
                score=score.score,
                action=score.action,
                price=score.price,
                final_weight=final_weight,
                dollars=dollars,
                approx_shares=approx_shares,
            )
        )
    lines.sort(key=lambda ln: ln.dollars, reverse=True)

    notes = [
        "Dollar-cost average: invest a fixed amount on a fixed cadence "
        f"(this plan splits your cash into {tranches} tranches).",
        "The hourly score only nudges tranche *sizing* - it is not a signal "
        "to trade every hour.",
        "The S&P 500 index is the core; single stocks are higher-risk "
        "satellites. Never let one name dominate.",
    ]

    return AllocationPlan(
        cash_usd=cash_usd,
        tranche_usd=tranche_usd,
        tranches=tranches,
        deploy_multiplier=deploy_multiplier,
        suggested_deploy_usd=suggested_deploy,
        market_temperature=temperature,
        lines=lines,
        notes=notes,
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
