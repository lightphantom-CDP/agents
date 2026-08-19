"""
Load pre-computed scores parquet into Iceberg scores table.

Use after scoring in CAI (score_in_cai.py) when HTTP API or batch_score_local fail.

CDE Job parameters:
  --db workshop_credit_user_xx
  --input s3a://<bucket>/workshop/credit_scoring/scoring/<user>/scores_out.parquet
"""

import argparse
import sys

from pyspark.sql import SparkSession


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--input", required=True, help="s3a:// path to scores parquet")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f">>> LOAD scores db={args.db} input={args.input} <<<", flush=True)
    spark = SparkSession.builder.appName("credit-04-load-scores").getOrCreate()
    scores = spark.read.parquet(args.input)
    n = scores.count()
    print(f"scores rows read: {n}", flush=True)
    scores.writeTo(f"{args.db}.scores").using("iceberg").option(
        "overwrite-schema", "true"
    ).createOrReplace()
    print(f"SUCCESS: loaded {n} rows into {args.db}.scores", flush=True)
    scores.groupBy("risk_band").count().orderBy("risk_band").show()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
