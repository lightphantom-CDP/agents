"""
Lab 6 workaround — score applicants in CAI (no Spark, no HTTP API).

Prerequisites:
  - /home/cdsw/model_files from export_model.py
  - Features parquet on S3 (from earlier export or 04_export_features.py)

Usage in CAI session:
  1. hadoop fs -get s3a://<bucket>/.../features /home/cdsw/features_parquet
  2. python score_in_cai.py --features-parquet /home/cdsw/features_parquet
  3. hadoop fs -put /home/cdsw/scores_out.parquet s3a://<bucket>/.../scores_out.parquet
  4. Run CDE job 04_load_scores.py
"""

import argparse
from datetime import datetime
from pathlib import Path

import mlflow
import pandas as pd

FEATURE_COLS = [
    "utilization",
    "age",
    "debt_ratio",
    "delinq_total",
    "open_credit_lines",
    "real_estate_loans",
    "dependents",
    "income_missing",
    "monthly_income",
    "high_utilization_flag",
]


def risk_band(probability: float) -> str:
    if probability < 0.10:
        return "A"
    if probability < 0.20:
        return "B"
    if probability < 0.35:
        return "C"
    return "D"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-parquet", default="/home/cdsw/features_parquet")
    parser.add_argument("--model-path", default="/home/cdsw/model_files")
    parser.add_argument("--output", default="/home/cdsw/scores_out.parquet")
    parser.add_argument("--model-name", default="xgboost1")
    parser.add_argument("--model-version", default="1")
    return parser.parse_args()


def main():
    args = parse_args()
    model = mlflow.sklearn.load_model(args.model_path)
    pdf = pd.read_parquet(args.features_parquet)
    print(f"Loaded {len(pdf)} rows from {args.features_parquet}")

    proba = model.predict_proba(pdf[FEATURE_COLS].fillna(0))[:, 1]
    out = pdf[["applicant_id"]].copy()
    out["probability_default"] = proba
    out["risk_band"] = out["probability_default"].map(risk_band)
    out["model_name"] = args.model_name
    out["model_version"] = args.model_version
    out["scored_at"] = datetime.utcnow().isoformat()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output, index=False)
    print(f"SUCCESS: scored {len(out)} rows -> {output}")


if __name__ == "__main__":
    main()
