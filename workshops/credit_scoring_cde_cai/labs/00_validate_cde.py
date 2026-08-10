"""
Optional smoke test — credit-00-validate

Confirms CDE Spark can create and read Iceberg tables.
Skip this job if credit-01-ingest-raw already works.

CDE Job: no arguments required (optional: --db workshop_credit)
"""

import argparse
from pyspark.sql import SparkSession


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="workshop_credit")
    return parser.parse_args()


def main():
    args = parse_args()
    spark = SparkSession.builder.appName("credit-00-validate").getOrCreate()

    spark.sql(f"CREATE DATABASE IF NOT EXISTS {args.db}")

    table = f"{args.db}.connectivity_test"
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            user_name STRING,
            tested_at TIMESTAMP
        ) USING iceberg
    """)
    spark.sql(f"""
        INSERT INTO {table}
        VALUES ('validation_job', current_timestamp())
    """)

    spark.table(table).show()
    print("SUCCESS: CDE + Iceberg working")


if __name__ == "__main__":
    main()
