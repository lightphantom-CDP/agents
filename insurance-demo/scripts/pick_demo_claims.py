#!/usr/bin/env python3
"""Print useful claim IDs for live insurance claim review demos."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load_claims() -> list[dict]:
    with (DATA_DIR / "claims.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_diagnoses() -> dict[str, dict]:
    with (DATA_DIR / "claim_diagnoses.csv").open(encoding="utf-8") as handle:
        return {row["claim_id"]: row for row in csv.DictReader(handle)}


def main() -> None:
    claims = load_claims()
    diagnoses = load_diagnoses()

    picks = {
        "fast_approve": next(c for c in claims if c["claim_outcome"] == "approved"),
        "clear_reject": next(c for c in claims if c["claim_outcome"] == "rejected"),
        "partial_approval": next(c for c in claims if c["claim_outcome"] == "partial_approval"),
        "manual_review": next(c for c in claims if c["claim_outcome"] == "manual_review"),
        "pre_existing_trap": next(
            c for c in claims if c["undisclosed_pre_existing_flag"] == "1"
        ),
        "missing_prior_auth": next(
            c for c in claims
            if "missing_prior_authorization" in c["denial_reasons"]
        ),
    }

    print("Suggested demo claims:\n")
    for label, claim in picks.items():
        diag = diagnoses.get(claim["claim_id"], {})
        print(
            f"- {label}: {claim['claim_id']} "
            f"(outcome={claim['claim_outcome']}, billed=${float(claim['total_billed_amount']):,.0f}, "
            f"dx={diag.get('icd10_code', 'n/a')} {diag.get('diagnosis_description', '')})"
        )
        if claim["denial_reasons"]:
            print(f"    reasons: {claim['denial_reasons']}")


if __name__ == "__main__":
    main()
