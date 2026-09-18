# Trino in Hue — your environment

CDW Database Catalog display name: `lhcai-default`
Trino catalog name in Hue: **`hive`** (see left panel: `hive.insurance_leo`)

## Before running any query

1. Top-right dropdown: change **`hive.default`** → **`hive.insurance_leo`**
2. Or expand `hive.insurance_leo` in the left panel and click a table

## Test query

```sql
SELECT COUNT(*) FROM ext_claims;
```

Or fully qualified:

```sql
SELECT COUNT(*) FROM hive.insurance_leo.ext_claims;
```

## Catalogs in your Trino VW

| Catalog | Use for |
|---|---|
| `hive` | Hive tables + your `insurance_leo` schema ✅ |
| `iceberg` | Iceberg-native tables (use after step 02) |

## Run scripts in order

`trino/rendered/00_setup.sql` → `01` → `02` → `03` → `04`

All use `hive.insurance_leo.*`
