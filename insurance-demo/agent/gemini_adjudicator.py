#!/usr/bin/env python3
"""
Insurance claim review agent using Google Gemini API.

Phase 1 demo: LLM reasons over claim features + policy text.
Later: swap Gemini for a Cloudera AI Inference endpoint (Hugging Face model).

Usage:
  export GEMINI_API_KEY=your-key
  python3 agent/gemini_adjudicator.py --claim-id CLM-50021
  python3 agent/gemini_adjudicator.py --claim-id CLM-50005 --model gemini-3.1-pro-preview
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
POLICY_PATH = DATA_DIR / "policy" / "coverage_policy.md"

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

SYSTEM_PROMPT = """You are MediClaim Review Copilot for hospital insurance claims.

You receive:
1) Claim features from the governed gold table (claim_features_v1)
2) The insurer coverage policy document

Your job:
- Recommend: approved, partial_approval, rejected, or manual_review
- List the top 3 risk flags that drove the decision
- Cite specific policy sections by number/title
- Be concise and actionable for a human claims adjuster

Rules:
- Never approve without checking waiting period, prior auth, pre-existing, and coverage flags.
- If undisclosed_pre_existing_flag = 1, explain the pre-existing rule.
- If missing_prior_auth_flag = 1, cite prior authorization requirements.
- If experimental_not_covered_flag = 1, cite experimental treatment exclusion.
- If unsure, recommend manual_review and say what a human should verify.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review a claim with Gemini API")
    parser.add_argument("--claim-id", required=True, help="e.g. CLM-50021")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--api-key",
        default=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
    )
    return parser.parse_args()


def load_claim_features(claim_id: str) -> dict:
    """Load one claim row from local CSVs (mirrors gold table fields)."""
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    row = claims[claims["claim_id"] == claim_id]
    if row.empty:
        raise ValueError(f"Claim not found: {claim_id}")

    diagnoses = pd.read_csv(DATA_DIR / "claim_diagnoses.csv")
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    members = pd.read_csv(DATA_DIR / "members.csv")

    claim = row.iloc[0].to_dict()
    policy_id = claim["policy_id"]
    member_id = claim["member_id"]

    dx = diagnoses[(diagnoses["claim_id"] == claim_id) & (diagnoses["is_primary"] == 1)]
    pol = policies[policies["policy_id"] == policy_id]
    mem = members[members["member_id"] == member_id]

    features = {
        "claim_id": claim_id,
        "member_id": member_id,
        "policy_id": policy_id,
        "admission_type": claim.get("admission_type"),
        "length_of_stay_days": int(claim.get("length_of_stay_days", 0)),
        "total_billed_amount": float(claim.get("total_billed_amount", 0)),
        "has_experimental_treatment": int(claim.get("has_experimental_treatment", 0)),
        "days_since_coverage_start": int(claim.get("days_since_coverage_start", 0)),
        "undisclosed_pre_existing_flag": int(claim.get("undisclosed_pre_existing_flag", 0)),
        "prior_auth_number": claim.get("prior_auth_number") or "",
        "has_prior_auth": 1 if claim.get("prior_auth_number") else 0,
        "claim_outcome_actual": claim.get("claim_outcome"),
        "approved_amount_actual": float(claim.get("approved_amount", 0)),
        "denial_reasons_actual": claim.get("denial_reasons") or "",
    }

    if not dx.empty:
        d = dx.iloc[0]
        features.update(
            {
                "icd10_code": d["icd10_code"],
                "diagnosis_description": d["diagnosis_description"],
                "diagnosis_category": d["diagnosis_category"],
                "is_chronic_related": int(d["is_chronic_related"]),
            }
        )

    if not pol.empty:
        p = pol.iloc[0]
        features.update(
            {
                "plan_type": p["plan_type"],
                "annual_coverage_limit": float(p["annual_coverage_limit"]),
                "waiting_period_days": int(p["waiting_period_days"]),
                "pre_auth_threshold": float(p["pre_auth_threshold"]),
                "maternity_covered": int(p["maternity_covered"]),
                "mental_health_covered": int(p["mental_health_covered"]),
                "experimental_treatment_covered": int(p["experimental_treatment_covered"]),
                "policy_status": p["policy_status"],
            }
        )
        features["waiting_period_violation"] = int(
            features["days_since_coverage_start"] < features["waiting_period_days"]
        )
        features["missing_prior_auth_flag"] = int(
            features["total_billed_amount"] > features["pre_auth_threshold"]
            and features["has_prior_auth"] == 0
        )
        features["experimental_not_covered_flag"] = int(
            features["has_experimental_treatment"] == 1
            and features["experimental_treatment_covered"] == 0
        )
        features["policy_inactive_flag"] = int(features.get("policy_status") != "active")

    if not mem.empty:
        m = mem.iloc[0]
        features.update(
            {
                "age": int(m["age"]),
                "smoker_flag": int(m["smoker_flag"]),
                "bmi_category": m["bmi_category"],
            }
        )

    return features


def call_gemini(api_key: str, model: str, claim_features: dict, policy_text: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise SystemExit(
            "Install Gemini SDK: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_PROMPT,
    )

    user_prompt = f"""Review this hospital insurance claim.

## Claim features (from claim_features_v1)
```json
{json.dumps(claim_features, indent=2)}
```

## Coverage policy
{policy_text}

Respond in this structure:
1. Recommended outcome (approved / partial_approval / rejected / manual_review)
2. Confidence (low / medium / high) and brief rationale
3. Top 3 risk flags
4. Policy citations (section numbers)
5. Suggested next action for the adjuster

Note: claim_outcome_actual is the historical label in training data — use it only to sanity-check your reasoning, not as the answer.
"""
    response = client.generate_content(user_prompt)
    return response.text


def main() -> None:
    args = parse_args()
    if not args.api_key:
        raise SystemExit("Set GEMINI_API_KEY or pass --api-key")

    claim_features = load_claim_features(args.claim_id)
    policy_text = POLICY_PATH.read_text(encoding="utf-8")

    print(f"Model: {args.model}")
    print(f"Claim: {args.claim_id}\n")
    print("=" * 60)
    print(call_gemini(args.api_key, args.model, claim_features, policy_text))
    print("=" * 60)


if __name__ == "__main__":
    main()
