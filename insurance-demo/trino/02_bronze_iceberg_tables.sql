-- Bronze Iceberg: cast VARCHAR staging CSV to proper types
-- CDW hive catalog: do not use "location" property (not supported)
-- Run ONE CREATE block at a time in Hue

-- Tip: if a raw_* table has 0 rows, run: DROP TABLE hive.insurance_leo_trino.raw_<name>;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_members
WITH (format = 'PARQUET')
AS
SELECT
    member_id,
    full_name,
    date_of_birth,
    CAST(age AS INTEGER) AS age,
    gender,
    region,
    CAST(smoker_flag AS INTEGER) AS smoker_flag,
    bmi_category
FROM ${CATALOG}.${DATABASE}.ext_members;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_policies
WITH (format = 'PARQUET')
AS
SELECT
    policy_id,
    member_id,
    plan_type,
    CAST(annual_coverage_limit AS DOUBLE) AS annual_coverage_limit,
    CAST(annual_deductible AS DOUBLE) AS annual_deductible,
    CAST(deductible_used_ytd AS DOUBLE) AS deductible_used_ytd,
    CAST(waiting_period_days AS INTEGER) AS waiting_period_days,
    coverage_start_date,
    coverage_end_date,
    CAST(pre_auth_threshold AS DOUBLE) AS pre_auth_threshold,
    CAST(maternity_covered AS INTEGER) AS maternity_covered,
    CAST(dental_covered AS INTEGER) AS dental_covered,
    CAST(mental_health_covered AS INTEGER) AS mental_health_covered,
    CAST(experimental_treatment_covered AS INTEGER) AS experimental_treatment_covered,
    policy_status
FROM ${CATALOG}.${DATABASE}.ext_policies;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_medical_history
WITH (format = 'PARQUET')
AS
SELECT
    history_id,
    member_id,
    condition_code,
    condition_name,
    diagnosed_date,
    CAST(is_chronic AS INTEGER) AS is_chronic,
    CAST(disclosed_on_enrollment AS INTEGER) AS disclosed_on_enrollment,
    CAST(is_pre_existing AS INTEGER) AS is_pre_existing
FROM ${CATALOG}.${DATABASE}.ext_medical_history;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_claims
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
FROM ${CATALOG}.${DATABASE}.ext_claims;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_claim_diagnoses
WITH (format = 'PARQUET')
AS
SELECT
    claim_id,
    icd10_code,
    diagnosis_description,
    diagnosis_category,
    CAST(is_primary AS INTEGER) AS is_primary,
    CAST(is_chronic_related AS INTEGER) AS is_chronic_related
FROM ${CATALOG}.${DATABASE}.ext_claim_diagnoses;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_claim_procedures
WITH (format = 'PARQUET')
AS
SELECT
    claim_id,
    procedure_code,
    procedure_description,
    CAST(quantity AS INTEGER) AS quantity,
    CAST(unit_price AS DOUBLE) AS unit_price,
    CAST(line_total AS DOUBLE) AS line_total,
    CAST(requires_prior_auth AS INTEGER) AS requires_prior_auth
FROM ${CATALOG}.${DATABASE}.ext_claim_procedures;

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.raw_hospital_bills
WITH (format = 'PARQUET')
AS
SELECT
    bill_line_id,
    claim_id,
    line_category,
    description,
    CAST(amount AS DOUBLE) AS amount,
    CAST(is_experimental AS INTEGER) AS is_experimental
FROM ${CATALOG}.${DATABASE}.ext_hospital_bills;
