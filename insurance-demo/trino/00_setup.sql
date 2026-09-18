-- Insurance demo — schema setup for Trino / CDW
-- Replace placeholders before running:
--   ${CATALOG}     e.g. hive
--   ${DATABASE}    e.g. insurance_leo
--   ${RAW_BASE}    e.g. s3a://lhdemocdpbca1/insurancedemo/raw
--   ${ICEBERG_BASE} e.g. s3a://lhdemocdpbca1/insurancedemo/iceberg

CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${DATABASE}
WITH (location = '${ICEBERG_BASE}');
