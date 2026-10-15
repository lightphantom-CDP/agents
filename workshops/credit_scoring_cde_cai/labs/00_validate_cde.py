"""Optional smoke test for CDE + Iceberg. Args: --db=workshop_credit"""

import argparse
import logging
import sys

from pyspark.sql import SparkSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("credit-00-validate")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="workshop_credit")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("Starting validation job for database %s", args.db)

    spark = SparkSession.builder.appName("credit-00-validate").getOrCreate()

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")
    table = f"{args.db}.connectivity_test"
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            user_name STRING,
            tested_at TIMESTAMP
        ) USING iceberg
    """)
    spark.sql(f"INSERT INTO {table} VALUES ('validation_job', current_timestamp())")
    spark.table(table).show()
    logger.info("SUCCESS: CDE + Iceberg working")
    print("SUCCESS: CDE + Iceberg working")


try:
    main()
except Exception:
    logger.exception("VALIDATION JOB FAILED")
    sys.exit(1)
