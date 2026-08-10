"""
Lab 1 — Ingest raw credit application data into Iceberg.

CDE Job parameters:
  --db workshop_credit
  --landing s3a://your-bucket/workshop/credit_scoring/landing

Optional (no CSV available):
  --synthetic   Generate 10,000 synthetic rows instead of reading CSV.
"""

import argparse
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Hive/Iceberg database name")
    parser.add_argument(
        "--landing",
        default=None,
        help="Landing path containing cs-training.csv",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate synthetic data when CSV is unavailable",
    )
    return parser.parse_args()


def generate_synthetic_data(spark, n_rows=10_000):
  """Fallback dataset for workshops without Kaggle access."""
  schema = StructType(
      [
          StructField("Id", IntegerType(), False),
          StructField("SeriousDlqin2yrs", IntegerType(), False),
          StructField("RevolvingUtilizationOfUnsecuredLines", DoubleType(), False),
          StructField("age", IntegerType(), False),
          StructField("NumberOfTime30-59DaysPastDueNotWorse", IntegerType(), False),
          StructField("DebtRatio", DoubleType(), False),
          StructField("MonthlyIncome", DoubleType(), True),
          StructField("NumberOfOpenCreditLinesAndLoans", IntegerType(), False),
          StructField("NumberOfTimes90DaysLate", IntegerType(), False),
          StructField("NumberRealEstateLoansOrLines", IntegerType(), False),
          StructField("NumberOfTime60-89DaysPastDueNotWorse", IntegerType(), False),
          StructField("NumberOfDependents", DoubleType(), True),
      ]
  )
  pdf = spark.range(0, n_rows).select(
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
  return pdf


def main():
    args = parse_args()
    spark = SparkSession.builder.appName("credit-01-ingest-raw").getOrCreate()

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")

    if args.synthetic:
        raw = generate_synthetic_data(spark)
    else:
        if not args.landing:
            raise ValueError("Provide --landing path or use --synthetic")
        path = f"{args.landing.rstrip('/')}/cs-training.csv"
        raw = spark.read.csv(path, header=True, inferSchema=True)

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
    (
        cleaned.writeTo(table)
        .using("iceberg")
        .option("overwrite-schema", "true")
        .createOrReplace()
    )

    count = spark.table(table).count()
    print(f"SUCCESS: wrote {count} rows to {table}")


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    main()
