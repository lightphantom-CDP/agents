-- Step 1: diagnose source
-- SELECT COUNT(*) FROM hive.insurance_leo_trino.ext_claims;   -- must be 4912

-- Step 2: drop empty raw_claims if it exists from a prior failed run
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_claims;

-- Step 3: recreate (no IF NOT EXISTS — forces fresh CTAS)
CREATE TABLE hive.insurance_leo_trino.raw_claims
WITH (format = 'PARQUET')
AS
SELECT
    claim_id,
    member_id,
    policy_id,
    hospital_id,
    hospital_name,
    admission_type,
    admission_date,
    discharge_date,
    CAST(length_of_stay_days AS INTEGER) AS length_of_stay_days,
    CAST(total_billed_amount AS DOUBLE) AS total_billed_amount,
    submitted_at,
    prior_auth_number,
    CAST(has_experimental_treatment AS INTEGER) AS has_experimental_treatment,
    attending_physician,
    claim_outcome,
    CAST(approved_amount AS DOUBLE) AS approved_amount,
    denial_reasons,
    CAST(days_since_coverage_start AS INTEGER) AS days_since_coverage_start,
    CAST(undisclosed_pre_existing_flag AS INTEGER) AS undisclosed_pre_existing_flag
FROM hive.insurance_leo_trino.ext_claims;

-- Step 4: verify
-- SELECT COUNT(*) FROM hive.insurance_leo_trino.raw_claims;
