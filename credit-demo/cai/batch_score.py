#!/usr/bin/env python3
"""Batch score applicants and write a CSV ready for BI or agent tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
OUTPUT_DIR = ARTIFACT_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch score credit applicants")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", default=str(OUTPUT_DIR / "credit_scores_batch.csv"))
    return parser.parse_args()


def decision_tier(probability: float, thin_file: int) -> str:
    if probability <= 0.35:
        return "approve"
    if probability <= 0.55 and thin_file == 1:
        return "review"
    if probability <= 0.65:
        return "review"
    return "decline"


def main() -> None:
    args = parse_args()
    from train_and_register import build_local_gold_frame

    model = joblib.load(ARTIFACT_DIR / "credit_default_xgb_v1.joblib")
    feature_columns = json.loads((ARTIFACT_DIR / "credit_default_xgb_v1_features.json").read_text())
    frame = build_local_gold_frame().head(args.limit).copy()

    probabilities = model.predict_proba(frame[feature_columns])[:, 1]
    frame["default_probability"] = probabilities
    frame["decision_tier"] = [
        decision_tier(prob, int(thin))
        for prob, thin in zip(probabilities, frame["thin_file"])
    ]

    output_cols = [
        "application_id",
        "customer_id",
        "applied_at",
        "thin_file",
        "default_probability",
        "decision_tier",
        "monthly_income",
        "requested_loan_amount",
        "debt_to_income_ratio",
    ]
    output_path = Path(args.output)
    frame[output_cols].to_csv(output_path, index=False)
    print(f"Wrote {len(frame)} scored rows -> {output_path}")


if __name__ == "__main__":
    main()
