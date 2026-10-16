"""
Agent Studio Tool — read a Spark job file from GitHub (Contents API).

Agent Studio runs tools in an isolated /workspace sandbox with NO CAI project
filesystem mounted, so filesystem reads cannot see project files. This tool reads
over the network instead — the same proven path push_spark_job_to_github uses.

GitHub is the source of truth: the agent reads cde_jobs.yaml, the job source_file
and meta_file from the repo, reviews/converts, then pushes back with
push_spark_job_to_github. A linked CDE Repository syncs the same branch.

Env (project or workflow):
  GITHUB_TOKEN          — PAT/fine-grained token with contents:read (optional for public repos)
  GITHUB_REPO           — owner/repo, e.g. my-org/spark-migration-demo
  GITHUB_DEFAULT_BRANCH — default main
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests
from pydantic import BaseModel, Field, field_validator

OUTPUT_KEY = "tool_output"
API = "https://api.github.com"


class UserParameters(BaseModel):
    github_repo: str = Field(
        default="",
        description="owner/repo (or set GITHUB_REPO env var)",
    )
    default_branch: str = Field(
        default="main",
        description="Branch/ref to read from (or GITHUB_DEFAULT_BRANCH)",
    )


class ToolParameters(BaseModel):
    file_path: str = Field(
        description=(
            "Path in the GitHub repo, e.g. spark-migration-demo/cde_jobs.yaml "
            "or jobs/spark3_events_etl/events_etl_spark3.py"
        ),
    )
    ref: str = Field(
        default="",
        description="Override branch/tag/sha; empty uses default_branch",
    )

    @field_validator("file_path", mode="before")
    @classmethod
    def strip_path(cls, value: Any) -> str:
        return str(value or "").strip().lstrip("/")


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    repo_full = (config.github_repo or os.getenv("GITHUB_REPO", "")).strip()
    if "/" not in repo_full:
        return {
            "error": "Set github_repo user param or GITHUB_REPO=owner/repo",
        }
    owner, repo = repo_full.split("/", 1)

    ref = (
        args.ref
        or config.default_branch
        or os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    ).strip()
    path = args.file_path
    if not path:
        return {"error": "file_path is required (repo-relative path)."}

    url = f"{API}/repos/{owner}/{repo}/contents/{path}"
    try:
        resp = requests.get(url, headers=_headers(), params={"ref": ref}, timeout=60)
    except requests.RequestException as exc:
        return {"error": f"GitHub request failed: {exc}", "url": url}

    if resp.status_code == 404:
        return {
            "error": "file_not_found",
            "repo": repo_full,
            "ref": ref,
            "requested": path,
            "hint": "Check path is relative to repo root and the ref/branch is correct.",
        }
    if resp.status_code >= 400:
        return {
            "error": f"GitHub API {resp.status_code}: {resp.text[:500]}",
            "repo": repo_full,
            "ref": ref,
            "requested": path,
        }

    body = resp.json()
    if isinstance(body, list):
        return {
            "error": "path_is_directory",
            "requested": path,
            "entries": [e.get("name") for e in body][:100],
        }

    encoding = body.get("encoding")
    raw = body.get("content", "")
    if encoding == "base64":
        try:
            text = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            return {"error": f"decode_error: {exc}", "path": path}
    else:
        text = raw

    return {
        "repo": repo_full,
        "ref": ref,
        "path": path,
        "size_bytes": body.get("size"),
        "sha": body.get("sha"),
        "html_url": body.get("html_url"),
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
