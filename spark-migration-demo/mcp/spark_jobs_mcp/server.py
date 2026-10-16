#!/usr/bin/env python3
"""
MCP server — read Spark migration demo files from CAI project (stdio).

Allowed root: SPARK_JOBS_ROOT (default /home/cdsw/csa-apac/spark-migration-demo)

Tools:
  read_job_file(relative_path) — read .py, .yaml, .json, .md, .txt, .csv
  list_spark_job_files(subpath) — list files under subpath (default "")

Agent Studio: register MCP server with command python + this script (see DEPLOY-MCP-SPARK-READ.md).
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DEFAULT_PROJECT = "csa-apac"
DEFAULT_ROOT_NAME = "spark-migration-demo"
ALLOWED_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".txt", ".csv"}

mcp = FastMCP(
    "spark-jobs-filesystem",
    instructions=(
        "Read Spark batch job sources for CDE migration demo. "
        "Start with cde_jobs.yaml, then job meta and .py paths from that file."
    ),
)


def jobs_root() -> Path:
    env = os.getenv("SPARK_JOBS_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    slug = os.getenv("CDSW_PROJECT", DEFAULT_PROJECT).strip() or DEFAULT_PROJECT
    return (Path(f"/home/cdsw/{slug}") / DEFAULT_ROOT_NAME).resolve()


def resolve_relative(relative: str) -> Path:
    raw = (relative or "").strip().replace("\\", "/").lstrip("/")
    if not raw or ".." in raw.split("/"):
        raise ValueError("Invalid path: use paths under spark-migration-demo without ..")
    root = jobs_root()
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path must stay under {root}") from exc
    if not target.is_file():
        raise FileNotFoundError(f"Not a file: {target}")
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"Suffix not allowed: {target.suffix}")
    return target


@mcp.tool()
def read_job_file(relative_path: str) -> str:
    """Read a text job file relative to spark-migration-demo root.

    Examples:
      cde_jobs.yaml
      jobs/spark3_events_etl/events_etl_spark3.py
      jobs/spark3_events_etl/job.meta.yaml
    """
    path = resolve_relative(relative_path)
    return path.read_text(encoding="utf-8")


@mcp.tool()
def list_spark_job_files(subpath: str = "") -> str:
    """List allowed files under subpath (relative to spark-migration-demo)."""
    root = jobs_root()
    sub = (subpath or "").strip().replace("\\", "/").lstrip("/")
    if ".." in sub.split("/"):
        raise ValueError("Invalid subpath")
    base = (root / sub).resolve() if sub else root
    try:
        base.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Subpath must stay under {root}") from exc
    if not base.is_dir():
        raise NotADirectoryError(str(base))
    lines: list[str] = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES:
            lines.append(str(p.relative_to(root)))
    return "\n".join(lines) if lines else "(no matching files)"


@mcp.tool()
def spark_jobs_root_info() -> str:
    """Return configured jobs root path and whether it exists."""
    root = jobs_root()
    return (
        f"SPARK_JOBS_ROOT={root}\n"
        f"exists={root.is_dir()}\n"
        f"CDE registry file exists={(root / 'cde_jobs.yaml').is_file()}"
    )


if __name__ == "__main__":
    mcp.run()
