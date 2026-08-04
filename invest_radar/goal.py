"""Honest 'can I actually hit my number?' maths.

A Buffett-minded advisor does not promise 140%/yr. This module converts the IDR
target to USD at the live rate, shows what return a lump-sum-only plan would
require (usually implausible), and then computes the monthly contribution needed
under realistic return assumptions - the honest path to the goal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import GoalConfig


def required_cagr(start: float, target: float, years: float) -> float:
    """Annualised return needed to grow ``start`` into ``target`` with no top-ups."""
    if start <= 0 or years <= 0:
        return float("inf")
    return (target / start) ** (1.0 / years) - 1.0


def future_value_lump_sum(start: float, years: float, annual_return: float) -> float:
    """Value of the initial cash after ``years`` at ``annual_return`` (monthly comp)."""
    i = annual_return / 12.0
    n = years * 12.0
    return start * (1.0 + i) ** n


def required_monthly(start: float, target: float, years: float, annual_return: float) -> float:
    """Monthly deposit needed to reach ``target`` given a starting balance.

    Uses a standard future-value-of-an-annuity (contributions at period end).
    Returns ``0`` if the starting cash already compounds past the target.
    """
    i = annual_return / 12.0
    n = years * 12.0
    fv_start = future_value_lump_sum(start, years, annual_return)
    if fv_start >= target:
        return 0.0
    shortfall = target - fv_start
    if i == 0:
        return shortfall / n
    annuity_factor = ((1.0 + i) ** n - 1.0) / i
    return shortfall / annuity_factor


@dataclass
class ScenarioRow:
    horizon_years: int
    scenario: str
    annual_return: float
    lump_sum_fv_usd: float
    monthly_usd: float


@dataclass
class GoalAnalysis:
    start_cash_usd: float
    target_idr: float
    fx_usd_idr: float | None
    target_usd: float | None
    multiple: float | None
    cagr_by_horizon: dict[int, float]
    rows: list[ScenarioRow] = field(default_factory=list)
    headline: str = ""


def analyze_goal(cfg: GoalConfig, fx_usd_idr: float | None) -> GoalAnalysis:
    """Produce the full goal analysis for the configured horizons and scenarios."""
    target_usd = (cfg.target_idr / fx_usd_idr) if fx_usd_idr else None
    multiple = (target_usd / cfg.start_cash_usd) if target_usd else None

    cagr_by_horizon: dict[int, float] = {}
    rows: list[ScenarioRow] = []
    if target_usd is not None:
        for years in cfg.horizons_years:
            cagr_by_horizon[years] = required_cagr(cfg.start_cash_usd, target_usd, years)
            for name, ret in cfg.return_scenarios:
                rows.append(
                    ScenarioRow(
                        horizon_years=years,
                        scenario=name,
                        annual_return=ret,
                        lump_sum_fv_usd=future_value_lump_sum(cfg.start_cash_usd, years, ret),
                        monthly_usd=required_monthly(cfg.start_cash_usd, target_usd, years, ret),
                    )
                )

    headline = _headline(cfg, target_usd, multiple, cagr_by_horizon, rows)
    return GoalAnalysis(
        start_cash_usd=cfg.start_cash_usd,
        target_idr=cfg.target_idr,
        fx_usd_idr=fx_usd_idr,
        target_usd=target_usd,
        multiple=multiple,
        cagr_by_horizon=cagr_by_horizon,
        rows=rows,
        headline=headline,
    )


def _headline(cfg, target_usd, multiple, cagr_by_horizon, rows) -> str:
    if target_usd is None:
        return "FX rate unavailable - cannot convert the IDR target this run."
    worst_cagr = min(cagr_by_horizon.values()) if cagr_by_horizon else float("inf")
    # Pick a realistic (index-like) monthly figure for the longest horizon.
    longest = max(cfg.horizons_years)
    realistic = [
        r for r in rows if r.horizon_years == longest and r.annual_return <= 0.10
    ]
    monthly = realistic[0].monthly_usd if realistic else None
    parts = [
        f"Target 1B IDR ~= ${target_usd:,.0f} (~{multiple:.1f}x your ${cfg.start_cash_usd:,.0f}).",
        f"Lump-sum-only needs ~{worst_cagr * 100:.0f}%/yr - far above even great long-run "
        "returns, so treating the $4k as a one-shot bet would be gambling, not investing.",
    ]
    if monthly is not None:
        parts.append(
            f"Realistic path: keep buying quality on the dips and add about "
            f"${monthly:,.0f}/month at ~10%/yr to reach it in {longest} years."
        )
    return " ".join(parts)
