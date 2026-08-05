"""MCP server exposing the investment scorer as tools for the course's agents.

This lets the LangGraph / OpenAI-Agents / AutoGen agents built earlier in the
course ask, in natural language, "is now a good price to add to NVDA?" and get a
structured, Buffett-flavoured answer.

Run it directly:

    uv run mcp_server.py

or wire it into an agent via stdio (see this folder's README for an example
``mcp_params`` entry). Requires the ``mcp`` package that ships with the course
environment; the rest of the scorer needs no third-party dependencies.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from investment_scorer.config import AppConfig, GoalConfig
from investment_scorer.data import get_series
from investment_scorer.goal import plan_goal
from investment_scorer.report import build_report
from investment_scorer.scoring import score_series

mcp = FastMCP("investment_scorer")


@mcp.tool()
async def score_ticker(symbol: str, name: str = "", demo: bool = False) -> dict:
    """Score whether now is a good price to add to a single stock/ETF.

    Args:
        symbol: Yahoo Finance ticker, e.g. "NVDA", "SPY", "AMZN", "META".
        name: Optional friendly name for the instrument.
        demo: If true, use deterministic offline data (no network).

    Returns a dict with a 0-100 buy score, a recommendation label, the four
    pillar sub-scores and a plain-English rationale.
    """
    series = get_series(symbol.upper(), name or symbol.upper(), demo=demo)
    return score_series(series).as_dict()


@mcp.tool()
async def score_portfolio(demo: bool = False) -> dict:
    """Score the full default portfolio (S&P 500 + NVDA + AMZN + META).

    Args:
        demo: If true, use deterministic offline data (no network).

    Returns the blended portfolio signal, per-holding scores and the "deploy
    cash now?" verdict for this hour.
    """
    cfg = AppConfig(demo=demo)
    results = [
        score_series(get_series(h.symbol, h.name, demo=demo)) for h in cfg.holdings
    ]
    plan = plan_goal(cfg.goal, demo=demo)
    return build_report(results, plan, cfg).to_json()


@mcp.tool()
async def investment_goal_plan(
    cash_usd: float = 4000.0,
    target_idr: float = 1_000_000_000.0,
    min_years: float = 3.0,
    max_years: float = 4.0,
    demo: bool = False,
) -> dict:
    """Assess a savings goal: required return and monthly contributions.

    Args:
        cash_usd: Starting cash in USD.
        target_idr: Target amount in Indonesian Rupiah.
        min_years / max_years: Time horizon range.
        demo: If true, skip the live FX lookup and use the fallback rate.

    Returns the USD target, the return the lump sum would need, and the monthly
    saving required under several return assumptions - plus a candid verdict.
    """
    goal = GoalConfig(
        starting_cash_usd=cash_usd,
        target_amount_idr=target_idr,
        min_years=min_years,
        max_years=max_years,
    )
    return plan_goal(goal, demo=demo).as_dict()


if __name__ == "__main__":
    mcp.run(transport="stdio")
