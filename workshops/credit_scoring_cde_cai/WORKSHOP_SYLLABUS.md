# Workshop Syllabus — Credit Scoring with CDE + CAI

**For:** Team approval, customer invites, scheduling  
**Format:** Technical demo + optional hands-on  
**Platform:** Cloudera Cloud (CDE + CAI)

---

## Title

**Intelligent Credit Decisioning with Cloudera Data Engineering and Cloudera AI**

---

## Objective

Show how Cloudera Cloud delivers **speed** and **enterprise quality** for credit risk AI:

- **CDE:** Ingest and feature-engineer data with serverless Spark → **Iceberg tables on S3**
- **CAI:** Train, track, and deploy a model with MLflow → **scoring API**
- **Together:** Batch score applicants without exporting data or managing separate platforms

---

## Audience

- Data engineers
- Data scientists / ML engineers
- Solution architects
- Optional: business stakeholders (demo portion only)

---

## Duration options

| Format | Length | Description |
|--------|--------|-------------|
| **Speed demo** | 30–45 min | Facilitator-led; show CDE → CAI → scores |
| **Technical workshop** | 4–6 hours | Jobs-only hands-on (no CDE Sessions required) |
| **Deep dive** | 2 days | Full build + customer PoC discussion |

---

## Prerequisites

- Cloudera Cloud environment with **CDE** and **CAI** enabled
- Sample CSV in S3 (`cs-training.csv`, ~40,000 rows, ~2 MB)
- CDE virtual cluster (Jobs supported; Sessions optional)
- CAI project with Python runtime
- Basic Python/SQL familiarity (hands-on track)

---

## Architecture summary

See [docs/ARCHITECTURE_ONE_PAGER.md](docs/ARCHITECTURE_ONE_PAGER.md) for diagram.

**Flow:** S3 CSV → CDE ingest → Iceberg → CDE features → CAI train/deploy → CDE batch score → Iceberg scores

---

## Iceberg tables created

| Table | Created by | Workshop step |
|-------|------------|---------------|
| `workshop_credit.raw_applications` | CDE ingest job | Required |
| `workshop_credit.features` | CDE features job | Required |
| `workshop_credit.scores` | CDE batch score job | Required |
| `workshop_credit.connectivity_test` | Optional validate job | Smoke test only |

**We create 3 Iceberg tables in the main workshop** (plus 1 optional test table).

We do **not** require Hive, Impala, or Data Warehouse in the workshop — CDE Spark creates Iceberg tables using the CDP catalog automatically.

---

## Agenda (Jobs-only, no Airflow)

| Module | Topic | Service | Time |
|--------|-------|---------|------|
| 0 | Intro + architecture | Slides | 20 min |
| 1 | Optional: validate CDE + Iceberg | CDE Job | 15 min |
| 2 | Ingest CSV from S3 | CDE Job | 45 min |
| 3 | Feature engineering | CDE Job | 60 min |
| 4 | Train model + MLflow | CAI notebook | 75 min |
| 5 | Deploy scoring API | CAI | 45 min |
| 6 | Batch scoring | CDE Job | 60 min |
| 7 | Governance overview | Discussion | 30 min |

---

## Learning outcomes

Participants will be able to:

1. Explain how CDE and CAI share data via **Iceberg**
2. Run **CDE Spark jobs** for ingest, features, and batch scoring
3. Train and register a model in **CAI** with **MLflow**
4. Deploy a **REST scoring API** and call it from CDE
5. Describe governance and production next steps

---

## Materials

| Asset | Location |
|-------|----------|
| Sample CSV | `data/cs-training.csv` |
| Participant steps | `PARTICIPANT_GUIDE.md` |
| Facilitator setup | `FACILITATOR_RUNBOOK.md` |
| Architecture slide | `docs/ARCHITECTURE_ONE_PAGER.md` |
| CDE scripts | `labs/01_ingest_raw.py`, `02_build_features.py`, `04_batch_score.py` |
| CAI scripts | `labs/cai/04_train_credit_model.py`, etc. |

---

## Deliverables (end of workshop)

- 3 Iceberg tables populated on S3
- Registered model in MLflow
- Deployed scoring API
- Batch-scored portfolio with risk bands
- Reference architecture for customer PoC

---

## Demo message (elevator pitch)

> On Cloudera Cloud, we go from raw credit data in S3 to a deployed scoring model and batch-scored portfolio — using **CDE** for data pipelines and **CAI** for ML — all on **governed Iceberg tables**, with no data export and no cluster babysitting.
