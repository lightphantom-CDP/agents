#!/usr/bin/env python3
"""
CDE Job 01 — Ingest raw applications and transactions into Bronze Iceberg tables.

CAI Workbench example (local CSV + local warehouse, no S3 needed):
  python3 01_ingest_bronze.py --catalog spark_catalog --database credit_demo \
    --raw-base-path file:///home/cdsw/data \
    --warehouse-path file:///home/cdsw/credit_demo_warehouse
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from catalog_utils import build_spark, ensure_database, write_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest credit demo bronze tables")
    parser.add_argument(
        "--catalog",
        default=os.getenv("CREDIT_CATALOG", "spark_catalog"),
    )
    parser.add_argument("--database", default=os.getenv("CREDIT_DATABASE", "credit_demo"))
    parser.add_argument(
        "--raw-base-path",
        default=os.getenv("RAW_BASE_PATH", "s3a://changeme/credit-demo/raw"),
    )
    parser.add_argument(
        "--warehouse-path",
        default=os.getenv("CREDIT_WAREHOUSE_PATH", ""),
    )
    return parser.parse_known_args()[0]


def main() -> None:
    args = parse_args()
    warehouse = args.warehouse_path or None
    spark = build_spark("credit_demo_01_ingest_bronze", warehouse)
    ensure_database(spark, args.catalog, args.database, warehouse)

    applications_path = f"{args.raw_base_path}/applications.csv"
    transactions_path = f"{args.raw_base_path}/transactions.csv"

    applications = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(applications_path)
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_file", F.lit(applications_path))
    )

    transactions = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(transactions_path)
        .withColumn("ingested_at", F.current_timestamp())
        .withColumn("source_file", F.lit(transactions_path))
    )

    apps_target = write_table(
        applications, args.catalog, args.database, "raw_applications", warehouse
    )
    txns_target = write_table(
        transactions, args.catalog, args.database, "raw_transactions", warehouse
    )

    app_count = applications.count()
    txn_count = transactions.count()
    print(f"Bronze tables refreshed: {apps_target} ({app_count} rows)")
    print(f"Bronze tables refreshed: {txns_target} ({txn_count} rows)")


if __name__ == "__main__":
    main()
