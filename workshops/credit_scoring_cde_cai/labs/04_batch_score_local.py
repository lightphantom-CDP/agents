"""
Lab 6 workaround — Batch score using a local model on S3 (no HTTP API).

Use when the CAI model gateway times out OR CAI Spark cannot read Iceberg.

Prerequisites:
  1. From CAI, upload exported model to S3:
       cd /home/cdsw && tar czf model_files.tgz model_files/
       hadoop fs -put -f model_files.tgz s3a://<bucket>/workshop/credit_scoring/models/<user>/model_files.tgz
  2. Upload this script to CDE Resources.

CDE Job parameters:
  --db workshop_credit_user_xx
  --model-s3 s3a://<bucket>/workshop/credit_scoring/models/<user>/model_files.tgz
  --model-name xgboost1
  --model-version 1
  --score-batch-size 5000
  --max-rows 0
"""

import argparse
import importlib
import logging
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime

from pyspark.sql import SparkSession, types as T

print(">>> 04_batch_score_local.py LOADED <<<", flush=True)

DEPS_DIR = "/tmp/credit-score-pydeps"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-04-batch-score-local")

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
    parser.add_argument("--model-s3", required=True, help="s3a:// path to model_files.tgz")
    parser.add_argument("--model-name", default="xgboost1")
    parser.add_argument("--model-version", default="1")
    parser.add_argument(
        "--score-batch-size",
        type=int,
        default=5000,
        help="Rows scored per predict_proba call on the driver",
    )
    parser.add_argument("--max-rows", type=int, default=0, help="0 = score all rows")
    return parser.parse_args()


def risk_band(probability: float) -> str:
    if probability < 0.10:
        return "A"
    if probability < 0.20:
        return "B"
    if probability < 0.35:
        return "C"
    return "D"


def ensure_packages(packages):
    """Install missing Python packages where the Spark driver can import them."""
    if os.path.isdir(DEPS_DIR) and DEPS_DIR not in sys.path:
        sys.path.insert(0, DEPS_DIR)

    missing = []
    for module_name, pip_name in packages:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name or module_name)
    if not missing:
        return

    os.makedirs(DEPS_DIR, exist_ok=True)
    logger.info("Installing missing packages to %s: %s", DEPS_DIR, ", ".join(missing))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "--no-cache-dir",
            "--target",
            DEPS_DIR,
            *missing,
        ],
        check=True,
    )
    if DEPS_DIR not in sys.path:
        sys.path.insert(0, DEPS_DIR)
    importlib.invalidate_caches()

    still_missing = []
    for module_name, pip_name in packages:
        try:
            importlib.import_module(module_name)
        except ImportError:
            still_missing.append(pip_name or module_name)
    if still_missing:
        raise ImportError(f"Packages still missing after pip install: {still_missing}")


def load_model(model_dir: str):
    """Load MLflow-exported sklearn model without mlflow (uses model.pkl)."""
    ensure_packages(
        [
            ("numpy", "numpy"),
            ("joblib", "joblib"),
            ("sklearn", "scikit-learn"),
            ("xgboost", "xgboost"),
        ]
    )

    import joblib

    pkl_path = os.path.join(model_dir, "model.pkl")
    if not os.path.isfile(pkl_path):
        raise FileNotFoundError(f"No model.pkl in {model_dir}")
    model = joblib.load(pkl_path)
    if not hasattr(model, "predict_proba"):
        raise TypeError(f"Loaded object has no predict_proba: {type(model)}")
    return model


def download_model(spark, model_s3: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    tgz_path = os.path.join(dest_dir, "model_files.tgz")
    logger.info("Downloading model from %s to %s", model_s3, tgz_path)

    jvm = spark.sparkContext._jvm
    conf = spark.sparkContext._jsc.hadoopConfiguration()
    src = jvm.org.apache.hadoop.fs.Path(model_s3)
    fs = src.getFileSystem(conf)
    dst = jvm.org.apache.hadoop.fs.Path(tgz_path)
    fs.copyToLocalFile(False, src, dst)

    with tarfile.open(tgz_path, "r:gz") as archive:
        archive.extractall(dest_dir)
    model_path = os.path.join(dest_dir, "model_files")
    if not os.path.isdir(model_path):
        raise FileNotFoundError(f"Expected model_files/ under {dest_dir}")
    return model_path


def row_to_features(row):
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


def score_rows(rows, model, model_name, model_version, scored_at):
    if not rows:
        return []
    import numpy as np

    matrix = np.array([row_to_features(row) for row in rows], dtype=np.float64)
    proba = model.predict_proba(matrix)[:, 1]
    scored = []
    for row, prob in zip(rows, proba):
        scored.append(
            {
                "applicant_id": int(row["applicant_id"]),
                "probability_default": float(prob),
                "risk_band": risk_band(float(prob)),
                "model_name": model_name,
                "model_version": model_version,
                "scored_at": scored_at,
            }
        )
    return scored


def main():
    args = parse_args()
    print(
        f">>> START batch_score_local db={args.db} max_rows={args.max_rows} <<<",
        flush=True,
    )
    logger.info(
        "Config: db=%s model_s3=%s score_batch_size=%s max_rows=%s",
        args.db,
        args.model_s3,
        args.score_batch_size,
        args.max_rows,
    )

    spark = SparkSession.builder.appName("credit-04-batch-score-local").getOrCreate()
    work_dir = tempfile.mkdtemp(prefix="credit-score-")
    try:
        model_path = download_model(spark, args.model_s3, work_dir)
        model = load_model(model_path)
        logger.info("Model loaded from %s/model.pkl", model_path)
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise

    features = spark.table(f"{args.db}.features").select("applicant_id", *FEATURE_COLS)
    scored_at = datetime.utcnow().isoformat()

    all_scores = []
    buffer = []
    row_count = 0
    for row in features.toLocalIterator():
        buffer.append(row.asDict())
        row_count += 1
        if len(buffer) >= args.score_batch_size:
            all_scores.extend(
                score_rows(buffer, model, args.model_name, args.model_version, scored_at)
            )
            logger.info("Scored %s rows so far", row_count)
            buffer = []
        if args.max_rows and row_count >= args.max_rows:
            break

    if buffer:
        all_scores.extend(
            score_rows(buffer, model, args.model_name, args.model_version, scored_at)
        )

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
    shutil.rmtree(work_dir, ignore_errors=True)


try:
    main()
except Exception:
    logger.exception("LOCAL BATCH SCORE JOB FAILED")
    sys.exit(1)
