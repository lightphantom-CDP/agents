#!/usr/bin/env python3
"""
Train a claim review model locally or in Cloudera AI Workbench.

Local mode builds a gold-like frame from data/*.csv.
CAI mode reads the governed table: hive.insurance_leo_trino.claim_features_v1
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    from xgboost import XGBClassifier

    MODEL_BACKEND = "xgboost"
except Exception:
    from sklearn.ensemble import HistGradientBoostingClassifier

    MODEL_BACKEND = "sklearn_hist_gb"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

FEATURE_COLUMNS = [
    "is_chronic_related",
    "length_of_stay_days",
    "total_billed_amount",
    "procedure_total",
    "experimental_bill_amount",
    "surgery_amount",
    "annual_coverage_limit",
    "deductible_used_ytd",
    "waiting_period_days",
    "pre_auth_threshold",
    "maternity_covered",
    "mental_health_covered",
    "experimental_treatment_covered",
    "has_prior_auth",
    "has_experimental_treatment",
    "days_since_coverage_start",
    "undisclosed_pre_existing_flag",
    "undisclosed_pre_existing_count",
    "procedures_requiring_auth",
    "age",
    "smoker_flag",
    "waiting_period_violation",
    "missing_prior_auth_flag",
    "experimental_not_covered_flag",
    "maternity_not_covered_flag",
    "mental_health_not_covered_flag",
    "policy_inactive_flag",
]

LABEL_COLUMN = "claim_outcome"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train insurance claim review model")
    parser.add_argument("--mode", choices=["local", "cai"], default="local")
    parser.add_argument(
        "--source-table",
        default=os.getenv(
            "INSURANCE_GOLD_TABLE",
            "hive.insurance_leo_trino.claim_features_v1",
        ),
    )
    parser.add_argument("--model-name", default="claim_adjudication_xgb_v1")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def build_local_gold_frame() -> pd.DataFrame:
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    diagnoses = pd.read_csv(DATA_DIR / "claim_diagnoses.csv")
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    members = pd.read_csv(DATA_DIR / "members.csv")
    procedures = pd.read_csv(DATA_DIR / "claim_procedures.csv")
    bills = pd.read_csv(DATA_DIR / "hospital_bills.csv")
    history = pd.read_csv(DATA_DIR / "medical_history.csv")

    primary_dx = diagnoses[diagnoses["is_primary"] == 1].copy()
    proc_summary = (
        procedures.groupby("claim_id")
        .agg(
            procedure_total=("line_total", "sum"),
            procedures_requiring_auth=(
                "requires_prior_auth",
                lambda s: int((s == 1).sum()),
            ),
        )
        .reset_index()
    )
    bill_summary = bills.groupby("claim_id").apply(
        lambda g: pd.Series(
            {
                "experimental_bill_amount": float(
                    g.loc[g["is_experimental"] == 1, "amount"].sum()
                ),
                "surgery_amount": float(
                    g.loc[g["line_category"] == "surgery", "amount"].sum()
                ),
            }
        )
    ).reset_index()

    hist_summary = (
        history.groupby("member_id")
        .agg(
            undisclosed_pre_existing_count=(
                "is_pre_existing",
                lambda s: int(
                    ((history.loc[s.index, "is_pre_existing"] == 1)
                     & (history.loc[s.index, "disclosed_on_enrollment"] == 0)).sum()
                ),
            )
        )
        .reset_index()
    )

    frame = claims.merge(primary_dx, on="claim_id", how="left", suffixes=("", "_dx"))
    frame = frame.merge(policies, on="policy_id", how="left", suffixes=("", "_pol"))
    frame = frame.merge(members, on="member_id", how="left", suffixes=("", "_mem"))
    frame = frame.merge(proc_summary, on="claim_id", how="left")
    frame = frame.merge(bill_summary, on="claim_id", how="left")
    frame = frame.merge(hist_summary, on="member_id", how="left")

    frame["has_prior_auth"] = (
        frame["prior_auth_number"].notna() & (frame["prior_auth_number"].astype(str) != "")
    ).astype(int)
    frame["waiting_period_violation"] = (
        frame["days_since_coverage_start"] < frame["waiting_period_days"]
    ).astype(int)
    frame["missing_prior_auth_flag"] = (
        (frame["total_billed_amount"] > frame["pre_auth_threshold"])
        & (frame["has_prior_auth"] == 0)
    ).astype(int)
    frame["experimental_not_covered_flag"] = (
        (frame["has_experimental_treatment"] == 1)
        & (frame["experimental_treatment_covered"] == 0)
    ).astype(int)
    frame["maternity_not_covered_flag"] = (
        (frame["diagnosis_category"] == "maternity")
        & (frame["maternity_covered"] == 0)
    ).astype(int)
    frame["mental_health_not_covered_flag"] = (
        (frame["diagnosis_category"] == "mental_health")
        & (frame["mental_health_covered"] == 0)
    ).astype(int)
    frame["policy_inactive_flag"] = (frame["policy_status"] != "active").astype(int)

    return frame.fillna(0)


def load_training_frame(mode: str, source_table: str) -> pd.DataFrame:
    if mode == "local":
        return build_local_gold_frame()

    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("insurance_demo_train_load").getOrCreate()
        pdf = spark.table(source_table).toPandas()
        spark.stop()
        return pdf
    except Exception as exc:  # pragma: no cover - workshop fallback
        print(f"Could not read Spark table {source_table}: {exc}")
        print("Falling back to local CSV merge.")
        return build_local_gold_frame()


def build_model(num_classes: int, random_state: int):
    if MODEL_BACKEND == "xgboost":
        return XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=num_classes,
            eval_metric="mlogloss",
            random_state=random_state,
        )

    return HistGradientBoostingClassifier(
        max_iter=250,
        max_depth=5,
        learning_rate=0.08,
        random_state=random_state,
    )


def main() -> None:
    args = parse_args()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    frame = load_training_frame(args.mode, args.source_table)
    X = frame[FEATURE_COLUMNS].astype(float)
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(frame[LABEL_COLUMN].astype(str))

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=args.random_state,
        stratify=y,
    )

    num_classes = len(label_encoder.classes_)
    model = build_model(num_classes, args.random_state)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(y_test, predictions, average="macro")

    model_path = ARTIFACT_DIR / f"{args.model_name}.joblib"
    feature_path = ARTIFACT_DIR / f"{args.model_name}_features.json"
    label_path = ARTIFACT_DIR / f"{args.model_name}_labels.json"
    metrics_path = ARTIFACT_DIR / f"{args.model_name}_metrics.json"

    joblib.dump({"model": model, "label_encoder": label_encoder}, model_path)
    feature_path.write_text(json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8")
    label_path.write_text(
        json.dumps(label_encoder.classes_.tolist(), indent=2),
        encoding="utf-8",
    )
    metrics = {
        "model_name": args.model_name,
        "accuracy_holdout": round(float(accuracy), 4),
        "macro_f1_holdout": round(float(macro_f1), 4),
        "classes": label_encoder.classes_.tolist(),
        "feature_count": len(FEATURE_COLUMNS),
        "training_rows": int(len(X_train)),
        "model_backend": MODEL_BACKEND,
        "source_table": args.source_table if args.mode == "cai" else "local_csv",
    }
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(f"Saved model -> {model_path}")

    if args.mode == "cai":
        print(
            "\nNext in Cloudera AI:\n"
            "1. Log this run with MLflow / AI Registry.\n"
            "2. Register the joblib artifact as a model version.\n"
            "3. Promote to Inference service: claim-adjudication-xgb-v1.\n"
            "4. Wire Agent Studio tools (see agent/claims_adjudicator_design.md)."
        )


if __name__ == "__main__":
    main()
