# Credit Scoring Workshop — Participant Guide

Detailed step-by-step instructions for every lab. Work in order.

**Mode:** **Jobs-only** — CDE Sessions are not required (use CDE Jobs + CAI Workbench).  
**Airflow:** Skipped in this workshop — run jobs manually in sequence.

---

## Workshop environment values

| Setting | Value |
|---------|-------|
| **S3 bucket** | `s3://workshpcloud-buk-5e3a7882` |
| **Landing path (Spark)** | `s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing` |
| **CSV file** | `s3://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing/cs-training.csv` |
| **Database** | `workshop_credit` |
| **CDE cluster** | `workshopcluster` (or name provided by facilitator) |
| **CAI project** | `credit-scoring-workshop` (or name provided by facilitator) |

**Important:** In CDE Spark job arguments, always use **`s3a://`** (not `s3://`).

---

## Iceberg tables created in this workshop

| Table | Created by | Purpose |
|-------|------------|---------|
| `workshop_credit.connectivity_test` | `credit-00-validate` (optional) | Smoke test only |
| `workshop_credit.raw_applications` | `credit-01-ingest-raw` | Raw credit data from CSV |
| `workshop_credit.features` | `credit-02-build-features` | Model-ready features |
| `workshop_credit.scores` | `credit-04-batch-score` | Model predictions |

---

## Job sequence overview

```
Upload CSV to S3
       ↓
credit-00-validate        (optional)
       ↓
credit-01-ingest-raw      → Iceberg: raw_applications
       ↓
credit-02-build-features  → Iceberg: features
       ↓
CAI: train + deploy model
       ↓
credit-04-batch-score     → Iceberg: scores
```

---

## Lab 0 — Validate your environment (Jobs-only)

**Goal:** Confirm CDE can run Spark jobs and create Iceberg tables.

**Time:** 20 minutes

### Step 0.1 — Log in to CDP

1. Open your CDP console URL.
2. Confirm you see **Data Engineering** and **Machine Learning / AI** in the left menu.

### Step 0.2 — Upload CSV to S3 (facilitator may do this once for all)

Upload `cs-training.csv` (~40,000 rows) to:

```
s3://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing/cs-training.csv
```

**AWS CLI example:**
```bash
aws s3 cp cs-training.csv s3://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing/cs-training.csv
```

Verify in S3 console that the file exists.

### Step 0.3 — Optional: validate CDE + Iceberg (CDE Job)

If you **do not** have CDE Sessions, use job `credit-00-validate` instead.

1. CDE → **Jobs** → **Create Job**
2. Fill in:

| Field | Value |
|-------|-------|
| Job Type | **Spark** |
| Name | `credit-00-validate` |
| Application Files | Upload `labs/00_validate_cde.py` |
| Main Class | *(leave empty for Python)* |
| Arguments | `--db workshop_credit` |

3. Click **Create** → **Run**
4. Open **Job Runs** → logs should show:

```
SUCCESS: CDE + Iceberg working
```

**Skip this job** if you prefer — go straight to Lab 1 ingest.

### Step 0.4 — Open CAI Workbench

1. Go to **Cloudera AI** → project `credit-scoring-workshop`
2. **New Session** → Python 3.10 → Start
3. Confirm you can open the editor (used starting in Lab 4)

### Step 0.5 — Checklist

- [ ] CSV exists in S3 landing path
- [ ] CDE job runs successfully (validate or ingest)
- [ ] CAI session starts
- [ ] You can open **Jobs** and **Job Runs** in CDE

✅ **Lab 0 complete.**

---

## Lab 1 — Ingest raw credit data (CDE Job)

**Goal:** Load CSV from S3 into Iceberg table `workshop_credit.raw_applications`.

**Time:** 45 minutes

### Step 1.1 — Confirm landing data in S3

File must exist at:

```
s3://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing/cs-training.csv
```

Expected: **~40,000 rows**, 12 columns, label column `SeriousDlqin2yrs`.

### Step 1.2 — Create CDE Job for ingest

1. CDE → **Jobs** → **Create Job**
2. Fill in:

| Field | Value |
|-------|-------|
| Job Type | **Spark** |
| Name | `credit-01-ingest-raw` |
| Application Files | Upload `labs/01_ingest_raw.py` |
| Main Class | *(leave empty for Python)* |
| Arguments | `--db workshop_credit` |
| Arguments | `--landing s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing` |

