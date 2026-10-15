-- Credit Scoring Workshop — Iceberg table reference DDL
-- Tables are created by CDE jobs; this file documents the schema.

CREATE DATABASE IF NOT EXISTS workshop_credit;

-- Populated by labs/01_ingest_raw.py
-- workshop_credit.raw_applications

-- Populated by labs/02_build_features.py
-- workshop_credit.features
-- Columns:
--   applicant_id BIGINT
--   utilization DOUBLE
--   age INT
--   debt_ratio DOUBLE
--   delinq_total INT
--   open_credit_lines INT
--   real_estate_loans INT
--   dependents DOUBLE
--   income_missing INT
--   monthly_income DOUBLE
--   high_utilization_flag INT
--   default_flag INT
--   feature_built_at TIMESTAMP

-- Populated by labs/03_data_quality.py
-- workshop_credit.quality_log

-- Populated by labs/04_batch_score.py
-- workshop_credit.scores
-- Columns:
--   applicant_id BIGINT
--   probability_default DOUBLE
--   risk_band STRING
--   model_name STRING
--   model_version STRING
--   scored_at STRING

-- Useful queries for workshop demos:

-- Default rate
SELECT default_flag, COUNT(*) AS n
FROM workshop_credit.features
GROUP BY default_flag;

-- Risk band distribution
SELECT risk_band, COUNT(*) AS n
FROM workshop_credit.scores
GROUP BY risk_band
ORDER BY risk_band;

-- Latest quality checks
SELECT * FROM workshop_credit.quality_log
ORDER BY checked_at DESC
LIMIT 10;

-- Iceberg snapshot for MLflow reproducibility
SELECT snapshot_id, committed_at
FROM workshop_credit.features.snapshots
ORDER BY committed_at DESC
LIMIT 5;
