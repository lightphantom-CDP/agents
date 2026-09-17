"""Catalog naming helpers for CDE (hive) and CAI (spark_catalog)."""

from __future__ import annotations

import os
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

# CAI and some Data Hub sessions use spark_catalog with database.table names.
TWO_PART_CATALOGS = {"spark_catalog", "spark", ""}
DEFAULT_LOCAL_WAREHOUSE = "file:///home/cdsw/credit_demo_warehouse"


def is_local_warehouse(path: str | None) -> bool:
    return bool(path and path.startswith("file:"))


def build_spark(app_name: str, warehouse: str | None = None) -> SparkSession:
    """Use local Spark mode for file:// warehouses so YARN executors are not required."""
    builder = SparkSession.builder.appName(app_name).enableHiveSupport()
    if is_local_warehouse(warehouse):
        builder = builder.master("local[*]")
    return builder.getOrCreate()


def uses_two_part_names(catalog: str) -> bool:
    return catalog in TWO_PART_CATALOGS


def fq_table(catalog: str, database: str, table: str) -> str:
    if uses_two_part_names(catalog):
        return f"{database}.{table}"
    return f"{catalog}.{database}.{table}"


def warehouse_path(catalog: str, override: str | None = None) -> str | None:
    if override:
        return override.rstrip("/")
    if uses_two_part_names(catalog):
        return os.getenv("CREDIT_WAREHOUSE_PATH", DEFAULT_LOCAL_WAREHOUSE).rstrip("/")
    return None


def table_path(base: str, database: str, table: str) -> str:
    return f"{base}/{database}/{table}"


def ensure_database(spark: SparkSession, catalog: str, database: str, local_base: str | None) -> None:
    if local_base:
        Path(local_base.replace("file://", "")) / database
        Path(local_base.replace("file://", ""), database).mkdir(parents=True, exist_ok=True)
        return

    if uses_two_part_names(catalog):
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")
        return

    try:
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog}.{database}")
    except Exception:
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")


def read_table(
    spark: SparkSession,
    catalog: str,
    database: str,
    table: str,
    local_base: str | None = None,
) -> DataFrame:
    local_base = local_base or warehouse_path(catalog)
    if local_base:
        path = table_path(local_base, database, table)
        return spark.read.parquet(path)
    return spark.table(fq_table(catalog, database, table))


def write_table(
    df: DataFrame,
    catalog: str,
    database: str,
    table: str,
    local_base: str | None = None,
) -> str:
    spark = df.sparkSession
    local_base = local_base or warehouse_path(catalog)
    table_ref = fq_table(catalog, database, table)

    if local_base:
        path = table_path(local_base, database, table)
        ensure_database(spark, catalog, database, local_base)
        df.write.mode("overwrite").parquet(path)
        return path

    spark.sql(f"DROP TABLE IF EXISTS {table_ref}")
    (
        df.writeTo(table_ref)
        .using("iceberg")
        .tableProperty("format-version", "2")
        .createOrReplace()
    )
    return table_ref
