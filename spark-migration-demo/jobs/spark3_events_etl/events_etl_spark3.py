#!/usr/bin/env python3
"""
Spark 3 demo job — events enrichment, window ranking, daily aggregates.

CDE: deploy on Spark 3 virtual cluster.
Agent demo: this file is the "before" artifact for Spark 3 → 4 conversion.

Usage (local or CDE arguments):
  --output /tmp/spark3_events_out
  --seed 42
"""
from __future__ import annotations

import argparse
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Spark 3 events ETL demo")
    p.add_argument(
        "--output",
        default="",
        help="Output directory (parquet). Leave blank on CDE to skip write and only print counts. Example: s3a://bucket/demo/spark3_out",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed for synthetic data")
    return p.parse_args(argv)


def build_spark() -> SparkSession:
    # No enableHiveSupport — not required for this demo; avoids metastore errors on some VCs.
    return SparkSession.builder.appName("spark3_events_etl").getOrCreate()


def synthetic_events(spark: SparkSession, seed: int):
    """Small in-memory dataset — no external input file required for first run."""
    spark.sparkContext.setJobGroup("seed", "Create synthetic events")
    rows = []
    customers = [("C001", "North"), ("C002", "South"), ("C003", "North")]
    cust_df = spark.createDataFrame(customers, ["customer_id", "region"])

    for i in range(200):
        cid = customers[i % 3][0]
        day = "2025-09-%02d" % (1 + (i % 28))
        amount = round(10.0 + (i % 17) * 3.25, 2)
        status = "OK" if i % 11 else "REVIEW"
        rows.append((f"E{i:05d}", cid, day, str(amount), status))

    events_df = spark.createDataFrame(
        rows, ["event_id", "customer_id", "event_date", "amount_str", "status"]
    )
    return events_df, cust_df


def transform(events_df, cust_df):
    # Spark 3 style: cast via string column (agent may suggest explicit try_cast for Spark 4 / ANSI)
    enriched = (
        events_df.join(cust_df, "customer_id", "left")
        .withColumn("amount", F.col("amount_str").cast("double"))
        .withColumn(
            "event_rank",
            F.row_number().over(
                Window.partitionBy("customer_id").orderBy(F.col("amount").desc())
            ),
        )
        .filter(F.col("status") != "REVIEW")
    )

    daily = (
        enriched.groupBy("event_date", "region")
        .agg(
            F.count("event_id").alias("event_count"),
            F.round(F.sum("amount"), 2).alias("total_amount"),
            F.max("amount").alias("max_amount"),
        )
        .orderBy("event_date", "region")
    )
    return enriched, daily


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    spark = build_spark()
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    # Common Spark 3 cluster default; note in migration reviews
    spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")

    events_df, cust_df = synthetic_events(spark, args.seed)
    enriched, daily = transform(events_df, cust_df)

    n_enriched = enriched.count()
    n_daily = daily.count()

    out = (args.output or "").strip().rstrip("/")
    if out:
        enriched.coalesce(1).write.mode("overwrite").parquet(f"{out}/enriched")
        daily.coalesce(1).write.mode("overwrite").parquet(f"{out}/daily_by_region")
        print(
            f"spark3_events_etl OK enriched_rows={n_enriched} daily_rows={n_daily} output={out}"
        )
    else:
        print(
            f"spark3_events_etl OK enriched_rows={n_enriched} daily_rows={n_daily} output=SKIPPED (set --output for parquet)"
        )
    spark.stop()


if __name__ == "__main__":
    main()
