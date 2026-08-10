"""
Lab 4 — Train credit default model with MLflow (run in CAI Workbench).

Prerequisites:
  - workshop_credit.features table populated (Lab 2)
  - pip install xgboost scikit-learn mlflow shap
"""

import json

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# --- CONFIG: update for your environment ---
WORKSHOP_DB = "workshop_credit"
FEATURES_TABLE = f"{WORKSHOP_DB}.features"
FEATURES_SNAPSHOT_ID = "REPLACE_WITH_SNAPSHOT_ID"  # from Lab 2 job logs
EXPERIMENT_NAME = "credit_default_prediction"
REGISTERED_MODEL_NAME = "credit_default_model"

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
LABEL_COL = "default_flag"


def ks_statistic(y_true, y_prob):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    return float(np.max(tpr - fpr))


def gini_from_auc(auc):
    return 2 * auc - 1


def load_features():
    """Load from Spark table. Requires Spark-enabled CAI session."""
    pdf = spark.table(FEATURES_TABLE).select(*FEATURE_COLS, LABEL_COL, "applicant_id").toPandas()
    return pdf


def train(max_depth=4, learning_rate=0.1, n_estimators=200):
    mlflow.set_experiment(EXPERIMENT_NAME)
    df = load_features()

    X = df[FEATURE_COLS]
    y = df[LABEL_COL]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        max_depth=max_depth,
        learning_rate=learning_rate,
        n_estimators=n_estimators,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        n_jobs=4,
    )

    with mlflow.start_run(run_name=f"xgb_depth{max_depth}"):
        mlflow.log_params(
            {
                "max_depth": max_depth,
                "learning_rate": learning_rate,
                "n_estimators": n_estimators,
                "features_table": FEATURES_TABLE,
                "features_snapshot_id": FEATURES_SNAPSHOT_ID,
            }
        )

        model.fit(X_train, y_train)
        prob = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, prob)
        ks = ks_statistic(y_test, prob)
        gini = gini_from_auc(auc)

        mlflow.log_metrics({"auc": auc, "ks": ks, "gini": gini})
        mlflow.sklearn.log_model(model, artifact_path="model")

        print(json.dumps({"auc": auc, "ks": ks, "gini": gini}, indent=2))
        return model, {"auc": auc, "ks": ks, "gini": gini}


if __name__ == "__main__":
    # Run three experiments for MLflow comparison demo
    for depth in [3, 4, 6]:
        train(max_depth=depth)

    print(f"\nNext step: register best run as '{REGISTERED_MODEL_NAME}' in Model Registry")
