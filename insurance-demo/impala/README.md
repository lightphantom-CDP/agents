# Insurance Demo — Impala path (CDW)

Use this if **Impala works** in your environment but Trino gives impersonation errors.

## Why Impala worked but Trino didn't

| | Impala VW | Trino VW |
|---|---|---|
| Auth in Hue | Mature, well-integrated | Stricter Ranger impersonation |
| Ranger service | Separate Impala policies | Separate Trino policies |
| Your error | None | `srv_env-... cannot become user leonard` |

Same Database Catalog, different Virtual Warehouse engine = different security layer. **Not strange — common on CDP.**

## S3 layout for Impala

Impala external tables need **one folder per table** (not a single file path like Trino).

```text
s3a://lhdemocdpbca1/insurancedemo/raw/
  claims/claims.csv
  members/members.csv
  policies/policies.csv
  medical_history/medical_history.csv
  claim_diagnoses/claim_diagnoses.csv
  claim_procedures/claim_procedures.csv
  hospital_bills/hospital_bills.csv
```

Upload with subfolders:

```bash
./scripts/upload_to_s3.sh --impala-layout
```

## Run in Hue → Impala

**Important:** Run each file separately. If you get `Database does not exist`, run step 0 first.

0. `00_create_database.sql` — create DB + `INVALIDATE METADATA`
1. `01_bronze_external.sql`
2. `02_bronze_iceberg.sql`
3. `03_silver_views.sql`
4. `04_gold_claim_features.sql`

## Verify

```sql
SELECT COUNT(*) FROM insurance_leo.ext_claims;
SELECT COUNT(*) FROM insurance_leo.claim_features_v1;

SELECT claim_id, claim_outcome, total_billed_amount
FROM insurance_leo.claim_features_v1
LIMIT 10;
```

## CAI gold table

```text
insurance_leo.claim_features_v1
```

(or `hive.insurance_leo.claim_features_v1` depending on your catalog naming)
