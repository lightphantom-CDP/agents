-- Insurance demo — schema setup for Trino / CDW
-- Replace placeholders before running:
--   hive     e.g. hive
--   insurance_leo_trino    e.g. insurance_leo
--   s3a://lhdemocdpbca1/insurancedemo/raw    e.g. s3a://lhdemocdpbca1/insurancedemo/raw
--   s3a://lhdemocdpbca1/insurancedemo/iceberg e.g. s3a://lhdemocdpbca1/insurancedemo/iceberg

CREATE SCHEMA IF NOT EXISTS hive.insurance_leo_trino
WITH (location = 's3a://lhdemocdpbca1/insurancedemo/iceberg');
