"""
Export features table to S3 parquet for offline scoring in CAI.

CDE Job parameters:
  --db workshop_credit_user_xx
  --output s3a://<bucket>/workshop/credit_scoring/scoring/<user>/features
"""

import argparse
import sys

from pyspark.sql import SparkSession


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--output", required=True, help="s3a:// path for parquet output")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f">>> EXPORT features db={args.db} output={args.output} <<<", flush=True)
    spark = SparkSession.builder.appName("credit-04-export-features").getOrCreate()
    df = spark.table(f"{args.db}.features")
    n = df.count()
    print(f"features rows: {n}", flush=True)
    df.write.mode("overwrite").parquet(args.output)
    print(f"SUCCESS: exported {n} rows to {args.output}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
