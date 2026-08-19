"""
Lab 6 — Batch score applicants via CAI model REST API.

CDE Job parameters:
  --db workshop_credit
  --model-url https://<cai-host>/model
  --model-name credit_default_model
  --model-version 1
  --access-key <gateway access key from CAI deployment Overview>
  --batch-size 1
  --max-rows 0
  --retries 3

Environment variable alternatives:
  CAI_MODEL_TOKEN
  CAI_MODEL_ACCESS_KEY
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime

import requests
from pyspark.sql import SparkSession, types as T

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
    parser.add_argument("--access-key", default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-rows", type=int, default=0, help="0 = score all rows; use 10 for a quick test")
    parser.add_argument("--retries", type=int, default=3, help="Retries for model API timeouts")
    return parser.parse_args()


def risk_band(probability: float) -> str:
    if probability < 0.10:
        return "A"
    if probability < 0.20:
        return "B"
    if probability < 0.35:
        return "C"
    return "D"


def feature_vector(row):
    values = []
    for col in FEATURE_COLS:
        val = row[col]
        if val is None:
            values.append(0.0)
        elif isinstance(val, bool):
            values.append(float(int(val)))
        else:
            num = float(val)
            if math.isnan(num) or math.isinf(num):
                num = 0.0
            values.append(num)
    return values


def score_batch(rows, model_url, token, access_key=None, retries=3):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    inner = {"inputs": [feature_vector(row) for row in rows]}
    if access_key:
        payload = {"accessKey": access_key, "request": inner}
    else:
        payload = inner

    if len(rows) == 1:
        logger.info("Sample payload: %s", json.dumps(payload)[:300])

    last_response = None
    for attempt in range(1, retries + 1):
        response = requests.post(model_url, headers=headers, json=payload, timeout=180)
        last_response = response
        if response.ok:
            break
        if response.status_code in (500, 502, 503, 504) and attempt < retries:
            logger.warning(
                "Model API attempt %s/%s failed (%s), retrying in 45s: %s",
                attempt,
                retries,
                response.status_code,
                response.text[:200],
            )
            time.sleep(45)
            continue
        logger.error("Model API error %s: %s", response.status_code, response.text[:500])
        response.raise_for_status()
    else:
        last_response.raise_for_status()
    response = last_response
    body = response.json()

    if isinstance(body, dict) and "response" in body:
        body = body["response"]

    if isinstance(body, dict) and "predictions" in body:
        preds = body["predictions"]
    elif isinstance(body, list):
        preds = body
    else:
        preds = body.get("outputs", body)

    scored = []
    for row, pred in zip(rows, preds):
        if isinstance(pred, (list, tuple)):
            prob = float(pred[1] if len(pred) > 1 else pred[0])
        else:
            prob = float(pred)
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
    access_key = args.access_key or os.environ.get("CAI_MODEL_ACCESS_KEY")
    if not access_key and "modelservice" in args.model_url:
        raise ValueError(
            "Missing --access-key (or CAI_MODEL_ACCESS_KEY env var). "
            "Required for gateway URL .../model"
        )
    logger.info(
        "Config: db=%s batch_size=%s access_key_set=%s max_rows=%s",
        args.db,
        args.batch_size,
        bool(access_key),
        args.max_rows,
    )
    spark = SparkSession.builder.appName("credit-04-batch-score").getOrCreate()

    features = spark.table(f"{args.db}.features").select("applicant_id", *FEATURE_COLS)
    scored_at = datetime.utcnow().isoformat()

    all_scores = []
    buffer = []
    row_count = 0
    for row in features.toLocalIterator():
        record = row.asDict()
        record["model_name"] = args.model_name
        record["model_version"] = args.model_version
        record["scored_at"] = scored_at
        buffer.append(record)
        row_count += 1
        if len(buffer) >= args.batch_size:
            all_scores.extend(score_batch(buffer, args.model_url, token, access_key, args.retries))
            buffer = []
        if args.max_rows and row_count >= args.max_rows:
            break

    if buffer:
        all_scores.extend(score_batch(buffer, args.model_url, token, access_key, args.retries))

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
