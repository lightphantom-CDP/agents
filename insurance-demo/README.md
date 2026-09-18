# Medical Insurance Claim Review Demo

**CDE + Cloudera AI + CAI demo using synthetic hospital claims data**

Build an AI agent that reviews hospital claims — diagnosis, procedures, policy coverage, and medical history — then recommends **approve**, **partial approval**, **reject**, or **manual review**.

---

## What's inside

```text
insurance-demo/
  data/
    members.csv              # 2,000 synthetic policy holders
    policies.csv             # plan limits, deductibles, coverage flags
    medical_history.csv      # pre-existing conditions + disclosure status
    claims.csv               # ~5,000 hospital claims with outcomes
    claim_diagnoses.csv      # ICD-10 codes per claim
    claim_procedures.csv     # CPT procedures and costs
    hospital_bills.csv       # itemized bill lines
    policy/coverage_policy.md  # fake insurer policy for RAG
  scripts/
    generate_dummy_data.py   # regenerate all data
    pick_demo_claims.py      # bookmark claims for live demos
```

---

## Quick start

### 1. Generate dummy data

```bash
cd insurance-demo
python3 scripts/generate_dummy_data.py
```

### 2. Inspect sample claims

```bash
python3 scripts/pick_demo_claims.py
head -5 data/claims.csv
```

---

## Data model (for DWH / Iceberg)

| Dataset | Grain | Key fields | Use in pipeline |
|---|---|---|---|
| `members` | 1 row per member | `member_id`, age, region, smoker | Bronze dimension |
| `policies` | 1 row per policy | plan type, limits, waiting period | Bronze dimension |
| `medical_history` | 1 row per condition | pre-existing, disclosed flag | Silver enrichment |
| `claims` | 1 row per claim | billed amount, outcome label | Bronze fact |
| `claim_diagnoses` | 1 row per diagnosis | ICD-10, category | Bronze clinical |
| `claim_procedures` | 1 row per procedure | CPT, cost, prior-auth flag | Bronze clinical |
| `hospital_bills` | 1 row per bill line | category, amount, experimental | Silver itemization |

Suggested gold feature table: `hive.insurance_leo.claim_features_v1`

Join claims + diagnoses + procedures + policy + history to produce ML features and agent context.

---

## Claim outcome distribution

The generator creates realistic labels for supervised learning:

| Outcome | Typical share | Demo storyline |
|---|---|---|
| `approved` | ~45–55% | Fast hospital approval |
| `partial_approval` | ~15–20% | Mixed covered/excluded items |
| `manual_review` | ~10–15% | Borderline clinical review |
| `rejected` | ~20–30% | Waiting period, pre-existing, missing auth |

---

## Cloudera stack mapping

### Option A — Trino + external Iceberg (primary path)

Use the SQL scripts in `trino/` to:
1. Create **external CSV tables** (`ext_*`) that read raw files in place
2. Materialize **Iceberg bronze** tables (`raw_*`) with CTAS
3. Build **silver views** and **gold** `claim_features_v1`

See [`trino/README.md`](trino/README.md) for full steps.

```bash
export RAW_BASE=s3a://lhdemocdpbca1/insurancedemo/raw
export ICEBERG_BASE=s3a://lhdemocdpbca1/insurancedemo/iceberg
python3 trino/render_sql.py 01_bronze_external_csv.sql --print
```

### Option B — Spark CDE jobs
1. Ingest CSVs to Bronze Iceberg tables
2. Build Silver: join claims with diagnoses, procedures, policies
3. Publish Gold: `claim_features_v1` for model training and agent SQL lookup

### CAI (Cloudera AI)
1. Train classifier on `claim_outcome` from gold features
2. Register model in AI Registry
3. Deploy to AI Inference for real-time scoring

### Agent Studio
Suggested tools for the claim review copilot:
- SQL lookup on gold claim features
- Inference endpoint for approve/reject probability
- RAG on `data/policy/coverage_policy.md`
- Python tool to explain denial reasons

Example agent prompt:

> "Review claim CLM-50142. Pull diagnosis, procedures, policy limits, and medical history. Apply coverage policy and recommend approve or reject with cited reasons."

---

## Demo claims to bookmark

Run `python3 scripts/pick_demo_claims.py` after generating data. Look for:

| Scenario | What to show |
|---|---|
| Fast approve | Emergency visit, covered plan, within limits |
| Clear reject | Undisclosed pre-existing condition |
| Missing prior auth | High-cost procedure without authorization |
| Partial approval | Medically necessary + excluded line items |
| Manual review | Borderline case for human-in-the-loop |

---

## Environment variables (CDE)

| Variable | Example | Purpose |
|---|---|---|
| `INSURANCE_CATALOG` | `hive` | Iceberg catalog |
| `INSURANCE_DATABASE` | `insurance_leo` | Database name |
| `RAW_BASE_PATH` | `s3a://lhdemocdpbca1/insurancedemo/raw` | Bronze CSV location |

---

## Regenerate from scratch

```bash
python3 scripts/generate_dummy_data.py
python3 scripts/pick_demo_claims.py
```

All person and clinical data is **synthetic** and safe for workshops.
