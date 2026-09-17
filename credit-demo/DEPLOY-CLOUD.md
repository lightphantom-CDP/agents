# Deploy Credit Demo on Cloudera on Cloud (S3 + CDE + CAI)

Use this guide after you have validated the pack locally on your laptop.

Replace placeholders before running:


| Placeholder      | Example                          | Your value |
| ---------------- | -------------------------------- | ---------- |
| `YOUR-S3-BUCKET` | `s3a://my-datalake-bucket`       |            |
| `YOUR-CDE-VC`    | `credit-demo-vc`                 |            |
| `YOUR-CATALOG`   | `hive` or your CDW catalog name  |            |
| `YOUR-ENV-URL`   | `https://xxxxx.cdp.cloudera.com` |            |


---

## Architecture on your environment

```text
S3 raw CSVs
   -> CDE Spark Job 01 (Bronze Iceberg)
   -> CDE Spark Job 02 (Silver Iceberg)
   -> CDE Spark Job 03 (Gold Iceberg)
   -> CAI Workbench (train + register)
   -> CAI Inference (score API)
   -> Agent Studio (credit copilot + policy RAG)
```

---

## Step 0 — Local prep (your laptop)

Run once on your Mac to generate data and sanity-check the model:

```bash
cd "/Users/leonard/cursor demo ai/agents/credit-demo"
python3 -m pip install -r requirements.txt
python3 scripts/generate_dummy_data.py
python3 cai/train_and_register.py --mode local
python3 scripts/pick_demo_applicants.py
```

Keep the printed demo application IDs for the workshop.

---

## Step 1 — Upload files to S3

Upload from your laptop with AWS CLI (or the S3 console).

```bash
export BUCKET=s3://YOUR-S3-BUCKET
export DEMO_PREFIX=credit-demo

aws s3 cp data/applications.csv  "$BUCKET/$DEMO_PREFIX/raw/applications.csv"
aws s3 cp data/transactions.csv  "$BUCKET/$DEMO_PREFIX/raw/transactions.csv"
aws s3 cp data/policy/credit_policy.md "$BUCKET/$DEMO_PREFIX/policy/credit_policy.md"

aws s3 sync cde/ "$BUCKET/$DEMO_PREFIX/cde/"
aws s3 sync cai/  "$BUCKET/$DEMO_PREFIX/cai/" --exclude "artifacts/*"
```

Expected S3 layout:

```text
s3://YOUR-S3-BUCKET/credit-demo/
  raw/applications.csv
  raw/transactions.csv
  policy/credit_policy.md
  cde/01_ingest_bronze.py
  cde/02_build_silver_features.py
  cde/03_publish_gold_features.py
  cai/train_and_register.py
  cai/shap_explainer.py
  cai/batch_score.py
```

Spark reads these with the `s3a://` scheme:

```text
s3a://YOUR-S3-BUCKET/credit-demo/raw
```

---

## Step 2 — CDE: upload Resources (recommended)

In **Cloudera on Cloud → Data Engineering → Resources**:

1. Create resource folder: `credit-demo`
2. Upload the `cde/` Python files
3. Optionally upload `cai/` scripts too (useful if CAI reads from the same resource mount)

Note the resource path shown in CDE. Example:

```text
/home/cde/credit-demo/cde/01_ingest_bronze.py
```

---

## Step 3 — CDE: create Virtual Cluster (if needed)

In **Data Engineering → Virtual Clusters**:

- Name: `credit-demo-vc`
- Spark version: 3.x (match your environment)
- Enable Iceberg / Hive catalog access
- Size: small is enough for this demo (e.g. 2 executors)

Wait until status is **Running**.

---

## Step 4 — CDE: create Spark jobs

Create **3 Spark jobs** on your virtual cluster.

### Job 1 — Bronze ingest


| Field     | Value                                  |
| --------- | -------------------------------------- |
| Name      | `credit-demo-01-bronze`                |
| Script    | Resource path to `01_ingest_bronze.py` |
| Arguments | see below                              |


```text
--catalog YOUR-CATALOG
--database credit_demo
--raw-base-path s3a://YOUR-S3-BUCKET/credit-demo/raw
```

### Job 2 — Silver features


| Field     | Value                         |
| --------- | ----------------------------- |
| Name      | `credit-demo-02-silver`       |
| Script    | `02_build_silver_features.py` |
| Arguments |                               |


```text
--catalog YOUR-CATALOG
--database credit_demo
```

### Job 3 — Gold features


| Field     | Value                         |
| --------- | ----------------------------- |
| Name      | `credit-demo-03-gold`         |
| Script    | `03_publish_gold_features.py` |
| Arguments |                               |


```text
--catalog YOUR-CATALOG
--database credit_demo
--feature-version v1
```

Run them **in order**: Job 1 → Job 2 → Job 3.

---

## Step 5 — Verify Iceberg tables

In **Data Warehouse / Hue / Trino / Spark SQL** (whatever your env exposes), run:

