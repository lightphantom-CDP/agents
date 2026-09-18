-- Bronze staging: external CSV tables (Trino CSV = VARCHAR columns only)
-- Proper types are applied in 02_bronze_iceberg_tables.sql (CAST on CTAS)

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_members (
    member_id       VARCHAR,
    full_name       VARCHAR,
    date_of_birth   VARCHAR,
    age             VARCHAR,
    gender          VARCHAR,
    region          VARCHAR,
    smoker_flag     VARCHAR,
    bmi_category    VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/members',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_policies (
    policy_id                         VARCHAR,
    member_id                         VARCHAR,
    plan_type                         VARCHAR,
    annual_coverage_limit             VARCHAR,
    annual_deductible                 VARCHAR,
    deductible_used_ytd               VARCHAR,
    waiting_period_days               VARCHAR,
    coverage_start_date               VARCHAR,
    coverage_end_date                 VARCHAR,
    pre_auth_threshold                VARCHAR,
    maternity_covered                 VARCHAR,
    dental_covered                    VARCHAR,
    mental_health_covered             VARCHAR,
    experimental_treatment_covered    VARCHAR,
    policy_status                     VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/policies',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_medical_history (
    history_id                VARCHAR,
    member_id                 VARCHAR,
    condition_code            VARCHAR,
    condition_name            VARCHAR,
    diagnosed_date            VARCHAR,
    is_chronic                VARCHAR,
    disclosed_on_enrollment   VARCHAR,
    is_pre_existing           VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/medical_history',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_claims (
    claim_id                          VARCHAR,
    member_id                         VARCHAR,
    policy_id                         VARCHAR,
    hospital_id                       VARCHAR,
    hospital_name                     VARCHAR,
    admission_type                    VARCHAR,
    admission_date                    VARCHAR,
    discharge_date                    VARCHAR,
    length_of_stay_days               VARCHAR,
    total_billed_amount               VARCHAR,
    submitted_at                      VARCHAR,
    prior_auth_number                 VARCHAR,
    has_experimental_treatment        VARCHAR,
    attending_physician               VARCHAR,
    claim_outcome                     VARCHAR,
    approved_amount                   VARCHAR,
    denial_reasons                    VARCHAR,
    days_since_coverage_start         VARCHAR,
    undisclosed_pre_existing_flag     VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/claims',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_claim_diagnoses (
    claim_id                VARCHAR,
    icd10_code              VARCHAR,
    diagnosis_description   VARCHAR,
    diagnosis_category      VARCHAR,
    is_primary              VARCHAR,
    is_chronic_related      VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/claim_diagnoses',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_claim_procedures (
    claim_id                VARCHAR,
    procedure_code          VARCHAR,
    procedure_description   VARCHAR,
    quantity                VARCHAR,
    unit_price              VARCHAR,
    line_total              VARCHAR,
    requires_prior_auth     VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/claim_procedures',
    skip_header_line_count = 1
);

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.ext_hospital_bills (
    bill_line_id    VARCHAR,
    claim_id        VARCHAR,
    line_category   VARCHAR,
    description     VARCHAR,
    amount          VARCHAR,
    is_experimental VARCHAR
)
WITH (
    format = 'CSV',
    external_location = '${RAW_BASE}/hospital_bills',
    skip_header_line_count = 1
);
