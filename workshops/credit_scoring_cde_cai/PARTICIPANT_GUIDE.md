# Credit Scoring Workshop — Participant Guide

Detailed step-by-step instructions for every lab. Work in order.

**Before you start:** Replace these placeholders everywhere:

| Placeholder | Your value (example) |
|-------------|----------------------|
| `<CDE_VC_NAME>` | `workshop-vc-01` |
| `<CAI_PROJECT>` | `credit-scoring-workshop` |
| `<WORKSHOP_DB>` | `workshop_credit` |
| `<LANDING_PATH>` | `s3a://datalake/workshop/credit_scoring/landing` |
| `<YOUR_USER>` | your CDP username |

---

## Lab 0 — Validate your environment

**Goal:** Confirm CDE and CAI can read/write the same Iceberg catalog.

**Time:** 30 minutes

### Step 0.1 — Log in to CDP

1. Open your CDP console URL (provided by facilitator).
2. Confirm you see **Data Engineering** and **Machine Learning / AI** in the left menu.
3. Note your environment name: ___________________

### Step 0.2 — Open CDE

1. Go to **Data Engineering** → **Overview**.
2. Click your virtual cluster: `<CDE_VC_NAME>`.
3. Click **Create Session** (or use facilitator-provided session).
4. Name: `lab0-<YOUR_USER>`
5. Wait until status = **Running**.

### Step 0.3 — Test Spark + Iceberg in CDE

In the CDE Session editor, run:

```python
spark.sql(f"CREATE DATABASE IF NOT EXISTS <WORKSHOP_DB>")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS <WORKSHOP_DB>.connectivity_test (
  user_name STRING,
  tested_at TIMESTAMP
) USING iceberg
""")
spark.sql(f"""
INSERT INTO <WORKSHOP_DB>.connectivity_test
VALUES ('<YOUR_USER>', current_timestamp())
""")
spark.table("<WORKSHOP_DB>.connectivity_test").show()
```

**Expected:** One row with your username and a timestamp.

### Step 0.4 — Open CAI Workbench

1. Go to **Machine Learning** (Cloudera AI).
2. Open project: `<CAI_PROJECT>`.
3. **New Session** → Runtime: Python 3.10 → Start.
4. If Spark is enabled, run the same `spark.table(...).show()` query.

**Expected:** Same row visible from CAI.

### Step 0.5 — Checklist

- [ ] CDE session runs without error
- [ ] CAI session runs without error
- [ ] Both see `connectivity_test` table
- [ ] You can open JupyterLab / Workbench editor

✅ **Lab 0 complete.** Tell facilitator if any step fails.

---

## Lab 1 — Ingest raw credit data (CDE)

**Goal:** Load the Give Me Some Credit CSV into Iceberg table `raw_applications`.

**Time:** 45 minutes

### Step 1.1 — Verify landing data

Ask facilitator for landing path. In CDE Session:

```python
# List files (adjust path)
df = spark.read.csv("<LANDING_PATH>/cs-training.csv", header=True, inferSchema=True)
print(f"Rows: {df.count()}, Columns: {len(df.columns)}")
df.printSchema()
df.show(5)
```

**Expected:** ~150,000 rows, 12 columns, label column `SeriousDlqin2yrs`.

### Step 1.2 — Create CDE Job for ingest

1. In CDE UI → **Jobs** → **Create Job**.
2. Settings:
   - **Name:** `credit-01-ingest-raw`
   - **Type:** Spark
   - **Script:** Upload `labs/01_ingest_raw.py`
   - **Parameters:** `--db <WORKSHOP_DB> --landing <LANDING_PATH>`
3. **Resources:** 2 executors, 4g memory (facilitator may adjust).
4. Click **Create**.

### Step 1.3 — Run the job

1. Click **Run** on job `credit-01-ingest-raw`.
2. Open **Run Details** → watch logs.
3. Wait for status **Succeeded**.

### Step 1.4 — Validate in CDE Session

```python
raw = spark.table("<WORKSHOP_DB>.raw_applications")
print("Count:", raw.count())
raw.groupBy("default_flag").count().show()
raw.printSchema()
```

**Expected:**
- Row count matches source CSV
- `default_flag` has values 0 and 1
- `ingested_at` column populated

### Step 1.5 — Discussion questions

1. Why store raw data in Iceberg instead of keeping only CSV?
2. What governance policies (Ranger) should apply to PII columns?

✅ **Lab 1 complete.**

---

## Lab 2 — Feature engineering (CDE)

**Goal:** Transform raw data into model-ready features in `features` table.

**Time:** 60 minutes

### Step 2.1 — Review feature logic

Open `labs/02_build_features.py`. Key transformations:

