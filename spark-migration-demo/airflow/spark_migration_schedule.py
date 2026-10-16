"""
CDE Airflow DAG — scheduled run of the Spark migration demo jobs.

Runs inside CDE Airflow, so it uses CDE's built-in, pre-authorized connection
(default connection_id "cde_runtime_api"). No workload token / Knox endpoint /
GitHub secrets needed — this is why Airflow is the clean fit for this internal
environment.

Flow:
  (optional) run spark3-events-etl  -> Spark 3 VC   (baseline counts for parity)
             run spark4-events-etl  -> Spark 4 VC   (the agent's converted job)

The Spark jobs must already exist in CDE (created via Job Definition with
Source = Repository -> spark-migration-demo). This DAG triggers them by name.

NOTE on fresh code: a CDE job that uses a Git Repository runs the LAST SYNCED
commit. After the agent pushes new code to GitHub, click "Sync" on the CDE
Repository (Repositories page) so the next scheduled run picks it up.
"""
from __future__ import annotations

import pendulum
from airflow import DAG

# CDE's custom operator (provided inside CDE Airflow runtimes)
from cloudera.cde.operators.cde_operator import CDEJobRunOperator

# ── Schedule (cron, UTC) ──────────────────────────────────────────────
# Examples:  "*/15 * * * *" every 15 min | "0 * * * *" hourly | "0 2 * * *" daily 02:00
SCHEDULE = "0 * * * *"

default_args = {
    "owner": "spark-migration-demo",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=5),
}

with DAG(
    dag_id="spark_migration_schedule",
    description="Scheduled Spark 3 (baseline) + Spark 4 (converted) CDE job runs",
    schedule=SCHEDULE,
    start_date=pendulum.datetime(2026, 10, 15, tz="UTC"),
    catchup=False,
    is_paused_upon_creation=False,
    default_args=default_args,
    tags=["spark-migration", "cde", "demo"],
) as dag:

    # Baseline Spark 3 run (keep for parity comparison; comment out if not needed).
    run_spark3 = CDEJobRunOperator(
        task_id="run_spark3_events_etl",
        job_name="spark3-events-etl",
    )

    # The agent's converted Spark 4 job.
    run_spark4 = CDEJobRunOperator(
        task_id="run_spark4_events_etl",
        job_name="spark4-events-etl",
    )

    run_spark3 >> run_spark4
