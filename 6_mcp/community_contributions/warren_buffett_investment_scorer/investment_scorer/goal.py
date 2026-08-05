"""Goal planning: can $4,000 become 1,000,000,000 IDR in 3-4 years?

This module does the honest arithmetic a good advisor would do before talking
about entry prices: it converts the rupiah target to USD at the live FX rate,
works out the return the goal implies, and - because that return is almost
always unrealistic from a lump sum alone - sizes the monthly contribution needed
under sober return assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import GoalConfig
from .data import get_usd_idr


def future_value(pv: float, monthly_contribution: float, annual_return: float,
                 years: float) -> float:
    """FV of a lump sum plus end-of-month contributions, compounded monthly."""
    i = annual_return / 12.0
    n = round(years * 12)
    if i == 0:
        return pv + monthly_contribution * n
    growth = (1 + i) ** n
    return pv * growth + monthly_contribution * (growth - 1) / i


def required_cagr(pv: float, fv: float, years: float) -> float:
    if pv <= 0 or fv <= 0 or years <= 0:
        return float("inf")
    return (fv / pv) ** (1.0 / years) - 1.0


def required_monthly_contribution(pv: float, fv: float, annual_return: float,
                                  years: float) -> float:
    """Monthly saving needed to reach ``fv`` given a starting ``pv``."""
    i = annual_return / 12.0
    n = round(years * 12)
    growth = (1 + i) ** n
    lump_grown = pv * growth
    if fv <= lump_grown:
        return 0.0
    if i == 0:
        return (fv - lump_grown) / n
    annuity_factor = (growth - 1) / i
    return (fv - lump_grown) / annuity_factor


@dataclass
class GoalScenario:
    years: float
    annual_return: float
    required_monthly_usd: float
    fv_lump_only_usd: float

    def as_dict(self) -> dict:
        return {
            "years": self.years,
            "annual_return_pct": round(self.annual_return * 100, 1),
            "required_monthly_usd": round(self.required_monthly_usd, 0),
            "fv_lump_only_usd": round(self.fv_lump_only_usd, 0),
        }


@dataclass
class GoalPlan:
    starting_cash_usd: float
    target_idr: float
    fx_usd_idr: float
    fx_is_live: bool
    target_usd: float
    horizons: List[float]
    lump_sum_cagr: Dict[float, float] = field(default_factory=dict)
    scenarios: List[GoalScenario] = field(default_factory=list)
    verdict: str = ""
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "starting_cash_usd": round(self.starting_cash_usd, 2),
            "target_idr": self.target_idr,
            "fx_usd_idr": round(self.fx_usd_idr, 2),
            "fx_is_live": self.fx_is_live,
            "target_usd": round(self.target_usd, 2),
            "horizons_years": self.horizons,
            "lump_sum_required_cagr_pct": {
                str(y): round(r * 100, 1) for y, r in self.lump_sum_cagr.items()
            },
            "contribution_scenarios": [s.as_dict() for s in self.scenarios],
            "verdict": self.verdict,
            "notes": self.notes,
        }


def plan_goal(goal: GoalConfig, demo: bool = False) -> GoalPlan:
    fx, is_live = get_usd_idr(goal.fallback_usd_idr, demo=demo)
    target_usd = goal.target_amount_idr / fx
    horizons = _horizons(goal.min_years, goal.max_years)

    lump_cagr = {y: required_cagr(goal.starting_cash_usd, target_usd, y) for y in horizons}

    scenarios: List[GoalScenario] = []
    for y in horizons:
        for r in goal.return_scenarios:
            scenarios.append(GoalScenario(
                years=y,
                annual_return=r,
                required_monthly_usd=required_monthly_contribution(
                    goal.starting_cash_usd, target_usd, r, y),
                fv_lump_only_usd=future_value(goal.starting_cash_usd, 0.0, r, y),
            ))

    verdict, notes = _assess(goal, target_usd, horizons, lump_cagr)
    return GoalPlan(
        starting_cash_usd=goal.starting_cash_usd,
        target_idr=goal.target_amount_idr,
        fx_usd_idr=fx,
        fx_is_live=is_live,
        target_usd=target_usd,
        horizons=horizons,
        lump_sum_cagr=lump_cagr,
        scenarios=scenarios,
        verdict=verdict,
        notes=notes,
    )


def _horizons(min_years: float, max_years: float) -> List[float]:
    if max_years <= min_years:
        return [min_years]
    mid = round((min_years + max_years) / 2.0, 1)
    seen: List[float] = []
    for y in (min_years, mid, max_years):
        if y not in seen:
            seen.append(y)
    return seen


def _assess(goal: GoalConfig, target_usd: float, horizons: List[float],
            lump_cagr: Dict[float, float]) -> tuple[str, List[str]]:
    best_case = min(lump_cagr.values())   # longest horizon needs the least return
    worst_case = max(lump_cagr.values())

    # Realistic monthly contribution to reach the goal at a solid 15%/yr,
    # over the most generous horizon.
    y = max(horizons)
    monthly_15 = required_monthly_contribution(goal.starting_cash_usd, target_usd, 0.15, y)
    monthly_10 = required_monthly_contribution(goal.starting_cash_usd, target_usd, 0.10, y)

    if worst_case > 0.35:
        verdict = (
            f"Very aggressive. Turning ${goal.starting_cash_usd:,.0f} into "
            f"{goal.target_amount_idr / 1e9:.2f}B IDR (~${target_usd:,.0f}) in "
            f"{min(horizons):.0f}-{max(horizons):.0f} years needs about "
            f"{worst_case * 100:.0f}%/yr (short horizon) to {best_case * 100:.0f}%/yr "
            f"(long horizon) from the lump sum alone - well beyond even Buffett's "
            f"~20%/yr. The realistic path is regular contributions."
        )
    elif worst_case > 0.20:
        verdict = (
            f"Ambitious but not impossible with a great decade of returns: needs "
            f"{best_case * 100:.0f}-{worst_case * 100:.0f}%/yr from the lump sum. "
            f"Adding monthly contributions makes it far safer."
        )
    else:
        verdict = (
            f"Reasonable: the lump sum needs only {best_case * 100:.0f}-"
            f"{worst_case * 100:.0f}%/yr, near long-run market averages."
        )

    notes = [
        f"To hit the goal in {y:.0f} years assuming a strong 15%/yr, save about "
        f"${monthly_15:,.0f}/month; at a more typical 10%/yr, about ${monthly_10:,.0f}/month.",
        "Warren Buffett's edge is ~20%/yr sustained over decades - treat anything "
        "above that as speculation, not a plan.",
        "Keep a low-cost S&P 500 index (SPY/VOO) as the core; size single stocks "
        "(NVDA/AMZN/META) so a 50% drawdown in one name can't derail the goal.",
        "Automate monthly buys (dollar-cost averaging) and let this score tilt the "
        "*size* of each buy - add more when scores are high, less when low.",
        "Avoid leverage and options to 'catch up' - the fastest way to lose the "
        "starting $4,000 is trying to 100x it quickly.",
    ]
    return verdict, notes
