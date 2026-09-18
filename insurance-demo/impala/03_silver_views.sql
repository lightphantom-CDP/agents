-- Silver views (Impala)

CREATE VIEW IF NOT EXISTS insurance_leo.claim_procedure_summary AS
SELECT
    claim_id,
    COUNT(*) AS procedure_count,
    SUM(line_total) AS procedure_total,
    SUM(CASE WHEN requires_prior_auth = 1 THEN 1 ELSE 0 END) AS procedures_requiring_auth,
    MAX(CASE WHEN requires_prior_auth = 1 THEN line_total ELSE 0 END) AS max_auth_procedure_cost
FROM insurance_leo.raw_claim_procedures
GROUP BY claim_id;

CREATE VIEW IF NOT EXISTS insurance_leo.claim_bill_summary AS
SELECT
    claim_id,
    COUNT(*) AS bill_line_count,
    SUM(amount) AS bill_total,
    SUM(CASE WHEN is_experimental = 1 THEN amount ELSE 0 END) AS experimental_bill_amount,
    SUM(CASE WHEN line_category = 'surgery' THEN amount ELSE 0 END) AS surgery_amount,
    SUM(CASE WHEN line_category = 'pharmacy' THEN amount ELSE 0 END) AS pharmacy_amount
FROM insurance_leo.raw_hospital_bills
GROUP BY claim_id;

CREATE VIEW IF NOT EXISTS insurance_leo.member_history_summary AS
SELECT
    member_id,
    COUNT(*) AS history_condition_count,
    SUM(CASE WHEN is_pre_existing = 1 THEN 1 ELSE 0 END) AS pre_existing_count,
    SUM(CASE WHEN is_pre_existing = 1 AND disclosed_on_enrollment = 0 THEN 1 ELSE 0 END) AS undisclosed_pre_existing_count
FROM insurance_leo.raw_medical_history
GROUP BY member_id;

CREATE VIEW IF NOT EXISTS insurance_leo.silver_claims_enriched AS
SELECT
    c.claim_id,
    c.member_id,
    c.policy_id,
    c.hospital_id,
    c.hospital_name,
    c.admission_type,
    c.admission_date,
    c.discharge_date,
    c.length_of_stay_days,
    c.total_billed_amount,
    c.submitted_at,
    c.prior_auth_number,
    CASE WHEN c.prior_auth_number IS NOT NULL AND c.prior_auth_number <> '' THEN 1 ELSE 0 END AS has_prior_auth,
    c.has_experimental_treatment,
    c.claim_outcome,
    c.approved_amount,
    c.denial_reasons,
    c.days_since_coverage_start,
    c.undisclosed_pre_existing_flag,
    d.icd10_code,
    d.diagnosis_description,
    d.diagnosis_category,
    d.is_chronic_related,
    p.plan_type,
    p.annual_coverage_limit,
    p.annual_deductible,
    p.deductible_used_ytd,
    p.waiting_period_days,
    p.pre_auth_threshold,
    p.maternity_covered,
    p.mental_health_covered,
    p.experimental_treatment_covered,
    p.policy_status,
    m.age,
    m.gender,
    m.region,
    m.smoker_flag,
    m.bmi_category,
    COALESCE(proc.procedure_count, 0) AS procedure_count,
    COALESCE(proc.procedure_total, 0) AS procedure_total,
    COALESCE(proc.procedures_requiring_auth, 0) AS procedures_requiring_auth,
    COALESCE(bill.experimental_bill_amount, 0) AS experimental_bill_amount,
    COALESCE(bill.surgery_amount, 0) AS surgery_amount,
    COALESCE(hist.pre_existing_count, 0) AS pre_existing_count,
    COALESCE(hist.undisclosed_pre_existing_count, 0) AS undisclosed_pre_existing_count
FROM insurance_leo.raw_claims c
LEFT JOIN insurance_leo.raw_claim_diagnoses d
    ON c.claim_id = d.claim_id AND d.is_primary = 1
LEFT JOIN insurance_leo.raw_policies p
    ON c.policy_id = p.policy_id
LEFT JOIN insurance_leo.raw_members m
    ON c.member_id = m.member_id
LEFT JOIN insurance_leo.claim_procedure_summary proc
    ON c.claim_id = proc.claim_id
LEFT JOIN insurance_leo.claim_bill_summary bill
    ON c.claim_id = bill.claim_id
LEFT JOIN insurance_leo.member_history_summary hist
    ON c.member_id = hist.member_id;
