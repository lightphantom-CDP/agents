-- Impala: materialize Iceberg bronze tables from external CSV staging

CREATE TABLE IF NOT EXISTS insurance_leo.raw_members
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_members'
AS SELECT * FROM insurance_leo.ext_members;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_policies
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_policies'
AS SELECT * FROM insurance_leo.ext_policies;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_medical_history
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_medical_history'
AS SELECT * FROM insurance_leo.ext_medical_history;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_claims
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_claims'
AS SELECT * FROM insurance_leo.ext_claims;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_claim_diagnoses
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_claim_diagnoses'
AS SELECT * FROM insurance_leo.ext_claim_diagnoses;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_claim_procedures
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_claim_procedures'
AS SELECT * FROM insurance_leo.ext_claim_procedures;

CREATE TABLE IF NOT EXISTS insurance_leo.raw_hospital_bills
STORED AS ICEBERG
LOCATION 's3a://lhdemocdpbca1/insurancedemo/iceberg/raw_hospital_bills'
AS SELECT * FROM insurance_leo.ext_hospital_bills;