3. **Resources:** 2 executors, 4g memory (facilitator may adjust)
4. Click **Create**

### Step 1.3 — Run the job

1. Click **Run** on `credit-01-ingest-raw`
2. Open **Job Runs** → select run → **Logs**
3. Wait for status **Succeeded**

**Look for in logs:**
```
SUCCESS: wrote 40000 rows to workshop_credit.raw_applications
```

### Step 1.4 — Validate (Job logs or CAI)

**Option A — Job logs:** confirm row count in success message above.

**Option B — CAI Workbench** (after Lab 2, or if Spark enabled now):

```python
raw = spark.table("workshop_credit.raw_applications")
print("Count:", raw.count())
raw.groupBy("default_flag").count().show()
raw.printSchema()
```

**Expected:**
- ~40,000 rows
- `default_flag` values 0 and 1
- `ingested_at` column populated

### Step 1.5 — Discussion questions

1. Why store raw data in Iceberg instead of keeping only CSV?
2. What governance policies (Ranger) should apply to applicant data?

✅ **Lab 1 complete.**

---

## Lab 2 — Feature engineering (CDE Job)

**Goal:** Transform raw data into model-ready features in `workshop_credit.features`.

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
| `high_utilization_flag` | 1 if utilization > 0.75 |
| `default_flag` | Label for modeling |

### Step 2.2 — Create CDE Job

1. **Jobs** → **Create Job**
2. Fill in:

| Field | Value |
|-------|-------|
| Job Type | **Spark** |
| Name | `credit-02-build-features` |
| Application Files | Upload `labs/02_build_features.py` |
| Main Class | *(leave empty for Python)* |
| Arguments | `--db workshop_credit` |

3. Click **Create** → **Run**

### Step 2.3 — Validate in job logs

**Look for:**
```
SUCCESS: wrote 40000 rows to workshop_credit.features
LATEST_SNAPSHOT_ID=<number>
```

**Save the snapshot ID** — you will log it in MLflow during Lab 4.

### Step 2.4 — Validate in CAI (optional)

```python
feat = spark.table("workshop_credit.features")
feat.printSchema()
feat.groupBy("default_flag").count().show()
```

**Expected:** ~4–7% positive class (defaults).

### Step 2.5 — Hands-on challenge (optional)

Add to `02_build_features.py` if not already present:

```python
.withColumn("high_utilization_flag", F.when(F.col("utilization") > 0.75, 1).otherwise(0))
```

Re-upload script, re-run job, confirm column exists.

✅ **Lab 2 complete.**

---

## Lab 3 — Train a credit model (CAI)

**Goal:** Train XGBoost classifier, track with MLflow, register best model.

**Time:** 75 minutes

### Step 3.1 — Open CAI and create session

1. **Cloudera AI** → project `credit-scoring-workshop`
2. Upload `labs/cai/04_train_credit_model.py` to project files
3. **New Session** — enable Spark if reading Iceberg via Spark connection
4. Install dependencies if needed:
   ```bash
   pip install xgboost scikit-learn
   ```

### Step 3.2 — Update config in training script

Edit these lines in `04_train_credit_model.py`:

```python
WORKSHOP_DB = "workshop_credit"
FEATURES_SNAPSHOT_ID = "<paste from Lab 2 job logs>"
```

### Step 3.3 — Load feature table

```python
features_df = spark.table("workshop_credit.features").toPandas()
print(features_df.shape)
features_df["default_flag"].value_counts()
```

### Step 3.4 — Train with MLflow

Run the full training script (trains 3 models with different `max_depth`).

**Expected MLflow metrics (approximate):**
- `auc` ≈ 0.80–0.87
- `ks` ≈ 0.30–0.45
- `gini` ≈ 0.60–0.74

### Step 3.5 — Register best model

1. CAI → **Experiments** → `credit_default_prediction`
2. Sort by `auc` descending
3. Best run → **Register Model** → name: `credit_default_model`

✅ **Lab 3 complete.**

---

## Lab 4 — Deploy model (CAI)

**Goal:** Deploy registered model as REST API and score one applicant.

**Time:** 45 minutes

### Step 4.1 — Deploy model

1. **Model Registry** → `credit_default_model`
2. Best version → **Deploy** → name: `credit-scoring-api`
3. Wait until status = **Deployed**

