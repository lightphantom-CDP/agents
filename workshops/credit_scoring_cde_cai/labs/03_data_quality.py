"""
Lab 3 — Data quality checks before feature consumption.

CDE Job parameters:
  --db workshop_credit

Fails the job (raises Exception) if any critical check fails.
"""

import argparse
from datetime import datetime

from pyspark.sql import SparkSession, functions as F


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    return parser.parse_args()


def run_checks(spark, db):
    results = []
    raw = spark.table(f"{db}.raw_applications")
    row_count = raw.count()

    results.append(("row_count_min", row_count > 1000, f"rows={row_count}"))
    results.append(("applicant_id_not_null", raw.filter(F.col("applicant_id").isNull()).count() == 0, "ok"))
    results.append(
        (
            "default_flag_valid",
            raw.filter(~F.col("default_flag").isin(0, 1)).count() == 0,
            "values in (0,1)",
        )
    )

    if row_count > 0:
        default_rate = raw.filter(F.col("default_flag") == 1).count() / row_count
        results.append(
            (
                "default_rate_range",
                0.01 <= default_rate <= 0.25,
                f"rate={default_rate:.4f}",
            )
        )

    return results


def main():
    args = parse_args()
    spark = SparkSession.builder.appName("credit-03-data-quality").getOrCreate()

    checks = run_checks(spark, args.db)
    failed = [c for c in checks if not c[1]]

    log_df = spark.createDataFrame(
        [(name, passed, detail, datetime.utcnow().isoformat()) for name, passed, detail in checks],
        ["check_name", "passed", "detail", "checked_at"],
    )
    log_df.writeTo(f"{args.db}.quality_log").using("iceberg").append()

    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {detail}")

    if failed:
        raise RuntimeError(f"Data quality failed: {[f[0] for f in failed]}")

    print("SUCCESS: all data quality checks passed")


if __name__ == "__main__":
    main()
