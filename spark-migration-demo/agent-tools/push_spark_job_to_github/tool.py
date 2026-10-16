"""
Agent Studio Tool — push or update a Spark job file on GitHub (Contents API).

Use after Spark 3 → 4 conversion and explicit user approval.
CDE can then run the job from a linked CDE Repository on the same branch.

Env (project or workflow):
  GITHUB_TOKEN          — PAT or fine-grained token with contents:write
  GITHUB_REPO           — owner/repo, e.g. my-org/spark-migration-demo
  GITHUB_DEFAULT_BRANCH — default main
  GITHUB_PUSH_ENABLED   — must be "true" or tool refuses (safety)
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
        description="Branch to commit to (or GITHUB_DEFAULT_BRANCH)",
    )


class ToolParameters(BaseModel):
    repo_path: str = Field(
        description="Path in GitHub repo, e.g. jobs/spark4_events_etl/events_etl_spark4.py",
    )
    file_content: str = Field(description="Full file text to commit")
    commit_message: str = Field(
        default="chore(spark): agent Spark 4 conversion",
        description="Git commit message",
    )
    branch: str = Field(
        default="",
        description="Override branch; empty uses default_branch",
    )
    user_confirmed: bool = Field(
        default=False,
        description="Must be true after user explicitly approves push to GitHub",
    )

    @field_validator("repo_path", mode="before")
    @classmethod
    def strip_path(cls, value: Any) -> str:
        return str(value or "").strip().lstrip("/")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _push_enabled() -> bool:
    return os.getenv("GITHUB_PUSH_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _get_file_sha(owner: str, repo: str, path: str, branch: str, token: str) -> str | None:
    url = f"{API}/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(
        url, headers=_headers(token), params={"ref": branch}, timeout=60
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    body = resp.json()
    return body.get("sha")


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    if not args.user_confirmed:
        return {
            "error": "Push blocked: user_confirmed must be true after explicit user approval.",
            "pushed": False,
        }

    if not _push_enabled():
        return {
            "error": "Push blocked: set GITHUB_PUSH_ENABLED=true on workflow/project env.",
            "pushed": False,
        }

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return {"error": "Missing GITHUB_TOKEN env var.", "pushed": False}

    repo_full = (config.github_repo or os.getenv("GITHUB_REPO", "")).strip()
    if "/" not in repo_full:
        return {
            "error": "Set github_repo user param or GITHUB_REPO=owner/repo",
            "pushed": False,
        }
    owner, repo = repo_full.split("/", 1)

    branch = (args.branch or config.default_branch or os.getenv("GITHUB_DEFAULT_BRANCH", "main")).strip()
    path = args.repo_path
    message = (args.commit_message or "Agent Studio Spark job update").strip()

    try:
        sha = _get_file_sha(owner, repo, path, branch, token)
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(args.file_content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        url = f"{API}/repos/{owner}/{repo}/contents/{path}"
        resp = requests.put(url, headers=_headers(token), json=payload, timeout=120)
        if resp.status_code >= 400:
            return {
                "error": f"GitHub API {resp.status_code}: {resp.text[:500]}",
                "pushed": False,
            }
        body = resp.json()
        commit = body.get("commit") or {}
        return {
            "pushed": True,
            "repo": repo_full,
            "branch": branch,
            "path": path,
            "commit_sha": commit.get("sha"),
            "html_url": body.get("content", {}).get("html_url"),
            "next_step": "Run CDE job linked to this repo path on Spark 4 VC.",
        }
    except requests.RequestException as exc:
        return {"error": f"GitHub request failed: {exc}", "pushed": False}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True)
    parser.add_argument("--tool-params", required=True)
    cli_args = parser.parse_args()

    user_config = UserParameters(**json.loads(cli_args.user_params))
    tool_args = ToolParameters(**json.loads(cli_args.tool_params))
    result = run_tool(user_config, tool_args)
    print(OUTPUT_KEY, json.dumps(result, indent=2, default=str))
