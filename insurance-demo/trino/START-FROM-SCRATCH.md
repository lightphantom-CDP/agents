# Trino — Start From Scratch

Your environment:

| Setting | Value |
|---|---|
| Hue engine | **Trino** (from Trino Virtual Warehouse) |
| Catalog | **`hive`** (top-right dropdown) |
| Schema | **`insurance_leo`** |
| S3 raw | `s3a://lhdemocdpbca1/insurancedemo/raw/` |
| S3 iceberg | `s3a://lhdemocdpbca1/insurancedemo/iceberg/` |

**No S3 re-upload needed** — CSVs already in subfolders.

---

## Before you start

1. Open **Hue** from **Data Warehouse → Trino Virtual Warehouse**
2. Top-right dropdown: select **`hive.insurance_leo`** (not `hive.default`)
3. Run **one script at a time** (or one `CREATE` block at a time if Hue batches fail)

---

## Step 0 — Clean slate (optional)

Removes yesterday's Impala/Trino tables in `insurance_leo`:

```text
trino/rendered/99_cleanup.sql
```

Then:

```text
trino/rendered/00_setup.sql
```

---

## Step 1 — External CSV tables (pointers to S3)

```text
trino/rendered/01_bronze_external_csv.sql
```

Creates `ext_*` tables — reads CSV, no copy.

**Test:**

```sql
SELECT COUNT(*) FROM ext_claims;
SELECT COUNT(*) FROM ext_members;
```

Expected: **4912** claims, **2000** members.

---

## Step 2 — Iceberg bronze (Parquet on S3)

```text
trino/rendered/02_bronze_iceberg_tables.sql
```

Copies CSV → Iceberg under `iceberg/raw_*`.

**Test:**

```sql
SELECT COUNT(*) FROM raw_claims;
```

Expected: **4912**

---

## Step 3 — Silver views (joins)

```text
trino/rendered/03_silver_views.sql
```

**Test:**

```sql
SELECT claim_id, claim_outcome, icd10_code, total_billed_amount
FROM silver_claims_enriched
LIMIT 5;
```

---

## Step 4 — Gold table (for CAI + agent)

```text
trino/rendered/04_gold_claim_features.sql
```

**Test:**

```sql
SELECT claim_outcome, COUNT(*)
FROM claim_features_v1
GROUP BY 1;
```

---

## Full pipeline diagram

```text
S3 CSV (raw/claims/claims.csv)
        ↓
ext_claims          ← Step 1  hive + TEXTFILE pointer
        ↓
raw_claims          ← Step 2  Iceberg Parquet on S3
        ↓
silver_claims_enriched  ← Step 3  view (joins)
        ↓
claim_features_v1   ← Step 4  gold for ML/agent
```

---

## Demo queries (after step 4)

```sql
-- Fast approve
SELECT * FROM claim_features_v1 WHERE claim_id = 'CLM-50005';

-- Pre-existing reject
SELECT * FROM claim_features_v1 WHERE claim_id = 'CLM-50021';

-- Outcome distribution
SELECT claim_outcome, COUNT(*) FROM claim_features_v1 GROUP BY 1;
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `MISSING_CATALOG_NAME` | Set dropdown to **`hive.insurance_leo`** |
| `Table already exists` | Run `99_cleanup.sql` first |
| `Could not resolve table` | Refresh left panel; run `SHOW TABLES` |
| Step 02 fails | Confirm step 01 counts work first |

---

## Files to run (in order)

```text
99_cleanup.sql          (optional reset)
00_setup.sql
01_bronze_external_csv.sql
02_bronze_iceberg_tables.sql
03_silver_views.sql
04_gold_claim_features.sql
```

All in: `insurance-demo/trino/rendered/`
