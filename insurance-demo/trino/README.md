# Insurance Demo — Trino + External Iceberg Tables

Use **Trino in Cloudera Data Warehouse (CDW)** instead of Spark CDE jobs. This path is often faster for workshops because you can query CSVs and build Iceberg tables with SQL only.

---

## Architecture

```text
CSV files on object storage
        |
        v
ext_* external CSV tables     <-- reads files in place (no copy)
        |
        v
raw_* Iceberg tables          <-- governed bronze (PARQUET + Iceberg metadata)
        |
        v
silver_* views                <-- joins + aggregations
        |
        v
claim_features_v1 Iceberg     <-- gold table for CAI + Agent Studio
```

**Why two bronze steps?**
- `ext_*` = cheap staging, great for first load and debugging
- `raw_*` = governed Iceberg tables with ACID, time travel, and lineage for CAI

You can skip `ext_*` later and `INSERT` directly into Iceberg once pipelines are stable.

---

## Prerequisites

- Cloudera Data Warehouse (CDW) with Trino or Hue SQL access
- AWS S3 bucket: **`s3a://lhdemocdpbca1/insurancedemo`** (your CDP environment)
- Iceberg enabled on your Hive catalog (default on most CDP DWH environments)

Pre-rendered SQL for this bucket is in **`trino/rendered/`** — ready to paste into Hue.

---

## Step 1 — Generate and upload CSVs

```bash
cd insurance-demo
python3 scripts/generate_dummy_data.py
```

Upload to your AWS bucket:

```bash
cd insurance-demo
python3 scripts/generate_dummy_data.py
./scripts/upload_to_s3.sh
```

Target paths:

```text
s3a://lhdemocdpbca1/insurancedemo/raw/members.csv
s3a://lhdemocdpbca1/insurancedemo/raw/policies.csv
s3a://lhdemocdpbca1/insurancedemo/raw/medical_history.csv
s3a://lhdemocdpbca1/insurancedemo/raw/claims.csv
s3a://lhdemocdpbca1/insurancedemo/raw/claim_diagnoses.csv
s3a://lhdemocdpbca1/insurancedemo/raw/claim_procedures.csv
s3a://lhdemocdpbca1/insurancedemo/raw/hospital_bills.csv
```

Iceberg tables will be written to:

```text
s3a://lhdemocdpbca1/insurancedemo/iceberg/
```

---

## Step 2 — Replace placeholders

In each SQL file, replace:

| Placeholder | Your value |
|---|---|
| `${CATALOG}` | `hive` |
| `${DATABASE}` | `insurance_leo` |
| `${RAW_BASE}` | `s3a://lhdemocdpbca1/insurancedemo/raw` |
| `${ICEBERG_BASE}` | `s3a://lhdemocdpbca1/insurancedemo/iceberg` |

Or use the helper script:

```bash
export INSURANCE_CATALOG=hive
export INSURANCE_DATABASE=insurance_leo
export RAW_BASE=s3a://lhdemocdpbca1/insurancedemo/raw
export ICEBERG_BASE=s3a://lhdemocdpbca1/insurancedemo/iceberg

python3 trino/render_sql.py --print 00_setup.sql
```

---

## Trino catalog prefix (required)

If you see `MISSING_CATALOG_NAME`, always use **3-part names**:

```sql
hive.insurance_leo.ext_claims        -- catalog.schema.table
```

Not:

```sql
insurance_leo.ext_claims             -- fails without session catalog
```

Run `00a_discover_catalog.sql` if `hive` is not your catalog:

```sql
SHOW CATALOGS;
```

In Hue, you can also pick the **catalog** from the dropdown above the editor (set it to `hive` or your DB catalog name).

---

## Step 3 — Run SQL in order

In **Hue → Query Editor** → **Trino**:

1. `00_setup.sql` — create schema
2. `01_bronze_external_csv.sql` — external CSV tables
3. `02_bronze_iceberg_tables.sql` — Iceberg bronze CTAS
4. `03_silver_views.sql` — silver views
5. `04_gold_claim_features.sql` — gold feature table

---

## Step 4 — Verify

```sql
SHOW TABLES IN hive.insurance_leo;

SELECT COUNT(*) FROM hive.insurance_leo.ext_claims;          -- ~4912
SELECT COUNT(*) FROM hive.insurance_leo.raw_claims;          -- ~4912
SELECT COUNT(*) FROM hive.insurance_leo.claim_features_v1;   -- ~4912

SELECT claim_outcome, COUNT(*)
FROM hive.insurance_leo.claim_features_v1
GROUP BY 1;

SELECT claim_id, claim_outcome, total_billed_amount, denial_reasons
FROM hive.insurance_leo.claim_features_v1
WHERE claim_id IN ('CLM-50005', 'CLM-50021', 'CLM-50003');
```

---

## Alternative: register existing Iceberg table

If Iceberg data + metadata already exist at a location (e.g. written by Spark), register instead of CTAS:

```sql
CALL hive.system.register_table(
    schema_name => 'insurance_leo',
    table_name  => 'raw_claims',
    table_location => 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_claims'
);
```

Syntax may vary slightly by Trino version; check your CDW docs for `register_table`.

---

## Connect CAI to gold table

Train from the governed gold table:

```bash
python3 cai/train_and_register.py \
  --mode cai \
  --source-table hive.insurance_leo.claim_features_v1
```

Agent Studio SQL tool example:

```sql
SELECT *
FROM hive.insurance_leo.claim_features_v1
WHERE claim_id = 'CLM-50021';
```

---

## Trino vs Spark CDE — when to use which

| Use Trino | Use Spark CDE |
|---|---|
| SQL-only workshops | Heavy transforms / UDFs |
| Quick Iceberg CTAS | Streaming or large-scale ETL |
| Agent ad-hoc queries | Complex ML feature engineering in Spark |
| External CSV → Iceberg | Already standardized on CDE Airflow |

For this insurance demo, **Trino is a great fit**.

---

## Refresh data

After regenerating CSVs:

```sql
-- Option A: drop and recreate (simplest for demos)
DROP TABLE IF EXISTS hive.insurance_leo.claim_features_v1;
-- re-run 02 → 04

-- Option B: merge / append into Iceberg (production pattern)
-- INSERT INTO hive.insurance_leo.raw_claims SELECT * FROM hive.insurance_leo.ext_claims;
```
