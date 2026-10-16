"""
Agent Studio Tool — read spark-migration-demo files via CAI Application HTTP API.

Use when catalog file read fails (bwrap Permission denied). The CAI app runs in the
project pod with normal filesystem access; this tool only performs HTTP GET.

Env (workflow / project):
  SPARK_FILE_READER_URL — base URL of running spark-file-reader CAI Application
    e.g. https://<workbench>/.../spark-file-reader/
  CDSW_API_KEY — optional, if app requires auth in your environment
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from pydantic import BaseModel, Field

OUTPUT_KEY = "tool_output"


class UserParameters(BaseModel):
    base_url: str = Field(
        default="",
        description="CAI app base URL (or SPARK_FILE_READER_URL env)",
    )


class ToolParameters(BaseModel):
    file_path: str = Field(
        description="e.g. spark-migration-demo/cde_jobs.yaml or cde_jobs.yaml",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    base = (config.base_url or os.getenv("SPARK_FILE_READER_URL", "")).strip().rstrip("/")
    if not base:
        return {
            "error": "Set SPARK_FILE_READER_URL to your running spark-file-reader app URL",
        }

    url = f"{base}/read"
    headers: dict[str, str] = {}
    api_key = os.getenv("CDSW_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(
            url,
            params={"path": args.file_path.strip()},
            headers=headers,
            timeout=60,
        )
        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {"error": body.get("error") or resp.text, "status": resp.status_code}
        return body
    except requests.RequestException as exc:
        return {"error": f"HTTP request failed: {exc}", "url": url}


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
