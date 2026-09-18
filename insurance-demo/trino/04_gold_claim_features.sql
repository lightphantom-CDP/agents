-- Gold layer: ML + agent feature table (Iceberg)
-- CAI training source: ${CATALOG}.${DATABASE}.claim_features_v1

CREATE TABLE IF NOT EXISTS ${CATALOG}.${DATABASE}.claim_features_v1
WITH (format = 'PARQUET')
AS
SELECT
    s.claim_id,
    s.member_id,
    s.policy_id,

    -- Clinical
    s.icd10_code,
    s.diagnosis_category,
    s.is_chronic_related,
    s.admission_type,
    s.length_of_stay_days,

    -- Financial
    s.total_billed_amount,
    s.procedure_total,
    s.experimental_bill_amount,
    s.surgery_amount,

    -- Policy coverage
    s.plan_type,
    s.annual_coverage_limit,
    s.deductible_used_ytd,
    s.waiting_period_days,
    s.pre_auth_threshold,
    s.maternity_covered,
    s.mental_health_covered,
    s.experimental_treatment_covered,
    s.policy_status,

    -- Risk flags
    s.has_prior_auth,
    s.has_experimental_treatment,
    s.days_since_coverage_start,
    s.undisclosed_pre_existing_flag,
    s.undisclosed_pre_existing_count,
    s.procedures_requiring_auth,

    -- Member
    s.age,
    s.smoker_flag,
    s.bmi_category,

    -- Derived features for model / agent
    CASE
        WHEN s.days_since_coverage_start < s.waiting_period_days THEN 1
        ELSE 0
    END AS waiting_period_violation,

    CASE
        WHEN s.total_billed_amount > s.pre_auth_threshold AND s.has_prior_auth = 0 THEN 1
        ELSE 0
    END AS missing_prior_auth_flag,

    CASE
        WHEN s.has_experimental_treatment = 1 AND s.experimental_treatment_covered = 0 THEN 1
        ELSE 0
    END AS experimental_not_covered_flag,

    CASE
        WHEN s.diagnosis_category = 'maternity' AND s.maternity_covered = 0 THEN 1
        ELSE 0
    END AS maternity_not_covered_flag,

    CASE
        WHEN s.diagnosis_category = 'mental_health' AND s.mental_health_covered = 0 THEN 1
        ELSE 0
    END AS mental_health_not_covered_flag,

    CASE
        WHEN s.policy_status <> 'active' THEN 1
        ELSE 0
    END AS policy_inactive_flag,

    -- Label for supervised learning
    s.claim_outcome,
    s.approved_amount,
    s.denial_reasons,

    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS feature_built_at
FROM ${CATALOG}.${DATABASE}.silver_claims_enriched s;

-- Verify
-- SELECT claim_outcome, COUNT(*) FROM ${CATALOG}.${DATABASE}.claim_features_v1 GROUP BY 1;
-- SELECT * FROM ${CATALOG}.${DATABASE}.claim_features_v1 WHERE claim_id = 'CLM-50021';