| Feature | Logic |
|---------|-------|
| `utilization` | Clip utilization to [0, 10] |
| `debt_ratio` | Clip to [0, 100] |
| `age` | Clip to [18, 100] |
| `delinq_total` | Sum of 30/60/90 DPD counters |
| `open_credit_lines` | Direct from source |
| `income_missing` | 1 if MonthlyIncome is null |
| `monthly_income` | Impute median when null |
| `default_flag` | Renamed label for modeling |

### Step 2.2 — Run feature job in CDE Session (dev test)

Paste the core logic from `02_build_features.py` into your session and run on a sample:

```python
raw = spark.table("<WORKSHOP_DB>.raw_applications")
sample = raw.limit(1000)
# ... paste feature transforms from lab script ...
sample.select("applicant_id", "utilization", "default_flag").show(10)
```

Fix any errors before creating the production job.

### Step 2.3 — Create CDE Job

1. **Jobs** → **Create Job**
2. **Name:** `credit-02-build-features`
3. **Script:** `labs/02_build_features.py`
4. **Parameters:** `--db <WORKSHOP_DB>`
5. **Run** the job.

### Step 2.4 — Validate features

```python
feat = spark.table("<WORKSHOP_DB>.features")
feat.printSchema()
feat.describe("utilization", "debt_ratio", "age", "delinq_total").show()
feat.groupBy("default_flag").count().show()
```

**Expected:** ~6–7% positive class (defaults) — typical for this dataset.

### Step 2.5 — Hands-on challenge (optional)

In `02_build_features.py`, add a new feature:

```python
.withColumn("high_utilization_flag", F.when(F.col("utilization") > 0.75, 1).otherwise(0))
```

Re-run job and confirm column exists.

### Step 2.6 — Log Iceberg snapshot ID

```python
snap = spark.sql(f"SELECT snapshot_id, committed_at FROM <WORKSHOP_DB>.features.snapshots ORDER BY committed_at DESC LIMIT 1")
snap.show(truncate=False)
```

**Save this snapshot ID** — you will log it in MLflow during Lab 4.

✅ **Lab 2 complete.**

---

## Lab 3 — Orchestrate with Airflow (CDE)

**Goal:** Chain ingest → quality checks → features in one DAG.

**Time:** 45 minutes

### Step 3.1 — Review data quality job

Open `labs/03_data_quality.py`. It checks:

- No null `applicant_id`
- `default_flag` in (0, 1)
- Row count > 100,000
- Default rate between 1% and 20%

Failures write to `quality_log` and raise an error to stop the DAG.

### Step 3.2 — Upload Airflow DAG

1. In CDE → **Airflow** → **DAGs**.
2. Upload `labs/airflow_credit_scoring_dag.py` as a resource (or use facilitator pre-deployed DAG).
3. Set Airflow Variables (facilitator provides):
   - `workshop_db` = `<WORKSHOP_DB>`
   - `landing_path` = `<LANDING_PATH>`
   - `cde_vc_name` = `<CDE_VC_NAME>`

### Step 3.3 — DAG structure

```
ingest_raw → data_quality → build_features → [end]
```

### Step 3.4 — Trigger the DAG

1. Enable DAG: `credit_scoring_pipeline`
2. Click **Trigger DAG** (play button).
3. Open **Graph** view and watch task colors turn green.

### Step 3.5 — Verify pipeline output

```python
spark.sql(f"SELECT * FROM <WORKSHOP_DB>.quality_log ORDER BY checked_at DESC LIMIT 5").show(truncate=False)
spark.table("<WORKSHOP_DB>.features").count()
```

### Step 3.6 — Discussion

- How would you schedule this nightly?
- Where would you add email alerts on `data_quality` failure?

✅ **Lab 3 complete.**

---

## Lab 4 — Train a credit model (CAI)

**Goal:** Train XGBoost classifier, track with MLflow, register best model.

**Time:** 75 minutes

### Step 4.1 — Open CAI and create session

1. **Cloudera AI** → Project `<CAI_PROJECT>`
2. Upload `labs/cai/04_train_credit_model.py` to project files (or open provided notebook).
3. **New Session** — enable Spark if reading Iceberg via Spark connection.
4. Install runtime dependency if needed:
   ```bash
   pip install xgboost scikit-learn
   ```

### Step 4.2 — Connect to feature table

In CAI Workbench, run the data load section from `04_train_credit_model.py`:

```python
# Via Spark (recommended)
features_df = spark.table("<WORKSHOP_DB>.features").toPandas()
```

Or use CAI Data Connection configured by facilitator.

### Step 4.3 — Train / validation split

**Important:** Use random split for workshop speed. In production, use **time-based split**.

```python
from sklearn.model_selection import train_test_split

FEATURE_COLS = [
    "utilization", "age", "debt_ratio", "delinq_total",
    "open_credit_lines", "real_estate_loans", "dependents",
    "income_missing", "monthly_income", "high_utilization_flag",
]
X = features_df[FEATURE_COLS]
y = features_df["default_flag"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
```

### Step 4.4 — Train with MLflow

Run the training block in `04_train_credit_model.py`.

