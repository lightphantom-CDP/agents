#!/usr/bin/env python3
"""CDE Job 03 — Publish Gold feature table for model training and serving."""

from __future__ import annotations

import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from catalog_utils import build_spark, read_table, write_table


FEATURE_COLUMNS = [
    "age",
    "monthly_income",
    "requested_loan_amount",
    "tenure_months",
    "existing_loans",
    "credit_history_months",
    "thin_file",
    "utility_on_time_pct",
    "cash_flow_stability_score",
    "inquiry_count_90d",
    "debt_to_income_ratio",
    "device_trust_score",
    "prior_default_flag",
    "txn_count_90d",
    "merchant_category_diversity",
    "utility_payment_count",
    "international_txn_count",
    "avg_txn_amount",
    "net_cash_flow_90d",
    "income_to_spend_ratio",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish gold credit features")
    parser.add_argument(
        "--catalog",
        default=os.getenv("CREDIT_CATALOG", "spark_catalog"),
    )
    parser.add_argument("--database", default=os.getenv("CREDIT_DATABASE", "credit_demo"))
    parser.add_argument("--feature-version", default=os.getenv("FEATURE_VERSION", "v1"))
    parser.add_argument(
        "--warehouse-path",
        default=os.getenv("CREDIT_WAREHOUSE_PATH", ""),
    )
    return parser.parse_known_args()[0]


def main() -> None:
    args = parse_args()
    warehouse = args.warehouse_path or None
    spark = build_spark("credit_demo_03_publish_gold", warehouse)

    apps = read_table(spark, args.catalog, args.database, "raw_applications", warehouse)
    silver = read_table(spark, args.catalog, args.database, "customer_behavior_30d", warehouse)

    join_keys = {"application_id", "customer_id"}
    silver_overlap = [col for col in silver.columns if col in apps.columns and col not in join_keys]
    silver_for_join = silver.drop(*silver_overlap)

    gold = (
        apps.join(silver_for_join, on=["application_id", "customer_id"], how="left")
        .select(
            "application_id",
            "customer_id",
            "applied_at",
            "employment_status",
            "loan_purpose",
            "region",
            *FEATURE_COLUMNS,
            "defaulted",
        )
        .withColumn("feature_version", F.lit(args.feature_version))
        .withColumn("published_at", F.current_timestamp())
    )

    target = write_table(
        gold,
        args.catalog,
        args.database,
        f"credit_features_{args.feature_version}",
        warehouse,
    )
    print(f"Gold table refreshed: {target} ({gold.count()} rows)")


if __name__ == "__main__":
    main()
