# Deploy Credit Demo on Data Hub with Spark

Use this guide if you run Spark on a **Data Hub cluster** instead of **Cloudera Data Engineering (CDE)**.

Your environment:

| Item | Value |
|---|---|
| S3 bucket | `lhdemocdpbca1` |
| Workshop env | `workshopdelh` |
| Data Hub cluster | your Spark cluster (e.g. `lhworkshop`) |

The **same 3 Python scripts** in `cde/` are reused. Only **how you run them** changes.

---

## Architecture

```text
MacBook
  -> upload CSVs + scripts to S3
Data Hub (Spark on YARN)
  -> spark3-submit Job 01 Bronze
  -> spark3-submit Job 02 Silver
  -> spark3-submit Job 03 Gold
  -> Iceberg tables in Hive
Cloudera AI
  -> train model + Agent Studio
```

---

## Step 0 — Local prep (MacBook, already done)

You already generated data locally. If needed:

```bash
cd "/Users/leonard/cursor demo ai/agents/credit-demo"
python3 scripts/generate_dummy_data.py
```

---

## Step 1 — Upload to S3 (MacBook)

```bash
cd "/Users/leonard/cursor demo ai/agents/credit-demo"
export BUCKET=s3://lhdemocdpbca1

aws s3 cp data/applications.csv "$BUCKET/credit-demo/raw/applications.csv"
aws s3 cp data/transactions.csv "$BUCKET/credit-demo/raw/transactions.csv"
aws s3 cp data/policy/credit_policy.md "$BUCKET/credit-demo/policy/credit_policy.md"
aws s3 sync cde/ "$BUCKET/credit-demo/cde/"
aws s3 sync cai/ "$BUCKET/credit-demo/cai/" --exclude "artifacts/*"
aws s3 sync datahub/ "$BUCKET/credit-demo/datahub/"
```

Verify:

```bash
aws s3 ls s3://lhdemocdpbca1/credit-demo/ --recursive | head -20
```

---

## Step 2 — Open your Data Hub cluster

In **Cloudera Management Console**:

1. Go to **Environments → workshopdelh**
2. Open **Data Hub** (not Data Engineering)
3. Start/open your Spark cluster if it is not running
4. Note how you connect:
   - **SSH** to gateway/edge node, or
   - **Hue** in the cluster

---

## Step 3 — Choose how to run Spark

You have **2 common options** on Data Hub.

### Option A — SSH + spark3-submit (recommended)

1. SSH to the cluster gateway node
2. Copy or pull the repo, or rely on scripts already in S3
3. Run jobs in order

```bash
# If repo is on the node:
cd credit-demo
source datahub/env.workshopdelh.sh
bash datahub/run_spark_jobs.sh bronze
bash datahub/run_spark_jobs.sh silver
bash datahub/run_spark_jobs.sh gold
```

Or all at once:

```bash
bash datahub/run_spark_jobs.sh all
```

#### If scripts are only on S3 (no git on cluster)

Download scripts first:

```bash
aws s3 sync s3://lhdemocdpbca1/credit-demo/cde/ /tmp/credit-demo/cde/
export SCRIPT_BASE=/tmp/credit-demo/cde
bash /tmp/credit-demo/datahub/run_spark_jobs.sh all
```

Or point `SCRIPT_BASE` at S3 if your cluster allows `spark3-submit s3a://...py` directly:

```bash
export SCRIPT_BASE=s3a://lhdemocdpbca1/credit-demo/cde
```

---

### Option B — Hue Spark / SQL editor

1. Open **Hue** from your Data Hub cluster
2. Go to **Editor → Spark** (or PySpark notebook)
3. Paste and run each script body, or run `spark3-submit` from the shell tab

For a workshop, Option A is simpler and repeatable.

---

## Step 4 — What each job does

| Order | Command | Creates |
|---|---|---|
| 1 | `run_spark_jobs.sh bronze` | `hive.credit_demo.raw_applications`, `raw_transactions` |
| 2 | `run_spark_jobs.sh silver` | `hive.credit_demo.customer_behavior_30d` |
| 3 | `run_spark_jobs.sh gold` | `hive.credit_demo.credit_features_v1` |

