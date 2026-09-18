# MediShield Hospital Claims Policy (Demo)

Version: 2026.1
Audience: Medical claims review and AI agent reviewers

## 1. Purpose
This policy governs automated and manual decisions for inpatient, outpatient, and emergency hospital claims.

## 2. Covered services by plan

### Basic plan
- Annual limit: USD 15,000
- Waiting period: 90 days from coverage start
- Maternity, dental, mental health, and experimental treatments are excluded
- Prior authorization required for procedures over USD 3,000

### Standard plan
- Annual limit: USD 50,000
- Waiting period: 30 days
- Maternity and mental health covered; dental and experimental excluded
- Prior authorization required over USD 8,000

### Premium plan
- Annual limit: USD 200,000
- No waiting period
- Full coverage including maternity, dental, mental health, and approved experimental therapies
- Prior authorization required over USD 25,000

## 3. Automatic approval criteria
Approve when ALL of the following are true:
- Policy status is active
- Waiting period has elapsed
- Diagnosis and procedures are covered under the member plan
- Prior authorization is on file when billed amount exceeds plan threshold
- Total claim is within remaining annual limit
- No undisclosed pre-existing condition matches the primary diagnosis

## 4. Automatic rejection criteria
Reject when ANY of the following apply:
- Policy is lapsed or inactive
- Service date falls inside the waiting period
- Primary diagnosis relates to an undisclosed pre-existing condition
- Experimental treatment on Basic or Standard plans
- Maternity claim on a plan without maternity coverage
- Mental health claim on Basic plan

## 5. Manual review triggers
Route to clinical review when:
- Claim amount is between 60% and 90% of remaining annual limit
- Multiple high-cost procedures on the same admission
- Conflicting diagnosis and procedure codes
- Readmission within 7 days for the same diagnosis category

## 6. Partial approval rules
- Apply partial approval when medically necessary services are mixed with excluded line items
- Document each excluded line item in the denial reasons
- Member pays deductible before insurer share is calculated

## 7. Emergency admission override
Emergency admissions may bypass prior authorization requirements, but:
- Documentation must confirm emergency presentation
- Experimental treatments remain excluded unless Premium plan
- Annual limit still applies

## 8. Claim review transparency
Every decision must cite specific policy sections and clinical factors.
Generic denials such as "not covered" without diagnosis or policy reference are not acceptable.

## 9. Model and agent governance
- Champion claim review model must be registered in Cloudera AI Registry
- Feature tables must be sourced from governed Iceberg gold tables only
- Agent decisions must include: outcome, approved amount, policy citations, and top risk factors
