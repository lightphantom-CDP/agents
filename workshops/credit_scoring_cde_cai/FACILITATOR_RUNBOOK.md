# Facilitator Runbook — Credit Scoring Workshop (CDE + CAI)

## Pre-workshop timeline

| When | Task |
|------|------|
| T-7 days | Send participant prerequisites email |
| T-5 days | Download Kaggle dataset, upload to landing zone |
| T-3 days | Run golden path end-to-end |
| T-1 day | Create user accounts, test logins |
| T-0 morning | Run DAG once, verify scores table, reset if needed |

---

## Environment setup (detailed)

### 1. CDE virtual cluster

```
Name: workshop-vc-01
Type: All Purpose - Tier 2 (for sessions + jobs)
Spark version: Latest supported with Iceberg
Executors: min 2, max 8
```

### 2. CAI project

```
Project: credit-scoring-workshop
Runtime: Python 3.10
Engine: Spark optional (enable Spark data connection to Iceberg)
Resource: 2 CPU, 8 GiB per session
```

Add to project **requirements.txt**:
```
xgboost>=2.0
scikit-learn>=1.3
mlflow
requests
shap
```

### 3. Create database and Ranger policies

Run as admin or in CDE session:

```sql
CREATE DATABASE IF NOT EXISTS workshop_credit;
```

Ranger policies (minimum):

| Policy | Table | Groups |
|--------|-------|--------|
| workshop-credit-read | `workshop_credit.*` | workshop-participants (select) |
| workshop-credit-write | `workshop_credit.*` | workshop-participants (insert, update, create) |

### 4. Upload workshop assets to CDE

**CSV → S3** (data only):

```
s3://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing/cs-training.csv
```

**Python scripts → CDE Resources** folder `workshop-credit/` (not S3 application path):

- `labs/00_test_hello.py` — run first to confirm Python executes
- `labs/01_ingest_raw.py`
- `labs/02_build_features.py`
- `labs/03_data_quality.py`
- `labs/04_batch_score.py`

> **Facilitator note:** If a job log shows `PythonRunner s3a://.../*.py` and exits in ~30s with no `HELLO` / `LOADED` / `SUCCESS` lines, the job is pointed at S3 for the script. Fix: Application file = **Resource**.

### 5. Pre-create CDE jobs

| Job name | Script (Resource path) | Parameters |
|----------|------------------------|------------|
| `credit-00-hello` | `00_test_hello.py` | *(none)* |
| `credit-01-ingest-raw` | `01_ingest_raw.py` | `--db workshop_credit --landing s3a://...` |
| `credit-02-build-features` | `02_build_features.py` | `--db workshop_credit` |
| `credit-03-data-quality` | `03_data_quality.py` | `--db workshop_credit` |
| `credit-04-batch-score` | `04_batch_score.py` | `--db workshop_credit --model-url <URL>` |

### 6. Deploy Airflow DAG

Set variables in CDE Airflow:

```bash
workshop_db = workshop_credit
landing_path = s3a://your-bucket/workshop/credit_scoring/landing
cde_vc_name = workshop-vc-01
```

Enable DAG `credit_scoring_pipeline`.

### 7. Golden path (facilitator private run)

Execute in order:

1. `credit-01-ingest-raw` → ~150k rows
2. `credit-02-build-features` → features table + note snapshot ID
3. CAI: run `04_train_credit_model.py` → AUC > 0.84
4. Register + deploy `credit_default_model`
5. `credit-04-batch-score` → scores table populated
6. Trigger full Airflow DAG → all green

Record timings for each step (use in agenda).

---

## Demo script — opening (15 min)

**Slide 1–3:** Customer pain — siloed data, notebook models, no audit trail.

**Slide 4:** Architecture diagram (from README).

**Slide 5:** Live CDE — show virtual cluster, one completed job run.

**Say:** "Everything you'll build today runs in your tenant — not a slide-ware demo."

---

## Demo script — CDE module (45 min)

### Beat 1: Session exploration (10 min)

1. Open CDE Session.
2. `spark.table("workshop_credit.raw_applications").groupBy("default_flag").count().show()`
3. Point out Iceberg — no extra config.

### Beat 2: Feature job (15 min)

1. Show `02_build_features.py` in editor (don't live-code from scratch).
2. Run job `credit-02-build-features`.
3. Show Spark UI link briefly — executors scaling.

### Beat 3: Airflow (15 min)

1. Open Airflow Graph view.
2. Trigger `credit_scoring_pipeline`.
3. Narrate each task: ingest → quality → features.
4. Show `quality_log` table on success.

### Beat 4: Iceberg time travel (5 min)

```python
spark.sql("SELECT * FROM workshop_credit.features.history").show(5)
```

**Key message:** "CAI will train on snapshot X — fully reproducible."

---

## Demo script — CAI module (45 min)

### Beat 1: EDA (10 min)

Open CAI, show feature distributions and class imbalance.

### Beat 2: MLflow training (20 min)

1. Run training script (pre-executed cells or live).
2. Open Experiments — compare 3 runs.
3. Log `features_snapshot_id`.

### Beat 3: Deploy + live score (15 min)

1. Deploy model from registry.
2. `curl` one applicant — read probability aloud.
3. Map to risk band A/B/C/D.

**Key message:** "From pipeline to API in one platform — no export to SageMaker."

---

## Demo script — batch scoring finale (15 min)

1. Run `credit-04-batch-score` or trigger DAG with score task.
2. Query top 10 riskiest applicants.
3. Open Lab 7 SHAP output for applicant #1.
4. Show `model_version` in scores table.

**Closing:** Recap CDE owns data + orchestration, CAI owns model lifecycle, Iceberg is the contract.

---

## Participant email template (T-7 days)

```
Subject: Credit Scoring Workshop — Prerequisites

Hi team,

Join us for a hands-on Cloudera workshop: Credit Scoring with CDE + CAI.

Please ensure:
- Laptop with browser access to CDP (URL: <CDP_URL>)
- Login credentials (sent separately)
- Basic Python/SQL familiarity

Agenda: ingest → features → train → deploy → batch score

Duration: <1-day or 2-day>
Location: <room / virtual link>

See you there,
<Your name>
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Permission denied on table | Ranger | Add user to workshop-participants group |
| Job exits ~30s, no Python output | `.py` on S3 as app file | Use CDE **Resource** for scripts; S3 only for CSV |
| Ingest 0 rows | Wrong landing path | Verify s3a path and file name |
| AUC very low (~0.50) | Wrong feature order | Check FEATURE_COLS match training |
| API connection refused from CDE | Network policy | Allow CDE → CAI endpoint in firewall |
| Airflow task failed | Upstream job failed | Check CDE job logs from Airflow task log link |
| SHAP slow | Large sample | Use `shap.sample(X, 500)` |

---

## Room logistics

- 1 projector for facilitator demo
- Participants work in **pairs** (DE + DS)
- 1 TA per 8 participants
- Shared Slack/Teams channel for questions
- Backup: pre-recorded 10-min golden path video

---

## Success metrics (post-workshop survey)

1. I understand how CDE and CAI work together. (1–5)
2. I could adapt this pattern to our use case. (1–5)
3. I want a follow-on PoC. (Y/N)

Target: average ≥ 4.0 on questions 1–2.
