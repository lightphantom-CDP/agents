"""
Lab 1 — Ingest raw credit application data into Iceberg.

CDE Resource: workshop-credit/01_ingest_raw.py

Arguments (optional, 2 rows):
  --db=workshop_credit_user001
  --landing=s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing
"""

import argparse
import logging
import os
import sys

SCRIPT_VERSION = "2026-08-10-v5"
DEFAULT_DB = "workshop_credit"
DEFAULT_LANDING = "s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-01-ingest-raw")

from pyspark.sql import SparkSession, functions as F


def _pick_arg(flag, default):
    """Resolve CLI flag from argv, env, or default (CDE PythonRunner-safe)."""
    env_key = flag.lstrip("-").replace("-", "_").upper()
    for arg in sys.argv:
        if arg == flag and sys.argv.index(arg) + 1 < len(sys.argv):
            return sys.argv[sys.argv.index(arg) + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return os.environ.get(env_key) or default


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    parser.add_argument("--landing", default=None)
    parser.add_argument("--synthetic", action="store_true")
    args, unknown = parser.parse_known_args()
    if unknown:
        logger.warning("Ignoring unknown argv entries: %s", unknown)

    db = args.db or _pick_arg("--db", DEFAULT_DB)
    landing = args.landing or _pick_arg("--landing", DEFAULT_LANDING)
    return argparse.Namespace(db=db, landing=landing, synthetic=args.synthetic)


def jlog(spark, message):
    """Write to Spark driver log (visible in CDE job logs)."""
    spark.sparkContext._jvm.org.apache.log4j.LogManager.getLogger(
        "credit-01-ingest-raw"
    ).info(message)


def generate_synthetic_data(spark, n_rows=10_000):
    return spark.range(0, n_rows).select(
        F.col("id").alias("Id"),
        (F.rand(seed=1) < 0.07).cast("int").alias("SeriousDlqin2yrs"),
        (F.rand(seed=2) * 2).alias("RevolvingUtilizationOfUnsecuredLines"),
        (F.floor(F.rand(seed=3) * 50) + 22).cast("int").alias("age"),
        F.floor(F.rand(seed=4) * 3).cast("int").alias("NumberOfTime30-59DaysPastDueNotWorse"),
        (F.rand(seed=5) * 2).alias("DebtRatio"),
        F.when(F.rand(seed=6) < 0.2, None).otherwise(F.rand(seed=7) * 15000).alias("MonthlyIncome"),
        F.floor(F.rand(seed=8) * 20).cast("int").alias("NumberOfOpenCreditLinesAndLoans"),
        F.floor(F.rand(seed=9) * 3).cast("int").alias("NumberOfTimes90DaysLate"),
        F.floor(F.rand(seed=10) * 5).cast("int").alias("NumberRealEstateLoansOrLines"),
        F.floor(F.rand(seed=11) * 2).cast("int").alias("NumberOfTime60-89DaysPastDueNotWorse"),
        F.when(F.rand(seed=12) < 0.15, None).otherwise(F.rand(seed=13) * 4).alias("NumberOfDependents"),
    )


def main():
    args = parse_args()
    spark = SparkSession.builder.appName("credit-01-ingest-raw").getOrCreate()

    jlog(spark, f"INGEST_SCRIPT_VERSION={SCRIPT_VERSION}")
    jlog(spark, f"argv={sys.argv}")
    jlog(spark, f"Starting ingest db={args.db} landing={args.landing}")

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")

    if args.synthetic:
        raw = generate_synthetic_data(spark)
    else:
        path = f"{args.landing.rstrip('/')}/cs-training.csv"
        jlog(spark, f"Reading CSV from {path}")
        try:
            raw = spark.read.csv(path, header=True, inferSchema=True)
            count = raw.count()
        except Exception as exc:
            jlog(spark, f"CSV read failed: {type(exc).__name__}: {exc}")
            jlog(
                spark,
                "Check: (1) file exists in S3 landing folder, "
                "(2) Ranger allows s3a read for user001, "
                "(3) path uses s3a:// not s3://",
            )
            raise

    count = raw.count()
    jlog(spark, f"Read {count} rows from source")
    if count == 0:
        raise ValueError("CSV has 0 rows — check file exists at landing/cs-training.csv")

    cleaned = (
        raw.withColumnRenamed("Id", "applicant_id")
        .withColumnRenamed("SeriousDlqin2yrs", "default_flag")
        .withColumnRenamed("RevolvingUtilizationOfUnsecuredLines", "utilization_raw")
        .withColumnRenamed("age", "age_raw")
        .withColumnRenamed("NumberOfTime30-59DaysPastDueNotWorse", "delinq_30_59")
        .withColumnRenamed("DebtRatio", "debt_ratio_raw")
        .withColumnRenamed("MonthlyIncome", "monthly_income_raw")
        .withColumnRenamed("NumberOfOpenCreditLinesAndLoans", "open_credit_lines_raw")
        .withColumnRenamed("NumberOfTimes90DaysLate", "delinq_90")
        .withColumnRenamed("NumberRealEstateLoansOrLines", "real_estate_loans_raw")
        .withColumnRenamed("NumberOfTime60-89DaysPastDueNotWorse", "delinq_60_89")
        .withColumnRenamed("NumberOfDependents", "dependents_raw")
        .withColumn("ingested_at", F.current_timestamp())
    )

    table = f"{args.db}.raw_applications"
    jlog(spark, f"Writing Iceberg table {table}")
    (
        cleaned.writeTo(table)
        .using("iceberg")
        .option("overwrite-schema", "true")
        .createOrReplace()
    )

    final_count = spark.table(table).count()
    msg = f"SUCCESS: wrote {final_count} rows to {table}"
    jlog(spark, msg)
    print(msg, flush=True)


try:
    main()
except Exception as exc:
    logger.exception("INGEST JOB FAILED")
    try:
        spark = SparkSession.getActiveSession()
        if spark:
            jlog(spark, f"INGEST JOB FAILED: {type(exc).__name__}: {exc}")
    except Exception:
        pass
    sys.exit(1)