### Step 4.2 — Test with curl

Replace `<CAI_MODEL_URL>` and `<TOKEN>` (facilitator provides):

```bash
curl -X POST "https://<CAI_MODEL_URL>/model/credit-scoring-api/infer" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [[0.35, 45, 0.25, 1, 8, 2, 1, 0, 5500.0, 0]]
  }'
```

**Expected:** probability of default (float 0–1).

### Step 4.3 — Risk bands

| Probability | Band |
|-------------|------|
| < 0.10 | A — Low risk |
| 0.10 – 0.20 | B — Medium |
| 0.20 – 0.35 | C — High |
| ≥ 0.35 | D — Very high |

✅ **Lab 4 complete.**

---

## Lab 5 — Batch scoring (CDE Job)

**Goal:** Score all applicants via CDE job calling CAI model API.

**Time:** 60 minutes

### Step 5.1 — Create CDE Job

1. **Jobs** → **Create Job**
2. Fill in:

| Field | Value |
|-------|-------|
| Job Type | **Spark** |
| Name | `credit-04-batch-score` |
| Application Files | Upload `labs/04_batch_score.py` |
| Main Class | *(leave empty for Python)* |
| Arguments | `--db workshop_credit` |
| Arguments | `--model-url https://<CAI_MODEL_URL>/model/credit-scoring-api/infer` |
| Arguments | `--model-name credit_default_model` |
| Arguments | `--model-version 1` |

3. Click **Create** → **Run**

### Step 5.2 — Validate in job logs

**Look for:**
```
SUCCESS: scored 40000 applicants into workshop_credit.scores
```

### Step 5.3 — Validate in CAI (optional)

```python
scores = spark.table("workshop_credit.scores")
scores.groupBy("risk_band").count().orderBy("risk_band").show()
scores.orderBy("probability_default", ascending=False).show(10)
```

**Expected columns:**
- `applicant_id`, `probability_default`, `risk_band`
- `model_name`, `model_version`, `scored_at`

### Step 5.4 — Capstone check

```
raw_applications → features → scores
                      ↑
                 CAI model API
```

✅ **Lab 5 complete.**

---

## Lab 6 — Governance & explainability (CAI, optional)

**Goal:** Generate reason codes for one applicant using SHAP.

**Time:** 30 minutes

1. Open `labs/cai/06_explainability.py` in CAI
2. Run script — review top SHAP contributors
3. Discuss with facilitator:

| Question | Platform answer |
|----------|-----------------|
| Who can read raw PII? | Ranger on `raw_applications` |
| Which data trained the model? | MLflow `features_snapshot_id` |
| Which model scored this applicant? | `scores.model_version` |
| Reproduce training data? | Iceberg time travel to snapshot ID |

✅ **Workshop complete.**

---

## Appendix — Airflow (skipped)

This workshop runs CDE jobs **manually in order**. In production, you would orchestrate with **CDE Airflow**:

```
ingest → quality → features → batch score
```

See `labs/airflow_credit_scoring_dag.py` for a future reference implementation.

---

## Quick reference — CDE job arguments

| Job | Arguments |
|-----|-----------|
| `credit-00-validate` | `--db workshop_credit` |
| `credit-01-ingest-raw` | `--db workshop_credit` `--landing s3a://workshpcloud-buk-5e3a7882/workshop/credit_scoring/landing` |
| `credit-02-build-features` | `--db workshop_credit` |
| `credit-04-batch-score` | `--db workshop_credit` `--model-url <URL>` `--model-name credit_default_model` `--model-version 1` |

---

## Quick reference — feature column order for API

```
[utilization, age, debt_ratio, delinq_total, open_credit_lines,
 real_estate_loans, dependents, income_missing, monthly_income,
 high_utilization_flag]
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Table not found` | Check database `workshop_credit` and Ranger policy |
| Ingest 0 rows | Verify CSV path in S3; use `s3a://` in job args |
| `Main Class` required error | Upload `.py` file; leave Main Class empty for Python |
| CDE Sessions unavailable | Use Jobs only — this guide supports that |
| Spark OOM | Reduce data or increase executor memory |
| MLflow run missing | Confirm `mlflow.start_run()` executed |
| Model API 401 | Refresh CAI API token |
| Batch score timeout | See chunking in `04_batch_score.py` |

Contact facilitator for CAI model URL and credentials.
