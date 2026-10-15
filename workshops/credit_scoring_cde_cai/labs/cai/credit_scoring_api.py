"""
CAI model deployment API for credit scoring workshop.

Deploy from code:
  Build script: cdsw-build.sh
  File: credit_scoring_api.py
  Function: predict
"""

import json
import sys

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

model = mlflow.sklearn.load_model("/home/cdsw/model_files")


def _parse_inputs(args):
    if isinstance(args, str):
        args = json.loads(args)
    if isinstance(args, dict) and "request" in args:
        args = args["request"]
    if isinstance(args, dict) and "inputs" in args:
        return args["inputs"]
    return args


def predict(args):
    try:
        inputs = _parse_inputs(args)
        df = pd.DataFrame(inputs, columns=FEATURE_COLS).fillna(0.0)
        proba = model.predict_proba(df)
        result = {"predictions": proba.tolist()}
        print(f"predict ok rows={len(inputs)}", file=sys.stderr)
        return result
    except Exception as exc:
        print(f"predict failed: {exc}", file=sys.stderr)
        raise
