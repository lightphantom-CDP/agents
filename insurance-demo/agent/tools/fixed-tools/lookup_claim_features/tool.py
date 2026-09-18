"""
Agent Studio Tool 1 — lookup claim features from governed gold table.

Preferred path: Trino HTTP (trino-python-client) — same data as Hue.
Fallbacks: Spark (if enabled), Parquet, demo_claims.json (workshop only).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

OUTPUT_KEY = "tool_output"
CLAIM_ID_RE = re.compile(r"^CLM-\d{5}$", re.IGNORECASE)

FEATURE_COLUMNS = [
    "claim_id",
    "member_id",
    "policy_id",
    "icd10_code",
    "diagnosis_category",
    "is_chronic_related",
    "admission_type",
    "length_of_stay_days",
    "total_billed_amount",
    "procedure_total",
    "experimental_bill_amount",
    "surgery_amount",
    "plan_type",
    "annual_coverage_limit",
    "deductible_used_ytd",
    "waiting_period_days",
    "pre_auth_threshold",
    "maternity_covered",
    "mental_health_covered",
    "experimental_treatment_covered",
    "policy_status",
    "has_prior_auth",
    "has_experimental_treatment",
    "days_since_coverage_start",
    "undisclosed_pre_existing_flag",
    "undisclosed_pre_existing_count",
    "waiting_period_violation",
    "missing_prior_auth_flag",
    "experimental_not_covered_flag",
    "maternity_not_covered_flag",
    "mental_health_not_covered_flag",
    "policy_inactive_flag",
    "procedures_requiring_auth",
    "age",
    "smoker_flag",
    "bmi_category",
    "denial_reasons",
]


class UserParameters(BaseModel):
    gold_table: str = Field(
        default="hive.insurance_leo_trino.claim_features_v1",
        description="Full table: catalog.schema.table",
    )
    gold_parquet_path: str = Field(
        default="insurance_demo_warehouse/claim_features_v1",
        description="Fallback Parquet folder",
    )
    trino_host: str = Field(
        default="",
        description="Trino coordinator host (no https://). Ask admin or see DEPLOY-TRINO-AGENT.md",
    )
    trino_port: int = Field(default=443)
    trino_user: str = Field(
        default="",
        description="CDP username (e.g. leonard). Empty = HADOOP_USER_NAME from CAI session.",
    )
    trino_password: str = Field(
        default="",
        description="Optional. Prefer WORKLOAD_PASSWORD env (CAI User Settings).",
    )
    trino_jwt: str = Field(
        default="",
        description="Knox JWT from CDW Token Generator. /tmp/jwt does NOT work for Trino.",
    )
    trino_catalog: str = Field(default="hive")
    trino_schema: str = Field(default="insurance_leo_trino")
    trino_http_scheme: str = Field(default="https")
    use_demo_fallback: bool = Field(
        default=False,
        description="If true, use demo_claims.json when Trino fails. Keep false for production.",
    )

    @field_validator("trino_port", mode="before")
    @classmethod
    def coerce_trino_port(cls, value: Any) -> int:
        if value in (None, ""):
            return 443
        return int(value)

    @field_validator("use_demo_fallback", mode="before")
    @classmethod
    def coerce_use_demo_fallback(cls, value: Any) -> bool:
        if value in (None, ""):
            return False
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    @field_validator(
        "gold_table",
        "gold_parquet_path",
        "trino_host",
        "trino_user",
        "trino_password",
        "trino_jwt",
        "trino_catalog",
        "trino_schema",
        "trino_http_scheme",
        mode="before",
    )
    @classmethod
    def empty_str_to_default(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str) and not value.strip():
            return ""
        return value


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Hospital claim ID, e.g. CLM-50021")


def tool_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        pass
    project = os.environ.get("CDSW_PROJECT", "").strip()
    candidates = [
        Path("/tool"),
        Path.cwd(),
        Path.cwd() / "lookup_claim_features",
    ]
    if project:
        candidates.append(Path(f"/home/cdsw/{project}/agent/tools/lookup_claim_features"))
    for path in candidates:
        if path.is_dir():
            return path
    return Path("/tool")


def project_root() -> Path:
    return Path("/home/cdsw")


def workflow_data_root() -> Path:
    explicit = os.environ.get("WORKFLOW_DATA_DIRECTORY", "").strip()
    return Path(explicit) if explicit else project_root()


def normalize_claim_id(raw: str) -> str:
    claim_id = raw.strip().upper()
    if not CLAIM_ID_RE.match(claim_id):
        raise ValueError(f"Invalid claim_id format: {raw!r} (expected CLM-50021)")
    return claim_id


def resolve_table(config: UserParameters) -> str:
    table = (config.gold_table or "").strip()
    if table.count(".") >= 2:
        return table
    name = table or "claim_features_v1"
    if "." in name:
        return f"{config.trino_catalog}.{name}"
    return f"{config.trino_catalog}.{config.trino_schema}.{name}"


def trino_connection_settings(config: UserParameters) -> dict[str, Any] | None:
    jdbc = os.getenv("TRINO_JDBC_URL", "").strip()
    host = (config.trino_host or os.getenv("TRINO_HOST", "")).strip()

    if jdbc:
        parsed = urlparse(jdbc.replace("jdbc:trino://", "trino://"))
        host = parsed.hostname or host
        port = parsed.port or config.trino_port
        scheme = parsed.scheme if parsed.scheme in ("http", "https") else config.trino_http_scheme
        path = (parsed.path or "").strip("/")
        parts = path.split("/") if path else []
        catalog = parts[0] if len(parts) > 0 else config.trino_catalog
        schema = parts[1] if len(parts) > 1 else config.trino_schema
        return {
            "host": host,
            "port": port,
            "http_scheme": scheme,
            "catalog": catalog,
            "schema": schema,
        }

    if not host:
        return None

    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    return {
        "host": host,
        "port": int(os.getenv("TRINO_PORT", str(config.trino_port))),
        "http_scheme": os.getenv("TRINO_HTTP_SCHEME", config.trino_http_scheme),
        "catalog": config.trino_catalog,
        "schema": config.trino_schema,
    }


def resolve_trino_user(config: UserParameters) -> str:
    return (
        (config.trino_user or "").strip()
        or os.getenv("HADOOP_USER_NAME", "").strip()
        or os.getenv("TRINO_USER", "").strip()
        or "cdsw"
    )


def resolve_trino_jwt(config: UserParameters) -> str:
    return (config.trino_jwt or os.getenv("TRINO_JWT", "")).strip()


def configure_no_proxy_for_host(host: str) -> None:
    host = host.split("/")[0]
    existing = os.environ.get("NO_PROXY", "")
    if host in existing:
        return
    os.environ["NO_PROXY"] = f"{existing},{host}" if existing else host
    os.environ["no_proxy"] = os.environ["NO_PROXY"]


def resolve_trino_auth(config: UserParameters, user: str) -> Any:
    try:
        from trino.auth import BasicAuthentication, JWTAuthentication
    except ImportError as exc:
        raise ImportError(f"trino package not installed: {exc}") from exc

    jwt = resolve_trino_jwt(config)
    if jwt:
        return JWTAuthentication(jwt)

    password = (
        config.trino_password
        or os.getenv("WORKLOAD_PASSWORD", "")
        or os.getenv("TRINO_PASSWORD", "")
    )
    if password:
        return BasicAuthentication(user, password)
    return None


def load_via_trino(config: UserParameters, claim_id: str) -> tuple[dict[str, Any] | None, str | None]:
    settings = trino_connection_settings(config)
    if not settings:
        return None, "Trino not configured (set trino_host or TRINO_HOST)"

    try:
        import trino.dbapi

        user = resolve_trino_user(config)
        auth = resolve_trino_auth(config, user)
        if not auth:
            return None, (
                "Trino auth not configured. Set WORKLOAD_PASSWORD in CAI User Settings "
                "(and matching workload password in CDP Profile), or paste a Knox JWT in trino_jwt."
            )
        configure_no_proxy_for_host(settings["host"])
    except ImportError as exc:
        return None, str(exc)

    try:
        conn = trino.dbapi.connect(
            host=settings["host"],
            port=settings["port"],
            user=user,
            auth=auth,
            catalog=settings["catalog"],
            schema=settings["schema"],
            http_scheme=settings["http_scheme"],
        )
        table = resolve_table(config)
        cols = ", ".join(FEATURE_COLUMNS)
        query = f"SELECT {cols} FROM {table} WHERE claim_id = '{claim_id}' LIMIT 1"
        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        if not row:
            return None, f"Trino OK but no row for claim_id={claim_id} in {table}"
        return dict(zip(FEATURE_COLUMNS, row)), None
    except Exception as exc:
        return None, f"Trino error ({settings['host']}:{settings['port']}): {exc}"


def demo_json_candidates() -> list[Path]:
    return [
        tool_dir() / "demo_claims.json",
        Path("/tool/demo_claims.json"),
        project_root() / "demo_claims.json",
    ]


def load_via_demo_json(claim_id: str) -> dict[str, Any] | None:
    for path in demo_json_candidates():
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            if row.get("claim_id") == claim_id:
                return {k: row.get(k) for k in FEATURE_COLUMNS if k in row}
    return None


def load_via_spark(table: str, claim_id: str) -> pd.DataFrame | None:
    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        query = f"""
            SELECT {", ".join(FEATURE_COLUMNS)}
            FROM {table}
            WHERE claim_id = '{claim_id}'
            LIMIT 1
        """
        return spark.sql(query).toPandas()
    except Exception:
        return None


def parquet_candidates(config: UserParameters) -> list[Path]:
    name = config.gold_parquet_path
    paths = [workflow_data_root() / name, project_root() / name, tool_dir() / name]
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def load_via_parquet(config: UserParameters, claim_id: str) -> pd.DataFrame | None:
    try:
        import pandas as pd
    except ImportError:
        return None
    for path in parquet_candidates(config):
        if not path.exists():
            continue
        gold = pd.read_parquet(path)
        df = gold.loc[gold["claim_id"] == claim_id, FEATURE_COLUMNS]
        if not df.empty:
            return df
    return None


def row_to_dict(row: pd.Series) -> dict[str, Any]:
    import pandas as pd

    out: dict[str, Any] = {}
    for col in FEATURE_COLUMNS:
        if col not in row.index:
            continue
        val = row[col]
        if pd.isna(val):
            out[col] = None
        elif hasattr(val, "item"):
            out[col] = val.item()
        else:
            out[col] = val
    return out


def _flag(row: dict[str, Any], name: str) -> int:
    val = row.get(name)
    if val is None:
        return 0
    return int(val)


def compute_suggested_outcome(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    # Hard rejects — policy void regardless of anything else.
    if _flag(row, "policy_inactive_flag"):
        return "rejected", ["policy_inactive_flag"]
    if _flag(row, "waiting_period_violation"):
        return "rejected", ["waiting_period_violation"]

    # Clinical review flag (from denial_reasons) forces human manual review.
    denial_reasons = str(row.get("denial_reasons") or "").lower()
    if "requires_clinical_review" in denial_reasons or _flag(row, "requires_clinical_review_flag"):
        return "manual_review", ["requires_clinical_review"]

    if _flag(row, "undisclosed_pre_existing_flag"):
        reasons.append("undisclosed_pre_existing_flag")
    if _flag(row, "experimental_not_covered_flag"):
        reasons.append("experimental_not_covered_flag")
    if _flag(row, "missing_prior_auth_flag"):
        reasons.append("missing_prior_auth_flag")
    if _flag(row, "maternity_not_covered_flag"):
        reasons.append("maternity_not_covered_flag")
    if _flag(row, "mental_health_not_covered_flag"):
        reasons.append("mental_health_not_covered_flag")
    if "undisclosed_pre_existing_flag" in reasons:
        return "rejected", reasons
    if len(reasons) >= 2:
        return "rejected", reasons
    if len(reasons) == 1:
        return "partial_approval", reasons
    return "approved", []


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    outcome, reasons = compute_suggested_outcome(row)
    row["suggested_outcome"] = outcome
    row["suggested_outcome_reasons"] = reasons
    row["agent_instruction"] = (
        f"Use suggested_outcome={outcome}. Ground all facts in this JSON only."
    )
    return row


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    try:
        claim_id = normalize_claim_id(args.claim_id)
    except ValueError as exc:
        return {"error": str(exc)}

    errors: list[str] = []

    # 1) Trino first (governed gold table — same as Hue)
    row, trino_err = load_via_trino(config, claim_id)
    if row:
        row["data_source"] = "trino"
        return enrich_row(row)
    if trino_err:
        errors.append(trino_err)

    # 2) Spark (if workload has Spark + hive access)
    df = load_via_spark(config.gold_table, claim_id)
    if df is not None and not df.empty:
        out = enrich_row(row_to_dict(df.iloc[0]))
        out["data_source"] = "spark"
        return out
    errors.append(f"spark:{config.gold_table}")

    # 3) Parquet export (optional)
    df = load_via_parquet(config, claim_id)
    if df is not None and not df.empty:
        out = enrich_row(row_to_dict(df.iloc[0]))
        out["data_source"] = "parquet"
        return out
    errors.append("parquet")

    # 4) Workshop demo file only if explicitly allowed
    if config.use_demo_fallback:
        row = load_via_demo_json(claim_id)
        if row:
            row["data_source"] = "demo_claims.json"
            return enrich_row(row)
        errors.append("demo_claims.json")
    else:
        errors.append("demo_claims.json skipped (use_demo_fallback=false)")

    settings = trino_connection_settings(config)
    return {
        "error": f"Claim not found: {claim_id}",
        "hint": (
            "Configure trino_host in tool settings. Hue URL is NOT the Trino host — "
            "ask your admin for the Trino coordinator hostname."
        ),
        "trino_configured": bool(settings),
        "trino_target": settings,
        "gold_table": resolve_table(config),
        "errors": errors,
    }


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
