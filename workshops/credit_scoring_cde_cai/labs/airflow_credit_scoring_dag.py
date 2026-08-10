"""
CDE Airflow DAG — Credit scoring data pipeline.

Upload to CDE Airflow resources and configure variables:
  workshop_db, landing_path, cde_vc_name

Tasks:
  ingest_raw -> data_quality -> build_features -> batch_score (optional)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.providers.cde.operators.cde_operator import CDEJobOperator

WORKSHOP_DB = Variable.get("workshop_db", default_var="workshop_credit")
LANDING_PATH = Variable.get("landing_path", default_var="s3a://changeme/workshop/credit_scoring/landing")
CDE_VC = Variable.get("cde_vc_name", default_var="workshop-vc-01")
MODEL_URL = Variable.get("cai_model_url", default_var="https://changeme/model/credit-scoring-api/infer")

default_args = {
    "owner": "credit-scoring-workshop",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="credit_scoring_pipeline",
    default_args=default_args,
    description="Ingest, validate, and feature-engineer credit application data",
    schedule_interval=None,  # Manual trigger for workshop; set to "@daily" in production
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["workshop", "credit-scoring"],
) as dag:

    ingest_raw = CDEJobOperator(
        task_id="ingest_raw",
        job_name="credit-01-ingest-raw",
        cde_region_name=CDE_VC,
        job_arguments=[f"--db={WORKSHOP_DB}", f"--landing={LANDING_PATH}"],
    )

    data_quality = CDEJobOperator(
        task_id="data_quality",
        job_name="credit-03-data-quality",
        cde_region_name=CDE_VC,
        job_arguments=[f"--db={WORKSHOP_DB}"],
    )

    build_features = CDEJobOperator(
        task_id="build_features",
        job_name="credit-02-build-features",
        cde_region_name=CDE_VC,
        job_arguments=[f"--db={WORKSHOP_DB}"],
    )

    batch_score = CDEJobOperator(
        task_id="batch_score",
        job_name="credit-04-batch-score",
        cde_region_name=CDE_VC,
        job_arguments=[
            f"--db={WORKSHOP_DB}",
            f"--model-url={MODEL_URL}",
            "--model-name=credit_default_model",
            "--model-version=1",
        ],
    )

    ingest_raw >> data_quality >> build_features >> batch_score
