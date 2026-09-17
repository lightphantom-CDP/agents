"""
Airflow DAG for the credit demo medallion pipeline.

Deploy this file as a CDE Airflow job after uploading the Spark scripts to CDE Resources.
Adjust CDE job names and resource paths to match your environment.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    "owner": "credit-demo",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

RESOURCE_BASE = "/home/cde/credit-demo"
CATALOG = "hive"
DATABASE = "credit_demo"
RAW_BASE_PATH = "s3a://changeme/credit-demo/raw"

with DAG(
    dag_id="credit_demo_medallion_pipeline",
    description="Bronze -> Silver -> Gold credit feature pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["credit-demo", "cde", "iceberg"],
) as dag:
    ingest_bronze = SparkSubmitOperator(
        task_id="ingest_bronze",
        application=f"{RESOURCE_BASE}/cde/01_ingest_bronze.py",
        application_args=[
            "--catalog",
            CATALOG,
            "--database",
            DATABASE,
            "--raw-base-path",
            RAW_BASE_PATH,
        ],
        name="credit_demo_01_ingest_bronze",
    )

    build_silver = SparkSubmitOperator(
        task_id="build_silver_features",
        application=f"{RESOURCE_BASE}/cde/02_build_silver_features.py",
        application_args=["--catalog", CATALOG, "--database", DATABASE],
        name="credit_demo_02_build_silver",
    )

    publish_gold = SparkSubmitOperator(
        task_id="publish_gold_features",
        application=f"{RESOURCE_BASE}/cde/03_publish_gold_features.py",
        application_args=[
            "--catalog",
            CATALOG,
            "--database",
            DATABASE,
            "--feature-version",
            "v1",
        ],
        name="credit_demo_03_publish_gold",
    )

    ingest_bronze >> build_silver >> publish_gold
