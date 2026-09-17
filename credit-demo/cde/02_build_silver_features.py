#!/usr/bin/env python3
"""CDE Job 02 — Build Silver behavioral features from transactions."""

from __future__ import annotations

import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from catalog_utils import build_spark, read_table, write_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build silver credit features")
    parser.add_argument(
        "--catalog",
        default=os.getenv("CREDIT_CATALOG", "spark_catalog"),
    )
    parser.add_argument("--database", default=os.getenv("CREDIT_DATABASE", "credit_demo"))
    parser.add_argument(
        "--warehouse-path",
        default=os.getenv("CREDIT_WAREHOUSE_PATH", ""),
    )
    return parser.parse_known_args()[0]


def main() -> None:
    args = parse_args()
    warehouse = args.warehouse_path or None
    spark = build_spark("credit_demo_02_build_silver", warehouse)

    apps = read_table(spark, args.catalog, args.database, "raw_applications", warehouse)
    txns = read_table(spark, args.catalog, args.database, "raw_transactions", warehouse)

    txn_features = (
        txns.groupBy("application_id", "customer_id")
        .agg(
            F.count("*").alias("txn_count_90d"),
            F.sum(F.when(F.col("is_income") == 1, F.col("amount")).otherwise(0)).alias(
                "income_inflow_90d"
            ),
            F.sum(F.when(F.col("is_income") == 0, F.col("amount")).otherwise(0)).alias(
                "spend_outflow_90d"
            ),
            F.countDistinct("merchant_category").alias("merchant_category_diversity"),
            F.sum(F.when(F.col("merchant_category") == "utilities", 1).otherwise(0)).alias(
                "utility_payment_count"
            ),
            F.sum(F.when(F.col("is_international") == 1, 1).otherwise(0)).alias(
                "international_txn_count"
            ),
            F.max("transaction_at").alias("last_transaction_at"),
        )
        .withColumn(
            "avg_txn_amount",
            F.when(F.col("txn_count_90d") > 0, F.col("spend_outflow_90d") / F.col("txn_count_90d")).otherwise(
                F.lit(0.0)
            ),
        )
        .withColumn(
            "net_cash_flow_90d",
            F.col("income_inflow_90d") - F.col("spend_outflow_90d"),
        )
    )

    silver = (
        apps.select(
            "application_id",
            "customer_id",
            "applied_at",
            "monthly_income",
            "utility_on_time_pct",
            "cash_flow_stability_score",
        )
        .join(txn_features, on=["application_id", "customer_id"], how="left")
        .fillna(
            {
                "txn_count_90d": 0,
                "income_inflow_90d": 0.0,
                "spend_outflow_90d": 0.0,
                "merchant_category_diversity": 0,
                "utility_payment_count": 0,
                "international_txn_count": 0,
                "avg_txn_amount": 0.0,
                "net_cash_flow_90d": 0.0,
            }
        )
        .withColumn(
            "income_to_spend_ratio",
            F.when(
                F.col("spend_outflow_90d") > 0,
                F.col("income_inflow_90d") / F.col("spend_outflow_90d"),
            ).otherwise(F.lit(0.0)),
        )
        .withColumn("feature_created_at", F.current_timestamp())
    )

    target = write_table(
        silver, args.catalog, args.database, "customer_behavior_30d", warehouse
    )
    print(f"Silver table refreshed: {target} ({silver.count()} rows)")


if __name__ == "__main__":
    main()
