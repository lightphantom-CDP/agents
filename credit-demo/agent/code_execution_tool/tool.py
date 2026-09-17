"""
Agent Studio tool — review a credit application using Spark Gold output + trained model.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None


OUTPUT_KEY = "tool_output"

REASON_LABELS = {
    "inquiry_count_90d": "recent credit inquiries",
    "cash_flow_stability_score": "unstable cash inflow patterns",
    "debt_to_income_ratio": "high debt-to-income ratio",
    "prior_default_flag": "prior default history",
    "utility_on_time_pct": "late utility payment history",
    "thin_file": "limited credit history",
    "net_cash_flow_90d": "negative net cash flow",
    "device_trust_score": "low device trust score",
    "international_txn_count": "elevated international transaction activity",
    "credit_history_months": "credit history length",
    "tenure_months": "employment tenure",
    "txn_count_90d": "recent transaction activity",
}


def workflow_data_root() -> Path:
    return Path(os.environ.get("WORKFLOW_DATA_DIRECTORY", "/workflow_data"))


class UserParameters(BaseModel):
    """Paths to Gold table and model artifacts (under project /workflow_data)."""

    gold_path: str = Field(
        default="credit_demo_warehouse/credit_demo/credit_features_v1",
        description=(
            "Relative path under /workflow_data to the Gold Parquet folder "
            "created by Spark job 03_publish_gold_features.py"
        ),
    )
    model_path: str = Field(
        default="cai/artifacts/credit_default_xgb_v1.joblib",
        description="Relative path under /workflow_data to the trained model file",
    )
    features_path: str = Field(
        default="cai/artifacts/credit_default_xgb_v1_features.json",
        description="Relative path under /workflow_data to the model feature list JSON",
    )


class ToolParameters(BaseModel):
    application_id: str = Field(
        description="Loan application ID, for example APP-10482",
    )
    top_k: int = Field(
        default=3,
        description="Number of top SHAP reasons to return",
    )


def resolve_path(relative_or_absolute: str) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return workflow_data_root() / relative_or_absolute


def decision_tier(probability: float, thin_file: int) -> str:
    if probability <= 0.35:
        return "approve"
    if probability <= 0.55 and thin_file == 1:
        return "review"
    if probability <= 0.65:
        return "review"
    return "decline"


def xgboost_shap_contributions(model, features: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    if shap is not None:
        try:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(features)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            return np.asarray(shap_values[0], dtype=float)
        except ValueError:
            pass

    import xgboost as xgb

    dmatrix = xgb.DMatrix(features[feature_columns], feature_names=feature_columns)
    contribs = model.get_booster().predict(dmatrix, pred_contribs=True)
    return np.asarray(contribs[0, :-1], dtype=float)


def build_reasons(feature_columns: list[str], contributions: np.ndarray, top_k: int) -> list[dict[str, Any]]:
    ranked = sorted(
        zip(feature_columns, contributions),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:top_k]

    reasons = []
    for feature, contribution in ranked:
        label = REASON_LABELS.get(feature, feature.replace("_", " "))
        direction = "increased" if contribution > 0 else "reduced"
        reasons.append(
            {
                "feature": feature,
                "contribution": round(float(contribution), 4),
                "plain_language": f"{label} {direction} default risk",
            }
        )
    return reasons


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    gold_path = resolve_path(config.gold_path)
    model_path = resolve_path(config.model_path)
    features_path = resolve_path(config.features_path)

    if not gold_path.exists():
        return {
            "error": f"Gold table not found at {gold_path}. "
            "Upload credit_demo_warehouse to the project and add it to workflow data.",
        }
    if not model_path.exists():
        return {
            "error": f"Model not found at {model_path}. "
            "Upload cai/artifacts to the project and add it to workflow data.",
        }

    gold = pd.read_parquet(gold_path)
    row = gold.loc[gold["application_id"] == args.application_id]
    if row.empty:
        return {"error": f"Application not found: {args.application_id}"}

    feature_columns = json.loads(features_path.read_text(encoding="utf-8"))
    model = joblib.load(model_path)
    features = row[feature_columns].astype(float)
    probability = float(model.predict_proba(features)[0, 1])
    thin_file = int(row.iloc[0]["thin_file"])
    tier = decision_tier(probability, thin_file)

    contributions = xgboost_shap_contributions(model, features, feature_columns)
    reasons = build_reasons(feature_columns, contributions, args.top_k)

    return {
        "application_id": args.application_id,
        "customer_id": row.iloc[0]["customer_id"],
        "default_probability": round(probability, 4),
        "decision_tier": tier,
        "thin_file": thin_file,
        "monthly_income": float(row.iloc[0]["monthly_income"]),
        "requested_loan_amount": float(row.iloc[0]["requested_loan_amount"]),
        "debt_to_income_ratio": float(row.iloc[0]["debt_to_income_ratio"]),
        "top_reasons": reasons,
        "adverse_action_notice": (
            "Application declined due to: "
            + "; ".join(reason["plain_language"] for reason in reasons[:2])
            if tier == "decline"
            else None
        ),
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
    print(OUTPUT_KEY, json.dumps(result, indent=2))