**Expected MLflow metrics:**
- `auc` ≈ 0.85–0.87
- `ks` ≈ 0.35–0.45
- `gini` ≈ 0.70–0.74

### Step 4.5 — Log Iceberg snapshot ID

```python
import mlflow
mlflow.log_param("features_snapshot_id", "<SNAPSHOT_ID_FROM_LAB_2>")
mlflow.log_param("features_table", "<WORKSHOP_DB>.features")
```

### Step 4.6 — Compare runs

1. CAI → **Experiments** → open experiment `credit_default_prediction`
2. Sort by `auc` descending
3. Select best run → **Register Model** → name: `credit_default_model`

### Step 4.7 — Hands-on challenge

Change `max_depth` from 4 to 6, re-run training, compare AUC in MLflow.

✅ **Lab 4 complete.**

---

## Lab 5 — Deploy model (CAI)

**Goal:** Deploy registered model as REST API and score one applicant.

**Time:** 45 minutes

### Step 5.1 — Promote model version

1. **Model Registry** → `credit_default_model`
2. Select best version → **Deploy** → **New Model Deployment**
3. Name: `credit-scoring-api`
4. Wait until status = **Deployed**

### Step 5.2 — Test with curl

Facilitator provides API URL and auth token.

```bash
curl -X POST "https://<CAI_MODEL_URL>/model/credit-scoring-api/infer" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [[0.35, 45, 0.25, 1, 8, 2, 1, 0, 5500.0, 0]]
  }'
```

**Expected response:** probability of default (float 0–1).

### Step 5.3 — Test from Python

Run `labs/cai/05_deploy_and_test.py` in CAI session.

### Step 5.4 — Risk bands

| Probability | Band |
|-------------|------|
| < 0.10 | A — Low risk |
| 0.10 – 0.20 | B — Medium |
| 0.20 – 0.35 | C — High |
| ≥ 0.35 | D — Very high |

✅ **Lab 5 complete.**

---

## Lab 6 — Batch scoring (CDE)

**Goal:** Score all applicants via CDE job calling CAI model API.

**Time:** 60 minutes

### Step 6.1 — Configure job parameters

Create CDE job `credit-04-batch-score` with script `labs/04_batch_score.py`.

**Environment variables / parameters:**

| Parameter | Value |
|-----------|-------|
| `--db` | `<WORKSHOP_DB>` |
| `--model-url` | CAI deployment URL |
| `--model-version` | e.g. `1` |

### Step 6.2 — Run batch scoring

1. Run job manually first.
2. Check logs for rows scored and any API errors.

### Step 6.3 — Validate scores table

```python
scores = spark.table("<WORKSHOP_DB>.scores")
scores.printSchema()
scores.groupBy("risk_band").count().orderBy("risk_band").show()
scores.orderBy(F.desc("probability_default")).show(10)
```

**Expected columns:**
- `applicant_id`
- `probability_default`
- `risk_band`
- `model_name`
- `model_version`
- `scored_at`

### Step 6.4 — Add scoring to Airflow DAG

Extend DAG with task: `build_features >> batch_score`

Trigger full pipeline and confirm `scores` refreshes.

### Step 6.5 — Capstone check

You should now have:

```
raw_applications → features → scores
                      ↑
                 CAI model API
```

✅ **Lab 6 complete.**

---

## Lab 7 — Governance & explainability (CAI)

**Goal:** Generate reason codes for one applicant using SHAP.

**Time:** 30 minutes

### Step 7.1 — Run explainability script

Open `labs/cai/06_explainability.py` in CAI.

### Step 7.2 — Interpret output

Example adverse-action style output:

```
Applicant ID: 12345
Probability of default: 0.31 (Risk band: C)
Top contributing factors:
  1. utilization (+0.08)
  2. delinq_total (+0.05)
  3. debt_ratio (+0.03)
  4. income_missing (+0.02)
```

### Step 7.3 — Governance discussion (with facilitator)

| Question | Platform answer |
|----------|-----------------|
| Who can read raw PII? | Ranger policy on `raw_applications` |
| Which data trained the model? | MLflow param `features_snapshot_id` |
| Which model version scored this applicant? | `scores.model_version` column |
| Can we reproduce training data? | Iceberg time travel to snapshot ID |

✅ **Workshop complete.**

---

## Quick reference — feature column order for API

When calling the model API, pass features in this order:

```
[utilization, age, debt_ratio, delinq_total, open_credit_lines,
 real_estate_loans, dependents, income_missing, monthly_income,
 high_utilization_flag]
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Table not found` | Check database name and Ranger policy |
| Spark OOM | Reduce data or increase executor memory |
| MLflow run missing | Confirm `mlflow.start_run()` block executed |
| Model API 401 | Refresh CAI API token |
| Batch score timeout | Score in chunks (see `04_batch_score.py`) |

Contact facilitator for environment-specific URLs and credentials.
