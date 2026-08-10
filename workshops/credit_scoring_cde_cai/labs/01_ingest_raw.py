"""
Lab 1 — Ingest raw credit application data into Iceberg.

CDE: upload to Resources (recommended), NOT as S3 application file.

Arguments (4 separate rows):
  --db
  workshop_credit
  --landing
  s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing

Or Spark config / env fallback:
  WORKSHOP_DB=workshop_credit
  WORKSHOP_LANDING=s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing
"""

import argparse
import os
import sys

print(">>> 01_ingest_raw.py LOADED <<<", flush=True)

from pyspark.sql import SparkSession, functions as F


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("WORKSHOP_DB"))
    parser.add_argument("--landing", default=os.environ.get("WORKSHOP_LANDING"))
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if not args.db:
        raise ValueError("Missing --db (or env WORKSHOP_DB)")
    return args


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
    print(f">>> START ingest db={args.db} landing={args.landing} <<<", flush=True)

    spark = SparkSession.builder.appName("credit-01-ingest-raw").getOrCreate()
    print(">>> SparkSession OK <<<", flush=True)

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")
    print(f">>> Database OK: {args.db} <<<", flush=True)

    if args.synthetic:
        raw = generate_synthetic_data(spark)
    else:
        if not args.landing:
            raise ValueError("Missing --landing (or env WORKSHOP_LANDING)")
        path = f"{args.landing.rstrip('/')}/cs-training.csv"
        print(f">>> Reading: {path} <<<", flush=True)
        raw = spark.read.csv(path, header=True, inferSchema=True)

    count = raw.count()
    print(f">>> Read {count} rows <<<", flush=True)
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
    print(f">>> Writing Iceberg table: {table} <<<", flush=True)
    (
        cleaned.writeTo(table)
        .using("iceberg")
        .option("overwrite-schema", "true")
        .createOrReplace()
    )

    final_count = spark.table(table).count()
    print(f"SUCCESS: wrote {final_count} rows to {table}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"INGEST JOB FAILED: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)
