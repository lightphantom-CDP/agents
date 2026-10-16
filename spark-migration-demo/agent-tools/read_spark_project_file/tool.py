"""
Agent Studio Tool — read text files from the CAI project (Spark migration demo).

Tries project-relative paths first, then absolute paths. Use for .py, .yaml, .json, .md, .csv.

Env:
  CDSW_PROJECT — optional; defaults to csa-apac if unset (set on workflow/project)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

OUTPUT_KEY = "tool_output"

# Extend if your project slug differs
DEFAULT_PROJECT = "csa-apac"
SPARK_DEMO_ROOT = "spark-migration-demo"


class UserParameters(BaseModel):
    project_slug: str = Field(
        default="",
        description="CAI project slug, e.g. csa-apac (or set CDSW_PROJECT env)",
    )


class ToolParameters(BaseModel):
    file_path: str = Field(
        description=(
            "Project-relative path, e.g. spark-migration-demo/cde_jobs.yaml "
            "or jobs/spark3_events_etl/events_etl_spark3.py"
        ),
    )


def _project_root(slug: str) -> Path:
    name = slug or os.getenv("CDSW_PROJECT", DEFAULT_PROJECT).strip() or DEFAULT_PROJECT
    return Path(f"/home/cdsw/{name}")


def _resolve(project: Path, raw: str) -> Path | None:
    raw = raw.strip().lstrip("/")
    if not raw:
        return None
    candidates = [
        Path(raw) if raw.startswith("/home/cdsw/") else None,
        project / raw,
        project / SPARK_DEMO_ROOT / raw,
        project / SPARK_DEMO_ROOT / "jobs" / raw,
    ]
    for c in candidates:
        if c is None:
            continue
        if c.is_file():
            return c.resolve()
    return None


def _listdir(p: Path) -> list[str]:
    try:
        return sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())[:60]
    except OSError as exc:
        return [f"<cannot list: {exc}>"]


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    project = _project_root(config.project_slug)
    path = _resolve(project, args.file_path)
    if path is None:
        return {
            "error": "file_not_found",
            "requested": args.file_path,
            "project_root": str(project),
            "hint": f"Try spark-migration-demo/cde_jobs.yaml under {project}",
            "diagnostics": {
                "cwd": os.getcwd(),
                "whoami": os.getenv("USER") or os.getenv("LOGNAME") or "?",
                "cdsw_project_env": os.getenv("CDSW_PROJECT"),
                "listing_/home/cdsw": _listdir(Path("/home/cdsw")),
                "listing_project_root": _listdir(project),
                "listing_cwd": _listdir(Path(os.getcwd())),
            },
        }
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": "decode_error", "path": str(path)}
    except OSError as exc:
        return {"error": str(exc), "path": str(path)}

    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "content": text,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True)
    parser.add_argument("--tool-params", required=True)
    cli = parser.parse_args()
    cfg = UserParameters(**json.loads(cli.user_params))
    params = ToolParameters(**json.loads(cli.tool_params))
    out = run_tool(cfg, params)
    print(OUTPUT_KEY, json.dumps(out, indent=2, default=str))
