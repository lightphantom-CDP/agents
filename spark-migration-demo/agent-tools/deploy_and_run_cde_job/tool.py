"""
Agent Studio Tool — deploy a Spark job to Cloudera Data Engineering (CDE) and run it.

Uploads the (converted) Spark file straight into a CDE *files resource*, ensures a
CDE job exists that points at it, then triggers a run on the correct virtual cluster.
No GitHub repository sync is required — the agent pushes the code directly to CDE.

Verified call sequence (CDE dex/api/v1):
  1. POST   /resources                      create files resource (idempotent)
  2. PUT    /resources/<res>/<file>         upload the .py (overwrites)
  3. POST   /jobs                           create the spark job (idempotent)
  4. POST   /jobs/<job>/run                 run it  -> { "id": <runId> }
  5. GET    /job-runs/<id>                   (optional) status

Auth: CDE uses a Knox SSO JWT sent as a COOKIE "hadoop-jwt=<JWT>" (NOT a Bearer
header). Capture it from a logged-in CDE console session and set it as CDE_JWT.

Env (workflow / project):
  CDE_JWT                  — the hadoop-jwt JWT value (required)
  CDE_SPARK4_JOBS_API_URL  — e.g. https://hrk7m4cp.cde-l5r2jpql.sha-ccf-cde.a97996.test.cldr.work/dex/api/v1
  CDE_SPARK3_JOBS_API_URL  — e.g. https://c2l54mzt.cde-l5r2jpql.sha-ccf-cde.a97996.test.cldr.work/dex/api/v1
  CDE_RUN_ENABLED          — must be "true" or the tool refuses (safety)
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests
from pydantic import BaseModel, Field, field_validator

OUTPUT_KEY = "tool_output"


class UserParameters(BaseModel):
    spark4_jobs_api_url: str = Field(
        default="",
        description="CDE Jobs API URL for the Spark 4 VC (or CDE_SPARK4_JOBS_API_URL env)",
    )
    spark3_jobs_api_url: str = Field(
        default="",
        description="CDE Jobs API URL for the Spark 3 VC (or CDE_SPARK3_JOBS_API_URL env)",
    )
    resource_name: str = Field(
        default="spark-migration-demo-files",
        description="CDE files resource that holds the uploaded job code",
    )


class ToolParameters(BaseModel):
    job_name: str = Field(description="CDE job name, e.g. spark4-events-etl")
    file_name: str = Field(description="File name inside the resource, e.g. events_etl_spark4.py")
    file_content: str = Field(description="Full text of the Spark job file to deploy")
    spark_version: int = Field(default=4, description="4 -> Spark 4 VC, 3 -> Spark 3 VC")
    user_confirmed: bool = Field(
        default=False,
        description="Must be true after the user explicitly approves deploy+run on CDE",
    )
    poll: bool = Field(default=True, description="Poll run status a few times before returning")

    @field_validator("file_name", mode="before")
    @classmethod
    def strip_name(cls, value: Any) -> str:
        return str(value or "").strip().lstrip("/")


def _run_enabled() -> bool:
    return os.getenv("CDE_RUN_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _headers(jwt: str) -> dict[str, str]:
    return {"Cookie": f"hadoop-jwt={jwt}"}


def _base_url(cfg: UserParameters, version: int) -> str:
    if version == 3:
        return (cfg.spark3_jobs_api_url or os.getenv("CDE_SPARK3_JOBS_API_URL", "")).strip().rstrip("/")
    return (cfg.spark4_jobs_api_url or os.getenv("CDE_SPARK4_JOBS_API_URL", "")).strip().rstrip("/")


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    if not args.user_confirmed:
        return {"error": "Blocked: user_confirmed must be true after explicit user approval.", "ran": False}
    if not _run_enabled():
        return {"error": "Blocked: set CDE_RUN_ENABLED=true on workflow/project env.", "ran": False}

    jwt = os.getenv("CDE_JWT", "").strip()
    if not jwt:
        return {"error": "Missing CDE_JWT env var (hadoop-jwt token from a CDE console session).", "ran": False}

    base = _base_url(config, args.spark_version)
    if not base:
        return {"error": f"No Jobs API URL for Spark {args.spark_version}. Set CDE_SPARK{args.spark_version}_JOBS_API_URL.", "ran": False}

    res = config.resource_name.strip()
    job = args.job_name.strip()
    headers = _headers(jwt)
    steps: list[dict[str, Any]] = []

    try:
        # 1) create files resource (idempotent)
        r = requests.post(f"{base}/resources", headers={**headers, "Content-Type": "application/json"},
                          json={"name": res, "type": "files"}, timeout=60)
        steps.append({"create_resource": r.status_code})
        if r.status_code >= 400 and r.status_code not in (400, 409):
            return {"error": f"create_resource failed {r.status_code}: {r.text[:300]}", "ran": False, "steps": steps}

        # 2) upload the file (overwrites)
        files = {"file": (args.file_name, args.file_content.encode("utf-8"), "text/x-python")}
        r = requests.put(f"{base}/resources/{res}/{args.file_name}", headers=headers, files=files, timeout=120)
        steps.append({"upload_file": r.status_code})
        if r.status_code >= 400:
            return {"error": f"upload_file failed {r.status_code}: {r.text[:300]}", "ran": False, "steps": steps}

        # 3) create the job (idempotent)
        job_body = {
            "name": job,
            "type": "spark",
            "retentionPolicy": "keep_indefinitely",
            "mounts": [{"dirPrefix": "/", "resourceName": res}],
            "spark": {"file": args.file_name},
            "schedule": {"enabled": False},
        }
        r = requests.post(f"{base}/jobs", headers={**headers, "Content-Type": "application/json"},
                          json=job_body, timeout=60)
        steps.append({"create_job": r.status_code})
        if r.status_code >= 400 and r.status_code not in (400, 409):
            return {"error": f"create_job failed {r.status_code}: {r.text[:300]}", "ran": False, "steps": steps}

        # 4) run the job
        r = requests.post(f"{base}/jobs/{job}/run", headers={**headers, "Content-Type": "application/json"},
                          json={}, timeout=60)
        steps.append({"run_job": r.status_code})
        if r.status_code >= 400:
            return {"error": f"run_job failed {r.status_code}: {r.text[:300]}", "ran": False, "steps": steps}
        run_id = (r.json() or {}).get("id")

        result: dict[str, Any] = {
            "ran": True,
            "job": job,
            "resource": res,
            "spark_version": args.spark_version,
            "run_id": run_id,
            "jobs_api_url": base,
            "steps": steps,
            "next_step": "Fetch driver logs when status is succeeded; paste counts back for parity.",
        }

        # 5) optional status poll
        if args.poll and run_id is not None:
            import time
            for _ in range(6):
                time.sleep(5)
                s = requests.get(f"{base}/job-runs/{run_id}", headers=headers, timeout=30)
                if s.status_code < 400:
                    status = (s.json() or {}).get("status")
                    result["status"] = status
                    if status in ("succeeded", "failed", "killed", "finished", "error"):
                        break
        return result

    except requests.RequestException as exc:
        return {"error": f"CDE request failed: {exc}", "ran": False, "steps": steps}


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
