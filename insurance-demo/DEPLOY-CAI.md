# Deploy Insurance Demo — CAI (Train + Agent)

Run this after the Trino pipeline is complete and `claim_features_v1` has 4912 rows.

## Architecture

```text
S3 CSVs
  -> Trino ext_* + raw_* + silver views + claim_features_v1 (DONE)
  -> CAI Workbench: train model from gold table
  -> AI Registry + Inference endpoint
  -> Agent Studio: SQL lookup + scoring + policy RAG
```

Gold table for CAI:

```text
hive.insurance_leo_trino.claim_features_v1
```

Policy document for RAG:

```text
s3a://lhdemocdpbca1/insurancedemo/policy/coverage_policy.md
```

---

## Step 1 — Local sanity check (your laptop)

```bash
cd insurance-demo
python3 -m pip install -r requirements.txt
python3 cai/train_and_register.py --mode local
python3 scripts/pick_demo_claims.py
```

Artifacts written to `cai/artifacts/`:

- `claim_adjudication_xgb_v1.joblib`
- `claim_adjudication_xgb_v1_features.json`
- `claim_adjudication_xgb_v1_labels.json`
- `claim_adjudication_xgb_v1_metrics.json`

---

## Step 2 — Upload CAI scripts to your environment

```bash
aws s3 sync cai/ s3://lhdemocdpbca1/insurancedemo/cai/ --exclude "artifacts/*"
aws s3 cp data/policy/coverage_policy.md s3://lhdemocdpbca1/insurancedemo/policy/coverage_policy.md
```

---

## Step 3 — Train in CAI Workbench

Create a Workbench session with Spark + Hive access, then:

```bash
pip install -r requirements.txt
python3 cai/train_and_register.py \
  --mode cai \
  --source-table hive.insurance_leo_trino.claim_features_v1
```

Register the model in **AI Registry** and promote to **AI Inference** as `claim-adjudication-xgb-v1`.

---

## Step 4 — Build Agent Studio workflow

Follow `agent/claims_adjudicator_design.md`:

| Tool | Source |
|---|---|
| Feature Lookup | SQL on `claim_features_v1` |
| Scoring | Inference endpoint |
| Policy RAG | `coverage_policy.md` |
| Bill Detail (optional) | SQL on `raw_hospital_bills` |

---

## Demo claims

| Story | Claim ID |
|---|---|
| Fast approve | `CLM-50005` |
| Pre-existing reject | `CLM-50021` |
| Partial / missing auth | `CLM-50003` |
| Manual review | `CLM-50001` |
| Policy inactive reject | `CLM-50009` |

Example agent prompt:

> Review claim CLM-50021. Pull features, score with the model, cite coverage policy, and recommend approve or reject with reasons.
