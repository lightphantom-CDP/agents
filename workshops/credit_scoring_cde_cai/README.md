# Credit Scoring Workshop — CDE + CAI on Cloudera

Customer hands-on workshop: build an end-to-end **credit default prediction** pipeline using **Cloudera Data Engineering (CDE)** and **Cloudera AI (CAI)** on a shared **Apache Iceberg** lakehouse.

## Use case

Predict whether a loan applicant will become seriously delinquent (90+ days past due) within 24 months, then score new applicants in batch.

## Workshop formats

| Format | Duration | Guide |
|--------|----------|-------|
| **1-day** | ~6.5 hours | [docs/01-day1-agenda.md](docs/01-day1-agenda.md) |
| **2-day** | ~12 hours | [docs/02-day2-agenda.md](docs/02-day2-agenda.md) |

## Start here

1. **Team / stakeholders:** Read [WORKSHOP_SYLLABUS.md](WORKSHOP_SYLLABUS.md) and [docs/ARCHITECTURE_ONE_PAGER.md](docs/ARCHITECTURE_ONE_PAGER.md).
2. **Facilitator:** Read [FACILITATOR_RUNBOOK.md](FACILITATOR_RUNBOOK.md) and complete pre-workshop setup.
3. **Participant:** Read [PARTICIPANT_GUIDE.md](PARTICIPANT_GUIDE.md) and follow labs in order (Jobs-only if Sessions unavailable).

## Lab sequence

| Lab | Topic | Service | Time |
|-----|-------|---------|------|
| [Lab 0](PARTICIPANT_GUIDE.md#lab-0--validate-your-environment) | Environment validation | CDE + CAI | 30 min |
| [Lab 1](PARTICIPANT_GUIDE.md#lab-1--ingest-raw-credit-data-cde) | Ingest raw data | CDE | 45 min |
| [Lab 2](PARTICIPANT_GUIDE.md#lab-2--feature-engineering-cde) | Feature engineering | CDE | 60 min |
| [Lab 3](PARTICIPANT_GUIDE.md#lab-3--orchestrate-with-airflow-cde) | Airflow orchestration | CDE | 45 min |
| [Lab 4](PARTICIPANT_GUIDE.md#lab-4--train-a-credit-model-cai) | Train + MLflow | CAI | 75 min |
| [Lab 5](PARTICIPANT_GUIDE.md#lab-5--deploy-model-cai) | Deploy model API | CAI | 45 min |
| [Lab 6](PARTICIPANT_GUIDE.md#lab-6--batch-scoring-cde) | Batch scoring | CDE | 60 min |
| [Lab 7](PARTICIPANT_GUIDE.md#lab-7--governance--explainability-cai) | SHAP + governance | CAI | 30 min |

## Files in this package

```
workshops/credit_scoring_cde_cai/
├── README.md
├── FACILITATOR_RUNBOOK.md      # Setup + demo script + troubleshooting
├── PARTICIPANT_GUIDE.md        # Detailed step-by-step for every lab
├── labs/
│   ├── 01_ingest_raw.py
│   ├── 02_build_features.py
│   ├── 03_data_quality.py
│   ├── 04_batch_score.py
│   ├── airflow_credit_scoring_dag.py
│   └── cai/
│       ├── 04_train_credit_model.py      # Run in CAI Workbench
│       ├── 05_deploy_and_test.py
│       └── 06_explainability.py
├── sql/
│   └── 00_create_tables.sql
└── data/
    └── DATASET.md              # How to obtain sample data
```

## Dataset

Public dataset: **Give Me Some Credit** (Kaggle). See [data/DATASET.md](data/DATASET.md).

## Prerequisites

- CDE enabled with a virtual cluster
- CAI workspace and project
- Shared Iceberg catalog (Hive Metastore)
- Ranger policies for workshop tables
- Python 3.10+ in CAI; Spark 3.x in CDE

## Official Cloudera references

- [DataServicesLabs](https://github.com/cloudera/DataServicesLabs)
- [CDE Iceberg with PySpark](https://community.cloudera.com/t5/Community-Articles/How-to-Create-an-Iceberg-Table-with-PySpark-in-Cloudera-Data/ta-p/394800)
- [MLflow + Iceberg in CAI](https://community.cloudera.com/t5/Community-Articles/Logging-Iceberg-Metrics-with-MLFlow-Tracking-in-CML/ta-p/385657)
- [MLOps with Cloudera AI](https://community.cloudera.com/t5/Community-Articles/Machine-Learning-Ops-with-Cloudera-AI/ta-p/403841)
