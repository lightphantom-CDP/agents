"""
Lab 1 — Ingest raw credit application data into Iceberg.

CDE Resource path: workshop-credit/01_ingest_raw.py

Job arguments (optional — defaults match this workshop):
  --db workshop_credit
  --landing s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing
"""

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-01-ingest-raw")

DEFAULT_DB = "workshop_credit"
DEFAULT_LANDING = "s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing"

logger.info("01_ingest_raw.py loaded argv=%s name=%s", sys.argv, __name__)

from pyspark.sql import SparkSession, functions as F


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=os.environ.get("WORKSHOP_DB", DEFAULT_DB),
    )
    parser.add_argument(
        "--landing",
        default=os.environ.get("WORKSHOP_LANDING", DEFAULT_LANDING),
    )
    parser.add_argument("--synthetic", action="store_true")
    return parser.parse_args()


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
    logger.info("Starting ingest db=%s landing=%s", args.db, args.landing)

    spark = SparkSession.builder.appName("credit-01-ingest-raw").getOrCreate()

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")

    if args.synthetic:
        raw = generate_synthetic_data(spark)
    else:
        path = f"{args.landing.rstrip('/')}/cs-training.csv"
        logger.info("Reading CSV from %s", path)
        raw = spark.read.csv(path, header=True, inferSchema=True)

    count = raw.count()
    logger.info("Read %s rows from source", count)
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
    logger.info("Writing Iceberg table %s", table)
    (
        cleaned.writeTo(table)
        .using("iceberg")
        .option("overwrite-schema", "true")
        .createOrReplace()
    )

    final_count = spark.table(table).count()
    msg = f"SUCCESS: wrote {final_count} rows to {table}"
    logger.info(msg)
    print(msg, flush=True)


try:
    main()
except Exception:
    logger.exception("INGEST JOB FAILED")
    sys.exit(1)
