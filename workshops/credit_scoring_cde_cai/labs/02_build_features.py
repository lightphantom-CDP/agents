"""
Lab 2 — Build model-ready credit features in Iceberg.

CDE Job parameters:
  --db workshop_credit
"""

import argparse
from pyspark.sql import SparkSession, functions as F


FEATURE_COLS = [
    "applicant_id",
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
    "default_flag",
    "feature_built_at",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    return parser.parse_args()


def build_features(raw_df):
    median_income = (
        raw_df.filter(F.col("monthly_income_raw").isNotNull())
        .approxQuantile("monthly_income_raw", [0.5], 0.01)[0]
    )

    return (
        raw_df.withColumn("utilization", F.least(F.greatest(F.col("utilization_raw"), F.lit(0.0)), F.lit(10.0)))
        .withColumn("age", F.least(F.greatest(F.col("age_raw"), F.lit(18)), F.lit(100)))
        .withColumn("debt_ratio", F.least(F.greatest(F.col("debt_ratio_raw"), F.lit(0.0)), F.lit(100.0)))
        .withColumn(
            "delinq_total",
            F.coalesce(F.col("delinq_30_59"), F.lit(0))
            + F.coalesce(F.col("delinq_60_89"), F.lit(0))
            + F.coalesce(F.col("delinq_90"), F.lit(0)),
        )
        .withColumn("open_credit_lines", F.coalesce(F.col("open_credit_lines_raw"), F.lit(0)))
        .withColumn("real_estate_loans", F.coalesce(F.col("real_estate_loans_raw"), F.lit(0)))
        .withColumn("dependents", F.coalesce(F.col("dependents_raw"), F.lit(0.0)))
        .withColumn("income_missing", F.when(F.col("monthly_income_raw").isNull(), 1).otherwise(0))
        .withColumn(
            "monthly_income",
            F.when(F.col("monthly_income_raw").isNull(), F.lit(median_income)).otherwise(F.col("monthly_income_raw")),
        )
        .withColumn("high_utilization_flag", F.when(F.col("utilization") > 0.75, 1).otherwise(0))
        .withColumn("default_flag", F.col("default_flag").cast("int"))
        .withColumn("feature_built_at", F.current_timestamp())
        .select(*FEATURE_COLS)
    )


def main():
    args = parse_args()
    spark = SparkSession.builder.appName("credit-02-build-features").getOrCreate()

    raw_table = f"{args.db}.raw_applications"
    features_table = f"{args.db}.features"

    raw = spark.table(raw_table)
    features = build_features(raw)

    features.writeTo(features_table).using("iceberg").option("overwrite-schema", "true").createOrReplace()

    count = spark.table(features_table).count()
    default_rate = (
        spark.table(features_table).groupBy("default_flag").count().orderBy("default_flag").collect()
    )
    print(f"SUCCESS: wrote {count} rows to {features_table}")
    print(f"Default distribution: {default_rate}")

    snapshot = spark.sql(f"SELECT snapshot_id FROM {features_table}.snapshots ORDER BY committed_at DESC LIMIT 1").collect()
    if snapshot:
        print(f"LATEST_SNAPSHOT_ID={snapshot[0]['snapshot_id']}")


if __name__ == "__main__":
    main()
