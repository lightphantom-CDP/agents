"""
Lab 6 — Batch score applicants via CAI model REST API.

CDE Job parameters:
  --db workshop_credit
  --model-url https://<cai-host>/model/credit-scoring-api/infer
  --model-name credit_default_model
  --model-version 1
  --auth-token <optional bearer token>

Environment variable alternative:
  CAI_MODEL_TOKEN
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import requests
from pyspark.sql import SparkSession, functions as F, types as T

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-04-batch-score")


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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--model-url", required=True)
    parser.add_argument("--model-name", default="credit_default_model")
    parser.add_argument("--model-version", default="1")
    parser.add_argument("--auth-token", default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    return parser.parse_args()


def risk_band(probability: float) -> str:
    if probability < 0.10:
        return "A"
    if probability < 0.20:
        return "B"
    if probability < 0.35:
        return "C"
    return "D"


def score_batch(rows, model_url, token):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"inputs": [[float(row[c]) for c in FEATURE_COLS] for row in rows]}
    response = requests.post(model_url, headers=headers, data=json.dumps(payload), timeout=120)
    response.raise_for_status()
    body = response.json()

    # Support common CAI / MLflow response shapes
    if isinstance(body, dict) and "predictions" in body:
        preds = body["predictions"]
    elif isinstance(body, list):
        preds = body
    else:
        preds = body.get("outputs", body)

    scored = []
    for row, pred in zip(rows, preds):
        prob = float(pred[0] if isinstance(pred, (list, tuple)) else pred)
        scored.append(
            {
                "applicant_id": int(row["applicant_id"]),
                "probability_default": prob,
                "risk_band": risk_band(prob),
                "model_name": row["model_name"],
                "model_version": row["model_version"],
                "scored_at": row["scored_at"],
            }
        )
    return scored


def main():
    args = parse_args()
    token = args.auth_token or os.environ.get("CAI_MODEL_TOKEN")
    spark = SparkSession.builder.appName("credit-04-batch-score").getOrCreate()

    features = spark.table(f"{args.db}.features").select("applicant_id", *FEATURE_COLS)
    scored_at = datetime.utcnow().isoformat()

    all_scores = []
    buffer = []
    for row in features.toLocalIterator():
        record = row.asDict()
        record["model_name"] = args.model_name
        record["model_version"] = args.model_version
        record["scored_at"] = scored_at
        buffer.append(record)
        if len(buffer) >= args.batch_size:
            all_scores.extend(score_batch(buffer, args.model_url, token))
            buffer = []

    if buffer:
        all_scores.extend(score_batch(buffer, args.model_url, token))

    schema = T.StructType(
        [
            T.StructField("applicant_id", T.LongType(), False),
            T.StructField("probability_default", T.DoubleType(), False),
            T.StructField("risk_band", T.StringType(), False),
            T.StructField("model_name", T.StringType(), False),
            T.StructField("model_version", T.StringType(), False),
            T.StructField("scored_at", T.StringType(), False),
        ]
    )

    scores_df = spark.createDataFrame(all_scores, schema=schema)
    scores_table = f"{args.db}.scores"
    scores_df.writeTo(scores_table).using("iceberg").option("overwrite-schema", "true").createOrReplace()

    logger.info("SUCCESS: scored applicants into %s", scores_table)
    print(f"SUCCESS: scored {scores_df.count()} applicants into {scores_table}")
    scores_df.groupBy("risk_band").count().orderBy("risk_band").show()


try:
    main()
except Exception:
    logger.exception("BATCH SCORE JOB FAILED")
    sys.exit(1)
