#!/usr/bin/env python3
"""Generate SHAP explanations and sample adverse-action reasons for one applicant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

try:
    import shap
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install shap with: pip install shap") from exc

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
DATA_DIR = ROOT / "data"

FEATURE_COLUMNS = json.loads((ARTIFACT_DIR / "credit_default_xgb_v1_features.json").read_text())


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
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain one credit decision")
    parser.add_argument("--application-id", default="APP-10482")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def load_applicant(application_id: str) -> pd.Series:
    from train_and_register import build_local_gold_frame

    frame = build_local_gold_frame()
    row = frame.loc[frame["application_id"] == application_id]
    if row.empty:
        raise ValueError(f"Application not found: {application_id}")
    return row.iloc[0]


def load_background_features(limit: int = 200) -> pd.DataFrame:
    from train_and_register import build_local_gold_frame

    frame = build_local_gold_frame().head(limit)
    return frame[FEATURE_COLUMNS].astype(float)


def xgboost_shap_contributions(model, features: pd.DataFrame) -> np.ndarray:
    """Return per-feature SHAP contributions for one row (XGBoost binary classifier)."""
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(features)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        return np.asarray(shap_values[0], dtype=float)
    except ValueError:
        # XGBoost >= 3.1 stores base_score as a list string; older SHAP cannot parse it.
        import xgboost as xgb

        dmatrix = xgb.DMatrix(features, feature_names=list(features.columns))
        contribs = model.get_booster().predict(dmatrix, pred_contribs=True)
        return np.asarray(contribs[0, :-1], dtype=float)


def main() -> None:
    args = parse_args()
    model = joblib.load(ARTIFACT_DIR / "credit_default_xgb_v1.joblib")
    applicant = load_applicant(args.application_id)

    features = applicant[FEATURE_COLUMNS].astype(float).to_frame().T
    probability = float(model.predict_proba(features)[0, 1])

    metrics = json.loads((ARTIFACT_DIR / "credit_default_xgb_v1_metrics.json").read_text())
    if metrics.get("model_backend") == "xgboost":
        contributions = xgboost_shap_contributions(model, features)
    else:
        background = load_background_features(limit=200)
        explainer = shap.Explainer(model.predict_proba, background)
        shap_values = explainer(features)
        contributions = shap_values.values[0][:, 1]

    ranked = sorted(
        zip(FEATURE_COLUMNS, contributions),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[: args.top_k]

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

    thin_file = int(applicant["thin_file"])
    if probability <= 0.35:
        tier = "approve"
    elif probability <= 0.55 and thin_file == 1:
        tier = "review"
    elif probability <= 0.65:
        tier = "review"
    else:
        tier = "decline"

    output = {
        "application_id": args.application_id,
        "customer_id": applicant["customer_id"],
        "default_probability": round(probability, 4),
        "decision_tier": tier,
        "thin_file": thin_file,
        "top_reasons": reasons,
        "adverse_action_notice": (
            "Application declined due to: "
            + "; ".join(reason["plain_language"] for reason in reasons[:2])
            if tier == "decline"
            else None
        ),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