Manual `spark3-submit` equivalent for Job 1:

```bash
spark3-submit \
  --master yarn \
  --deploy-mode client \
  s3a://lhdemocdpbca1/credit-demo/cde/01_ingest_bronze.py \
  --catalog hive \
  --database credit_demo \
  --raw-base-path s3a://lhdemocdpbca1/credit-demo/raw
```

Job 2:

```bash
spark3-submit \
  --master yarn \
  --deploy-mode client \
  s3a://lhdemocdpbca1/credit-demo/cde/02_build_silver_features.py \
  --catalog hive \
  --database credit_demo
```

Job 3:

```bash
spark3-submit \
  --master yarn \
  --deploy-mode client \
  s3a://lhdemocdpbca1/credit-demo/cde/03_publish_gold_features.py \
  --catalog hive \
  --database credit_demo \
  --feature-version v1
```

---

## Step 5 — Verify tables in Hue

In **Hue → Query Editor → Hive/Impala/Trino** (whatever your cluster exposes):

```sql
SHOW DATABASES LIKE 'credit_demo';

SELECT COUNT(*) FROM credit_demo.raw_applications;
SELECT COUNT(*) FROM credit_demo.raw_transactions;
SELECT COUNT(*) FROM credit_demo.customer_behavior_30d;
SELECT COUNT(*) FROM credit_demo.credit_features_v1;

SELECT application_id, thin_file, debt_to_income_ratio, defaulted
FROM credit_demo.credit_features_v1
LIMIT 10;
```

Expected:

| Table | Rows |
|---|---|
| raw_applications | 5000 |
| raw_transactions | 119737 |
| customer_behavior_30d | 5000 |
| credit_features_v1 | 5000 |

If your catalog requires a prefix, use `hive.credit_demo....` instead of `credit_demo....`.

---

## Step 6 — Cloudera AI (unchanged)

After gold table exists, in **CAI Workbench**:

```bash
pip install -r requirements.txt
python3 train_and_register.py \
  --mode cai \
  --source-table hive.credit_demo.credit_features_v1
```

Then Registry → Inference → Agent Studio (see `agent/credit_copilot_design.md`).

---

## CDE vs Data Hub — what changed for you

| Task | CDE | Data Hub with Spark |
|---|---|---|
| Run Spark | CDE Jobs UI | `spark3-submit` on cluster or Hue |
| Script location | CDE Resources | S3 or local path on gateway |
| Cluster picker | Virtual Cluster | Data Hub cluster |
| Orchestration | CDE Airflow | Manual order or Oozie/Airflow on cluster |
| Iceberg | Built into CDE | Usually preconfigured on Data Hub |

You do **not** need to rewrite the Python scripts.

---

## Troubleshooting

### `spark3-submit: command not found`

Try:

```bash
which spark3-submit
which spark-submit
```

Use whichever exists on your cluster.

### Cannot read `s3a://lhdemocdpbca1/...`

- Confirm files exist: `aws s3 ls s3://lhdemocdpbca1/credit-demo/raw/`
- Confirm Data Hub instance role can read the bucket
- Ask cloud admin to verify **S3 access** for the Data Hub cluster

### Iceberg / `writeTo` fails

Ask admin if Iceberg is enabled on the cluster. You may need Spark conf for Iceberg (see comments in `datahub/run_spark_jobs.sh`).

### Permission denied on cluster

Even as admin, you need **SSH access** to the gateway node or use **Hue** with your cluster user.

### Table not visible in CAI

Confirm CAI and Data Hub share the same **Hive Metastore** / catalog in environment `workshopdelh`.

---

## Quick checklist

- [ ] S3 upload done
- [ ] Data Hub cluster running
- [ ] SSH or Hue access working
- [ ] Bronze job success
- [ ] Silver job success
- [ ] Gold job success
- [ ] SQL row counts verified
- [ ] CAI training started

---

## Files for Data Hub

```text
credit-demo/datahub/
  env.workshopdelh.sh      # bucket/catalog defaults for your env
  run_spark_jobs.sh        # bronze | silver | gold | all
```
