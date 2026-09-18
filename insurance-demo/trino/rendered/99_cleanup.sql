-- Reset insurance_leo_trino for a fresh Trino run (Hue → Trino, dropdown = hive.insurance_leo_trino)
-- Run this entire file ONCE before starting from scratch.

DROP VIEW IF EXISTS hive.insurance_leo_trino.silver_claims_enriched;
DROP VIEW IF EXISTS hive.insurance_leo_trino.claim_procedure_summary;
DROP VIEW IF EXISTS hive.insurance_leo_trino.claim_bill_summary;
DROP VIEW IF EXISTS hive.insurance_leo_trino.member_history_summary;

DROP TABLE IF EXISTS hive.insurance_leo_trino.claim_features_v1;

DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_members;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_policies;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_medical_history;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_claims;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_claim_diagnoses;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_claim_procedures;
DROP TABLE IF EXISTS hive.insurance_leo_trino.raw_hospital_bills;

DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_members;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_policies;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_medical_history;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_claims;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_claim_diagnoses;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_claim_procedures;
DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_hospital_bills;
