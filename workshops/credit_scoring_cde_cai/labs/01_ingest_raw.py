"""
Lab 1 — Ingest raw credit application data into Iceberg.

CDE Job parameters (use separate rows OR equals form):
  --db=workshop_credit
  --landing=s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing

Optional:
  --synthetic   Generate synthetic rows instead of reading CSV.
"""

import argparse
import logging
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StructField,
    StructType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-01-ingest-raw")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Hive/Iceberg database name")
    parser.add_argument("--landing", default=None, help="S3 landing folder with cs-training.csv")
    parser.add_argument("--synthetic", action="store_true", help="Generate synthetic data")
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
    logger.info("Starting ingest job")
    logger.info("db=%s landing=%s synthetic=%s", args.db, args.landing, args.synthetic)

    spark = SparkSession.builder.appName("credit-01-ingest-raw").getOrCreate()
    logger.info("SparkSession created")

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")
    logger.info("Database ready: %s", args.db)

    if args.synthetic:
        raw = generate_synthetic_data(spark)
    else:
        if not args.landing:
            raise ValueError("Provide --landing path or use --synthetic")
        path = f"{args.landing.rstrip('/')}/cs-training.csv"
        logger.info("Reading CSV from %s", path)
        raw = spark.read.csv(path, header=True, inferSchema=True)

    row_count = raw.count()
    logger.info("Read %s rows from source", row_count)
    if row_count == 0:
        raise ValueError("Source has 0 rows — check CSV path and file name")

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

    count = spark.table(table).count()
    logger.info("SUCCESS: wrote %s rows to %s", count, table)
    print(f"SUCCESS: wrote {count} rows to {table}")


# CDE Spark: always call main() — do not rely on if __name__ == "__main__"
try:
    main()
except Exception:
    logger.exception("INGEST JOB FAILED")
    sys.exit(1)
