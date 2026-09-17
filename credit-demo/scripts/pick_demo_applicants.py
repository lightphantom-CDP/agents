#!/usr/bin/env python3
"""Print useful application IDs for live workshop demos."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "cai" / "artifacts"


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT))
    from cai.train_and_register import FEATURE_COLUMNS, build_local_gold_frame, decision_tier

    model = joblib.load(ARTIFACT_DIR / "credit_default_xgb_v1.joblib")
    frame = build_local_gold_frame()
    probs = model.predict_proba(frame[FEATURE_COLUMNS].astype(float))[:, 1]
    frame = frame.assign(default_probability=probs)
    frame["decision_tier"] = [
        decision_tier(prob, int(thin)) for prob, thin in zip(frame["default_probability"], frame["thin_file"])
    ]

    picks = {
        "decline_example": frame.sort_values("default_probability", ascending=False).head(1),
        "approve_example": frame.sort_values("default_probability", ascending=True).head(1),
        "thin_file_review": frame[frame["thin_file"] == 1]
        .sort_values("default_probability", ascending=False)
        .head(1),
        "borderline_review": frame[
            (frame["default_probability"] > 0.45) & (frame["default_probability"] < 0.60)
        ].head(1),
    }

    print("Suggested demo applicants:\n")
    for label, subset in picks.items():
        if subset.empty:
            print(f"- {label}: none found")
            continue
        row = subset.iloc[0]
        print(
            f"- {label}: {row['application_id']} "
            f"(p={row['default_probability']:.3f}, tier={row['decision_tier']}, thin_file={int(row['thin_file'])})"
        )

    metrics_path = ARTIFACT_DIR / "credit_default_xgb_v1_metrics.json"
    if metrics_path.exists():
        print("\nModel metrics:")
        print(json.dumps(json.loads(metrics_path.read_text()), indent=2))


if __name__ == "__main__":
    main()
