# Governed Credit Intelligence Workshop

**CDE + Cloudera AI demo using synthetic NovaBank credit data**

This pack gives you everything to run a 2026-style credit scoring workshop:

- dummy applications + transactions
- CDE Spark/Iceberg pipeline scripts
- CAI model training + SHAP explainability
- Agent Studio copilot design

---

## What's inside

```text
credit-demo/
  data/
    applications.csv          # 5,000 synthetic loan applications
    transactions.csv          # ~120k synthetic transactions
    policy/credit_policy.md   # fake bank policy for RAG
  scripts/
    generate_dummy_data.py    # regenerate data anytime
  cde/
    01_ingest_bronze.py
    02_build_silver_features.py
    03_publish_gold_features.py
    airflow_dag.py
  cai/
    train_and_register.py
    shap_explainer.py
    batch_score.py
    artifacts/                # created after training
  agent/
    credit_copilot_design.md
  requirements.txt
```

---

## Quick start (local, 15 minutes)

### 1. Install Python deps

```bash
cd credit-demo
python3 -m pip install -r requirements.txt
```

### 2. Regenerate dummy data (optional)

```bash
python3 scripts/generate_dummy_data.py
```

### 3. Train the model locally

```bash
python3 cai/train_and_register.py --mode local
```

Expected output includes:

- holdout AUC around **0.60+ locally** with the sklearn fallback
- higher AUC on Cloudera AI when XGBoost is available
- artifacts in `cai/artifacts/`

### 4. Explain one applicant

```bash
python3 cai/shap_explainer.py --application-id APP-10482
```

### 5. Batch score sample applicants

```bash
python3 cai/batch_score.py --limit 100
python3 scripts/pick_demo_applicants.py
```

---

## Workshop flow (90–120 min)

| Time | Section | What you show |
|---|---|---|
| 0–10 | Story | Thin-file lending + governed AI |
| 10–45 | CDE | Bronze -> Silver -> Gold on Iceberg |
| 45–70 | CAI | Train XGBoost, register, explain with SHAP |
| 70–100 | Agent Studio | Credit copilot with policy RAG |
| 100–120 | Q&A | Audit, retrain, promote model |

Facilitator tip: get **one applicant score working locally** before the workshop. Agents are the final layer, not the starting point.

---

## CDE deployment steps

### 1. Upload raw files to object storage

Upload these files:

- `data/applications.csv`
- `data/transactions.csv`

Example layout:

```text
s3a://YOUR-BUCKET/credit-demo/raw/applications.csv
s3a://YOUR-BUCKET/credit-demo/raw/transactions.csv
```

### 2. Upload Spark scripts to CDE Resources

Upload the `cde/` folder to your CDE resource path.

### 3. Create CDE Spark jobs

Run in order:

1. `01_ingest_bronze.py`
2. `02_build_silver_features.py`
3. `03_publish_gold_features.py`

Set environment variables or CLI args:

```bash
--catalog hive
--database credit_demo
--raw-base-path s3a://YOUR-BUCKET/credit-demo/raw
```

Tables created:

| Layer | Table |
|---|---|
| Bronze | `hive.credit_demo.raw_applications` |
| Bronze | `hive.credit_demo.raw_transactions` |
| Silver | `hive.credit_demo.customer_behavior_30d` |
| Gold | `hive.credit_demo.credit_features_v1` |

### 4. Optional: Airflow DAG

Deploy `cde/airflow_dag.py` as a CDE Airflow job and update:

- `RESOURCE_BASE`
- `RAW_BASE_PATH`
- catalog/database names

---

## Cloudera AI deployment steps

### 1. Create a Workbench project

Install requirements:

```bash
pip install -r requirements.txt
```

### 2. Train from governed gold table

```bash
python3 cai/train_and_register.py --mode cai --source-table hive.credit_demo.credit_features_v1
```

### 3. Register model in AI Registry

Log and register `cai/artifacts/credit_default_xgb_v1.joblib`.

Promote to **AI Inference** as `credit-default-xgb-v1`.

### 4. Build Agent Studio workflow

Follow `agent/credit_copilot_design.md`.

Suggested tools:

- SQL feature lookup on gold table
- Inference endpoint for scoring
- Python SHAP tool
- RAG on `data/policy/credit_policy.md`

---

## Demo applicants to bookmark

These IDs are useful live demo targets:

| Application ID | Why |
|---|---|
| `APP-10482` | Works well for decline / review storyline |
| `APP-10110` | Useful for "why review?" explanation |
| `APP-10055` | Thin-file manual review path |
| `APP-10225` | Good for adverse-action wording |

To find more programmatically:

```bash
python3 cai/batch_score.py --limit 5000
```

Then inspect `cai/artifacts/credit_scores_batch.csv` for high-risk and thin-file cases.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CREDIT_CATALOG` | `hive` | Iceberg catalog |
| `CREDIT_DATABASE` | `credit_demo` | Database name |
| `RAW_BASE_PATH` | `s3a://changeme/...` | Bronze CSV location |
| `FEATURE_VERSION` | `v1` | Gold table suffix |
| `CREDIT_GOLD_TABLE` | `hive.credit_demo.credit_features_v1` | CAI training source |

---

## Regenerate everything from scratch

```bash
python3 scripts/generate_dummy_data.py
python3 cai/train_and_register.py --mode local
python3 cai/batch_score.py --limit 100
python3 cai/shap_explainer.py --application-id APP-10482
```

---

## Notes

- All person/application data is **synthetic** and safe for demos.
- Default rate in the dummy data is intentionally high (~41%) so the model learns clearly.
- Replace `s3a://changeme/...` and catalog names with your environment values before CDE execution.
- For banking audiences, emphasize **SHAP + policy RAG + Iceberg lineage**, not just model accuracy.

---

## Next steps

1. Run the local quick start above
2. Upload data + scripts to CDE
3. Train/register in CAI
4. Build the Agent Studio copilot
5. Dry-run the 4 demo prompts in `agent/credit_copilot_design.md`
