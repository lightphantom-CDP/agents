"""Goal maths: turn "$4,000 now -> 1,000,000,000 IDR in 3-4 years" into
honest, concrete numbers.

Nothing here is a promise of returns - it simply reports the compound growth
rate the goal *implies* and how it compares to historically achievable rates,
plus how regular contributions change the picture.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import GOAL, Goal


@dataclass
class Projection:
    label: str
    annual_return: float
    final_value_usd: float
    required_monthly_usd: float  # to still hit the target at this return


@dataclass
class GoalAnalysis:
    start_usd: float
    target_idr: float
    usd_idr: float
    target_usd: float
    years_low: float
    years_high: float
    required_cagr_low: float   # for the shorter (harder) horizon
    required_cagr_high: float  # for the longer horizon
    monthly_contribution_usd: float
    feasibility: str
    projections: list[Projection] = field(default_factory=list)


def _cagr(start: float, end: float, years: float) -> float:
    if start <= 0 or years <= 0:
        return float("inf")
    return (end / start) ** (1.0 / years) - 1.0


def _future_value(start: float, monthly: float, annual_return: float, years: float) -> float:
    n = int(round(years * 12))
    r_m = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    fv_lump = start * (1.0 + r_m) ** n
    if abs(r_m) < 1e-9:
        fv_contrib = monthly * n
    else:
        fv_contrib = monthly * (((1.0 + r_m) ** n - 1.0) / r_m)
    return fv_lump + fv_contrib


def _required_monthly(start: float, target: float, annual_return: float, years: float) -> float:
    n = int(round(years * 12))
    r_m = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    fv_lump = start * (1.0 + r_m) ** n
    remaining = target - fv_lump
    if remaining <= 0:
        return 0.0
    if abs(r_m) < 1e-9:
        return remaining / n
    factor = ((1.0 + r_m) ** n - 1.0) / r_m
    return remaining / factor


def _feasibility(required_cagr: float) -> str:
    if required_cagr <= 0.10:
        return "ACHIEVABLE - in line with long-run market returns."
    if required_cagr <= 0.15:
        return "AMBITIOUS but historically plausible for a strong portfolio."
    if required_cagr <= 0.20:
        return "AGGRESSIVE - above what broad markets deliver; needs great picks or luck."
    if required_cagr <= 0.30:
        return "VERY AGGRESSIVE - high risk; few investors sustain this for years."
    return "EXTREMELY AGGRESSIVE - closer to speculation than investing; expect large drawdowns."


def analyse(usd_idr: float, goal: Goal = GOAL) -> GoalAnalysis:
    target_usd = goal.target_idr / usd_idr if usd_idr > 0 else float("inf")
    req_low = _cagr(goal.start_capital_usd, target_usd, goal.horizon_years_low)
    req_high = _cagr(goal.start_capital_usd, target_usd, goal.horizon_years_high)

    projections: list[Projection] = []
    # Use the longer horizon for planning (the more forgiving case).
    plan_years = goal.horizon_years_high
    for label, r in goal.reference_returns.items():
        fv = _future_value(
            goal.start_capital_usd, goal.monthly_contribution_usd, r, plan_years
        )
        req_monthly = _required_monthly(
            goal.start_capital_usd, target_usd, r, plan_years
        )
        projections.append(
            Projection(
                label=label,
                annual_return=r,
                final_value_usd=fv,
                required_monthly_usd=req_monthly,
            )
        )

    return GoalAnalysis(
        start_usd=goal.start_capital_usd,
        target_idr=goal.target_idr,
        usd_idr=usd_idr,
        target_usd=target_usd,
        years_low=goal.horizon_years_low,
        years_high=goal.horizon_years_high,
        required_cagr_low=req_low,
        required_cagr_high=req_high,
        monthly_contribution_usd=goal.monthly_contribution_usd,
        feasibility=_feasibility(req_high),
        projections=projections,
    )
