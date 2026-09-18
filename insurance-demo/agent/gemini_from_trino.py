#!/usr/bin/env python3
"""
Gemini claim review using Trino/Hive gold table (for CAI Workbench).

No local CSV needed — reads hive.insurance_leo_trino.claim_features_v1 via Spark.

Notebook usage:
    from agent.gemini_from_trino import review_claim_with_gemini
    print(review_claim_with_gemini("CLM-50021", api_key="...", model="gemini-3.1-pro-preview"))
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_TABLE = os.getenv(
    "INSURANCE_GOLD_TABLE",
    "hive.insurance_leo_trino.claim_features_v1",
)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

SYSTEM_PROMPT = """You are MediClaim Review Copilot for hospital insurance claims.

Recommend: approved, partial_approval, rejected, or manual_review.
List top 3 risk flags, cite policy sections, be concise for a claims adjuster.

Rules:
- Check waiting period, prior auth, pre-existing, coverage flags.
- If undisclosed_pre_existing_flag = 1, explain pre-existing rule.
- If missing_prior_auth_flag = 1, cite prior authorization requirements.
- If experimental_not_covered_flag = 1, cite experimental exclusion.
"""


def load_policy_text() -> str:
    """Try local file first; else use bundled minimal policy reference."""
    candidates = [
        Path("data/policy/coverage_policy.md"),
        Path("/home/cdsw/data/policy/coverage_policy.md"),
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")

    return """# MediShield Hospital Claims Policy (Demo excerpt)
- Waiting period must elapse before coverage applies.
- Prior authorization required when billed amount exceeds plan threshold.
- Undisclosed pre-existing conditions are grounds for rejection.
- Experimental treatments excluded unless plan covers them.
- Policy must be active.
Upload data/policy/coverage_policy.md to CAI for full policy text.
"""


def load_claim_from_trino(claim_id: str, table: str = DEFAULT_TABLE) -> dict:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    row = (
        spark.sql(
            f"""
            SELECT *
            FROM {table}
            WHERE claim_id = '{claim_id}'
            LIMIT 1
            """
        )
        .toPandas()
    )
    if row.empty:
        raise ValueError(f"Claim not found in {table}: {claim_id}")

    features = row.iloc[0].to_dict()
    # Spark/pandas may return numpy types — normalize for JSON
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in features.items()}


def review_claim_with_gemini(
    claim_id: str,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    table: str = DEFAULT_TABLE,
    policy_text: str | None = None,
) -> str:
    import google.generativeai as genai

    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Set GEMINI_API_KEY")

    features = load_claim_from_trino(claim_id, table=table)
    policy = policy_text or load_policy_text()

    genai.configure(api_key=key)
    client = genai.GenerativeModel(model_name=model, system_instruction=SYSTEM_PROMPT)

    prompt = f"""Review this hospital insurance claim.

## Claim features (from {table})
```json
{json.dumps(features, indent=2, default=str)}
```

## Coverage policy
{policy}

Respond with:
1. Recommended outcome
2. Confidence + rationale
3. Top 3 risk flags
4. Policy citations
5. Next action for adjuster
"""
    return client.generate_content(prompt).text
