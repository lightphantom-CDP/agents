"""Orchestration: fetch data, score assets, build the goal + allocation plan.

The data providers are injectable so the whole report can be built from
synthetic snapshots in tests, with no network access.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import config, data, planner, scoring
from .planner import AllocationPlan, GoalAnalysis
from .scoring import AssetScore

SnapshotProvider = Callable[[str, str], data.AssetSnapshot]
FxProvider = Callable[[], "tuple[float, bool]"]

DISCLAIMER = (
    "Educational tool, NOT financial advice. Markets are uncertain; single "
    "stocks can fall 50%+ and not recover. Past performance does not predict "
    "the future. Only invest money you can leave untouched, and consider a "
    "licensed advisor for decisions that matter."
)


@dataclass
class Report:
    generated_at: datetime
    scores: list[AssetScore] = field(default_factory=list)
    goal: GoalAnalysis | None = None
    allocation: AllocationPlan | None = None
    errors: list[tuple[str, str]] = field(default_factory=list)
    market_state: str = "UNKNOWN"
    data_asof: datetime | None = None
    disclaimer: str = DISCLAIMER


def _default_snapshot_provider(symbol: str, name: str) -> data.AssetSnapshot:
    return data.get_snapshot(symbol, name=name)


def _infer_market_state(now_utc: datetime) -> str:
    """Rough US-market open/closed hint when the feed does not supply one.

    Approximates NYSE regular hours (13:30-20:00 UTC on weekdays) and ignores
    market holidays. The authoritative freshness signal is always the
    ``Data as of`` timestamp shown in the report.
    """
    if now_utc.weekday() >= 5:
        return "CLOSED (weekend)"
    minutes = now_utc.hour * 60 + now_utc.minute
    if 13 * 60 + 30 <= minutes < 20 * 60:
        return "OPEN (approx)"
    return "CLOSED (approx)"


def build_report(
    assets: tuple[config.Asset, ...] = config.DEFAULT_ASSETS,
    *,
    cash_usd: float = config.DEFAULT_CASH_USD,
    target_idr: float = config.DEFAULT_TARGET_IDR,
    usd_idr: float | None = None,
    horizons_years: tuple[float, ...] = config.DEFAULT_HORIZONS_YEARS,
    tranches: int = config.DEFAULT_DCA_TRANCHES,
    snapshot_provider: SnapshotProvider | None = None,
    fx_provider: FxProvider | None = None,
) -> Report:
    snapshot_provider = snapshot_provider or _default_snapshot_provider

    if usd_idr is not None:
        rate, is_live = usd_idr, False
    elif fx_provider is not None:
        rate, is_live = fx_provider()
    else:
        rate, is_live = data.get_usd_idr()

    scores: list[AssetScore] = []
    errors: list[tuple[str, str]] = []
    market_state = "UNKNOWN"
    data_asof: datetime | None = None

    for asset in assets:
        try:
            snapshot = snapshot_provider(asset.symbol, asset.name)
        except Exception as exc:  # noqa: BLE001 - surface any provider failure per-asset
            errors.append((asset.symbol, str(exc)))
            continue
        scores.append(scoring.score_asset(snapshot, asset))
        if snapshot.market_state and snapshot.market_state != "UNKNOWN":
            market_state = snapshot.market_state
        if snapshot.market_time and (data_asof is None or snapshot.market_time > data_asof):
            data_asof = snapshot.market_time

    generated_at = datetime.now(tz=timezone.utc)
    if market_state == "UNKNOWN":
        market_state = _infer_market_state(generated_at)

    goal = planner.goal_analysis(
        start_usd=cash_usd,
        target_idr=target_idr,
        usd_idr=rate,
        is_live_fx=is_live,
        horizons_years=horizons_years,
    )
    allocation = planner.suggest_allocation(cash_usd, scores, assets, tranches)

    return Report(
        generated_at=generated_at,
        scores=scores,
        goal=goal,
        allocation=allocation,
        errors=errors,
        market_state=market_state,
        data_asof=data_asof,
    )
