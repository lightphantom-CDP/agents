-- ============================================================
-- STEP A — Run ONLY line 1 below. Stop. Check for red error.
-- Do NOT run all lines together until CREATE succeeds.
-- ============================================================

CREATE DATABASE insurance_leo
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/insurance_leo.db';

-- ============================================================
-- STEP B — After step A succeeds, run these two lines:
-- ============================================================

INVALIDATE METADATA;

SHOW DATABASES LIKE 'insurance%';

-- Expected result: one row → insurance_leo
-- Then click the refresh icon (↻) on the left Databases panel.
