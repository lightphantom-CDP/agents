# NovaBank Credit Policy (Demo)

Version: 2026.1
Audience: Retail lending underwriters

## 1. Purpose
This policy governs automated and manual credit decisions for personal loans up to USD 25,000.

## 2. Thin-file applicants
An applicant is thin-file when credit_history_months < 12.

Rules:
- If model default probability > 0.65, route to manual review.
- Require 2 additional bank statements when cash_flow_stability_score < 0.50.
- Utility payment on-time percentage below 0.80 requires income verification.

## 3. Automated decision tiers
- Approve: default probability <= 0.35 and debt_to_income_ratio <= 0.45
- Review: default probability between 0.36 and 0.65, or thin_file = 1 with probability <= 0.55
- Decline: default probability > 0.65, or prior_default_flag = 1 with probability > 0.40

## 4. Maximum exposure
- Maximum debt_to_income_ratio for approval: 0.45
- Maximum requested_loan_amount for gig_worker without co-signer: USD 10,000
- Maximum inquiry_count_90d for auto-approval: 3

## 5. Adverse action requirements
Decline notices must cite specific contributing factors such as:
- recent credit inquiries
- unstable cash inflow patterns
- high debt-to-income ratio
- prior default history

Generic reasons like "credit history" alone are not acceptable.

## 6. Fraud and device trust
- device_trust_score < 0.55 requires step-up authentication
- More than 2 international transactions in 30 days triggers fraud review

## 7. Model governance
- Champion model must be registered in Cloudera AI Registry
- Any model promotion requires validation AUC >= 0.72 on holdout thin-file segment
- Feature tables must be sourced from governed Iceberg gold tables only
