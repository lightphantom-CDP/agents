#!/usr/bin/env python3
"""
Train a credit default model locally or in Cloudera AI Workbench.

Local mode reads data/applications.csv and data/transactions.csv and writes artifacts to cai/artifacts/.
On Cloudera AI, point --source-table to the governed Iceberg gold table instead.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

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
    "age",
    "monthly_income",
    "requested_loan_amount",
    "tenure_months",
    "existing_loans",
    "credit_history_months",
    "thin_file",
    "utility_on_time_pct",
    "cash_flow_stability_score",
    "inquiry_count_90d",
    "debt_to_income_ratio",
    "device_trust_score",
    "prior_default_flag",
    "txn_count_90d",
    "merchant_category_diversity",
    "utility_payment_count",
    "international_txn_count",
    "avg_txn_amount",
    "net_cash_flow_90d",
    "income_to_spend_ratio",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train credit default model")
    parser.add_argument("--mode", choices=["local", "cai"], default="local")
    parser.add_argument(
        "--source-table",
        default=os.getenv("CREDIT_GOLD_TABLE", "hive.credit_demo.credit_features_v1"),
    )
    parser.add_argument("--model-name", default="credit_default_xgb_v1")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def build_local_gold_frame() -> pd.DataFrame:
    apps = pd.read_csv(DATA_DIR / "applications.csv")
    txns = pd.read_csv(DATA_DIR / "transactions.csv")

    income = (
        txns[txns["is_income"] == 1]
        .groupby(["application_id", "customer_id"])["amount"]
        .sum()
        .rename("income_inflow_90d")
    )
    spend = (
        txns[txns["is_income"] == 0]
        .groupby(["application_id", "customer_id"])["amount"]
        .sum()
        .rename("spend_outflow_90d")
    )
    txn_features = (
        txns.groupby(["application_id", "customer_id"])
        .agg(
            txn_count_90d=("transaction_id", "count"),
            merchant_category_diversity=("merchant_category", "nunique"),
            utility_payment_count=("merchant_category", lambda s: (s == "utilities").sum()),
            international_txn_count=("is_international", "sum"),
        )
        .reset_index()
    )
    txn_features = txn_features.merge(income, on=["application_id", "customer_id"], how="left")
    txn_features = txn_features.merge(spend, on=["application_id", "customer_id"], how="left")
    txn_features[["income_inflow_90d", "spend_outflow_90d"]] = txn_features[
        ["income_inflow_90d", "spend_outflow_90d"]
    ].fillna(0.0)

    txn_features["avg_txn_amount"] = np.where(
        txn_features["txn_count_90d"] > 0,
        txn_features["spend_outflow_90d"] / txn_features["txn_count_90d"],
        0.0,
    )
    txn_features["net_cash_flow_90d"] = (
        txn_features["income_inflow_90d"] - txn_features["spend_outflow_90d"]
    )
    txn_features["income_to_spend_ratio"] = np.where(
        txn_features["spend_outflow_90d"] > 0,
        txn_features["income_inflow_90d"] / txn_features["spend_outflow_90d"],
        0.0,
    )

    gold = apps.merge(txn_features, on=["application_id", "customer_id"], how="left")
    return gold.fillna(0)


def load_training_frame(mode: str, source_table: str) -> pd.DataFrame:
    if mode == "local":
        return build_local_gold_frame()

    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("credit_demo_train_load").getOrCreate()
        pdf = spark.table(source_table).toPandas()
        spark.stop()
        return pdf
    except Exception as exc:  # pragma: no cover - workshop fallback
        print(f"Could not read Spark table {source_table}: {exc}")
        print("Falling back to local CSV merge.")
        return build_local_gold_frame()


def decision_tier(probability: float, thin_file: int) -> str:
    if probability <= 0.35:
        return "approve"
    if probability <= 0.55 and thin_file == 1:
        return "review"
    if probability <= 0.65:
        return "review"
    return "decline"


def build_model(random_state: int):
    if MODEL_BACKEND == "xgboost":
        return XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
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
    X = frame[FEATURE_COLUMNS]
    y = frame["defaulted"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=args.random_state,
        stratify=y,
    )

    model = build_model(args.random_state)
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probabilities)

    thin_mask = frame.loc[X_test.index, "thin_file"] == 1
    thin_auc = roc_auc_score(y_test[thin_mask], probabilities[thin_mask]) if thin_mask.any() else None

    model_path = ARTIFACT_DIR / f"{args.model_name}.joblib"
    feature_path = ARTIFACT_DIR / f"{args.model_name}_features.json"
    metrics_path = ARTIFACT_DIR / f"{args.model_name}_metrics.json"

    joblib.dump(model, model_path)
    feature_path.write_text(json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8")
    metrics = {
        "model_name": args.model_name,
        "auc_holdout": round(float(auc), 4),
        "auc_holdout_thin_file": round(float(thin_auc), 4) if thin_auc is not None else None,
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
            "\nNext in Cloudera AI Registry:\n"
            "1. Log this run with MLflow / AI Registry.\n"
            "2. Register artifact path above as a model version.\n"
            "3. Promote to Inference service after validation."
        )


if __name__ == "__main__":
    main()
