-- Run ONE block at a time in Hue → Impala (select block → Execute)
-- Skip ext_hospital_bills — already exists

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_members (
    member_id STRING, full_name STRING, date_of_birth STRING, age INT,
    gender STRING, region STRING, smoker_flag INT, bmi_category STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/members'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_policies (
    policy_id STRING, member_id STRING, plan_type STRING,
    annual_coverage_limit DOUBLE, annual_deductible DOUBLE, deductible_used_ytd DOUBLE,
    waiting_period_days INT, coverage_start_date STRING, coverage_end_date STRING,
    pre_auth_threshold DOUBLE, maternity_covered INT, dental_covered INT,
    mental_health_covered INT, experimental_treatment_covered INT, policy_status STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/policies'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_medical_history (
    history_id STRING, member_id STRING, condition_code STRING, condition_name STRING,
    diagnosed_date STRING, is_chronic INT, disclosed_on_enrollment INT, is_pre_existing INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/medical_history'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_claims (
    claim_id STRING, member_id STRING, policy_id STRING, hospital_id STRING,
    hospital_name STRING, admission_type STRING, admission_date STRING, discharge_date STRING,
    length_of_stay_days INT, total_billed_amount DOUBLE, submitted_at STRING,
    prior_auth_number STRING, has_experimental_treatment INT, attending_physician STRING,
    claim_outcome STRING, approved_amount DOUBLE, denial_reasons STRING,
    days_since_coverage_start INT, undisclosed_pre_existing_flag INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/claims'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_claim_diagnoses (
    claim_id STRING, icd10_code STRING, diagnosis_description STRING,
    diagnosis_category STRING, is_primary INT, is_chronic_related INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/claim_diagnoses'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS insurance_leo.ext_claim_procedures (
    claim_id STRING, procedure_code STRING, procedure_description STRING,
    quantity INT, unit_price DOUBLE, line_total DOUBLE, requires_prior_auth INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3a://lhdemocdpbca1/insurancedemo/raw/claim_procedures'
TBLPROPERTIES ('skip.header.line.count'='1');