```sql
SHOW DATABASES LIKE 'credit_demo';

SELECT COUNT(*) FROM hive.credit_demo.raw_applications;
SELECT COUNT(*) FROM hive.credit_demo.raw_transactions;
SELECT COUNT(*) FROM hive.credit_demo.customer_behavior_30d;
SELECT COUNT(*) FROM hive.credit_demo.credit_features_v1;

SELECT application_id, thin_file, debt_to_income_ratio, defaulted
FROM hive.credit_demo.credit_features_v1
LIMIT 10;
```

Expected counts:


| Table                 | Rows    |
| --------------------- | ------- |
| raw_applications      | 5000    |
| raw_transactions      | ~119737 |
| customer_behavior_30d | 5000    |
| credit_features_v1    | 5000    |


If your catalog is not `hive`, replace it in all SQL and job args.

---

## Step 6 — CAI Workbench: create project

In **Cloudera AI → Workbench**:

1. Create project: `credit-demo`
2. Upload or git-sync the `credit-demo/cai/` folder
3. Open a Python 3 session with a runtime that includes Spark + ML libs
4. Install deps in the session:

```bash
pip install -r requirements.txt
```

1. Confirm Spark can read the gold table:

```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("credit_demo_check").getOrCreate()
df = spark.table("hive.credit_demo.credit_features_v1")
df.printSchema()
print(df.count())
```

---

## Step 7 — CAI: train and register model

In the Workbench session:

```bash
python3 train_and_register.py \
  --mode cai \
  --source-table hive.credit_demo.credit_features_v1
```

This writes artifacts under `cai/artifacts/`.

Then in **AI Registry**:

1. Log the run (MLflow if enabled in your project)
2. Register `credit_default_xgb_v1.joblib`
3. Validate metrics JSON in artifacts
4. Promote to **AI Inference** as endpoint name: `credit-default-xgb-v1`

Test explainability:

```bash
python3 shap_explainer.py --application-id APP-10482
```

---

## Step 8 — CAI: policy RAG

In **RAG Studio** (or your CAI knowledge base feature):

1. Upload `data/policy/credit_policy.md`
2. Create knowledge base: `novabank-credit-policy`
3. Test retrieval:
  - "What is the thin-file review threshold?"
  - "What decline wording is required?"

---

## Step 9 — Agent Studio: Credit Copilot

Follow `agent/credit_copilot_design.md`.

Minimum tools to wire up:


| Tool           | Source                                       |
| -------------- | -------------------------------------------- |
| Feature lookup | SQL on `hive.credit_demo.credit_features_v1` |
| Scoring        | Inference endpoint `credit-default-xgb-v1`   |
| Explainability | Python tool wrapping `shap_explainer.py`     |
| Policy         | RAG knowledge base `novabank-credit-policy`  |


Demo prompts:

```text
Review applicant APP-10482 for a USD 15,000 personal loan.
Why is APP-10002 in review instead of approve?
Draft an adverse action notice for APP-12918 with policy-compliant wording.
What documents do we need for thin-file applicant APP-14164?
```

---

## Step 10 — Optional Airflow orchestration in CDE

After the 3 jobs work manually, deploy `cde/airflow_dag.py` as a CDE Airflow job.

Update these constants in the DAG file first:

- `RESOURCE_BASE`
- `RAW_BASE_PATH`
- `CATALOG`
- `DATABASE`

Schedule: `@daily` for demo, or manual trigger only.

---

## Troubleshooting

### Spark cannot read S3 (`s3a://...`)

- Confirm the bucket path exists
- Confirm the CDE cluster has cloud storage access to that bucket
- Use `s3a://` not `s3://` in Spark job args

### Table not found in CAI

- Confirm catalog/database names match CDE job args
- Confirm Job 3 succeeded
- Run `SHOW TABLES IN hive.credit_demo` from the same CAI Spark session

### XGBoost/lib errors in CAI

- Use the ML runtime image recommended by your admin
- If XGBoost still fails, the script falls back to sklearn automatically

### Permission / IAM issues on S3 upload from laptop

- Run `aws sts get-caller-identity`
- Ensure your IAM role/user can `s3:PutObject` to the target bucket

---

## Workshop run order (live demo)

1. Show S3 raw files
2. Run CDE Job 1 → 2 → 3 (or trigger Airflow DAG)
3. Query gold Iceberg table
4. Train/register model in CAI
5. Call Inference endpoint for one applicant
6. Show SHAP explanation
7. Open Agent Studio copilot and ask the 4 demo prompts

---

## Quick reference — what runs where


| Command / asset                        | Runs on           |
| -------------------------------------- | ----------------- |
| `scripts/generate_dummy_data.py`       | Your laptop       |
| `aws s3 cp ...`                        | Your laptop       |
| `cde/01_*.py` Spark jobs               | **CDE**           |
| `cai/train_and_register.py --mode cai` | **CAI Workbench** |
| Inference endpoint                     | **CAI Inference** |
| Agent copilot                          | **Agent Studio**  |


