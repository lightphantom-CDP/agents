"""
Lab 7 — SHAP-based reason codes for credit decisions (CAI Workbench).

Run after training. Requires: pip install shap
"""

import json

import mlflow
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split

WORKSHOP_DB = "workshop_credit"
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


def load_model_from_mlflow(run_id=None):
    client = mlflow.tracking.MlflowClient()
    if run_id is None:
        experiment = client.get_experiment_by_name("credit_default_prediction")
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["metrics.auc DESC"],
            max_results=1,
        )
        run_id = runs[0].info.run_id
    model_uri = f"runs:/{run_id}/model"
    return mlflow.sklearn.load_model(model_uri), run_id


def explain_applicant(model, applicant_row: pd.Series, background: pd.DataFrame, top_n=4):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(applicant_row[FEATURE_COLS].values.reshape(1, -1))

    if isinstance(shap_values, list):
        values = shap_values[1][0]
    else:
        values = shap_values[0]

    contributions = sorted(
        zip(FEATURE_COLS, values),
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:top_n]

    prob = float(model.predict_proba(applicant_row[FEATURE_COLS].values.reshape(1, -1))[0, 1])
    return prob, contributions


def main():
    df = spark.table(f"{WORKSHOP_DB}.features").select(*FEATURE_COLS, "applicant_id", "default_flag").toPandas()
    model, run_id = load_model_from_mlflow()

    _, X_sample = train_test_split(df, test_size=0.2, random_state=42, stratify=df["default_flag"])
    background = X_sample[FEATURE_COLS].sample(500, random_state=42)

    # Pick highest utilization applicant in sample for demo
    applicant = X_sample.sort_values("utilization", ascending=False).iloc[0]
    prob, reasons = explain_applicant(model, applicant, background)

    output = {
        "applicant_id": int(applicant["applicant_id"]),
        "probability_default": round(prob, 4),
        "mlflow_run_id": run_id,
        "top_reasons": [
            {"feature": name, "shap_contribution": round(float(val), 4)} for name, val in reasons
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
