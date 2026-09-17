# Credit Copilot — Agent Studio Design

Use this document when building the Agent Studio workflow in Cloudera AI.

## Goal

Give a loan officer a governed copilot that can:

1. Look up an applicant
2. Return model score + decision tier
3. Explain top risk drivers
4. Cite bank policy from RAG
5. Draft an adverse-action notice when needed

## Recommended workflow

```text
User question
    -> Manager Agent
        -> Feature Lookup Tool
        -> Scoring Tool
        -> Explainability Tool
        -> Policy RAG Tool
        -> Response Composer
```

## Manager Agent system prompt

```text
You are NovaBank Credit Copilot, an assistant for retail loan underwriters.

Rules:
- Never approve or decline without showing default probability and top 3 contributing factors.
- For thin-file applicants, always cite the thin-file section of credit policy.
- Use specific adverse-action language; do not use vague reasons like "credit history".
- If policy requires manual review, say so explicitly.
- If data is missing, ask for application_id.
```

## Tools to configure

### 1. Feature Lookup Tool

- **Type:** Python function or SQL tool
- **Input:** `application_id`
- **Source:** `hive.credit_demo.credit_features_v1`
- **Output fields:** income, DTI, thin_file, utility_on_time_pct, cash_flow_stability_score

Example SQL:

```sql
SELECT *
FROM hive.credit_demo.credit_features_v1
WHERE application_id = '{{application_id}}'
LIMIT 1;
```

### 2. Scoring Tool

- **Type:** Inference endpoint tool
- **Endpoint:** `credit-default-xgb-v1`
- **Input:** feature vector from gold table or batch score CSV
- **Output:** `default_probability`, `decision_tier`

Decision tiers:

| Tier | Rule |
|---|---|
| approve | probability <= 0.35 and DTI <= 0.45 |
| review | probability <= 0.65 or thin-file with probability <= 0.55 |
| decline | probability > 0.65 |

### 3. Explainability Tool

- **Type:** Python tool wrapping `cai/shap_explainer.py`
- **Input:** `application_id`
- **Output:** top 3 SHAP reasons + adverse-action draft

### 4. Policy RAG Tool

- **Type:** RAG Studio knowledge base
- **Documents:** `data/policy/credit_policy.md`
- **Use for:** thin-file rules, DTI limits, decline wording requirements

Suggested retrieval prompts:

- "What is the manual review threshold for thin-file applicants?"
- "What reasons are acceptable in an adverse action notice?"
- "What is the max loan amount for gig workers?"

## Demo prompts

Use these during the workshop:

1. `Review applicant APP-10482 for a USD 15,000 personal loan.`
2. `Why is APP-10110 in review instead of approve?`
3. `Draft an adverse action notice for APP-10225 with policy-compliant wording.`
4. `What documents do we need for thin-file applicant APP-10055?`

## Sample expected response shape

```json
{
  "application_id": "APP-10482",
  "default_probability": 0.71,
  "decision_tier": "decline",
  "top_reasons": [
    "recent credit inquiries increased default risk",
    "unstable cash inflow patterns increased default risk",
    "high debt-to-income ratio increased default risk"
  ],
  "policy_citations": [
    "Thin-file applicants with probability > 0.65 require manual review or decline.",
    "Generic decline reasons are not acceptable."
  ],
  "recommended_action": "Decline and send specific adverse-action notice."
}
```

## RBAC suggestion

| Role | Access |
|---|---|
| Underwriter | run workflow, view explanations |
| Team lead | edit workflow, view evaluations |
| Auditor | read-only deployed workflow history |

## Evaluation cases

Create 10 workflow evaluations in Agent Studio:

| Prompt | Expected contains |
|---|---|
| Review APP-10482 | probability, review or decline, 3 reasons |
| Explain thin-file rule | credit_history_months < 12 |
| Draft adverse action | specific factor wording |
| Gig worker max loan | USD 10,000 |
| Device trust low | step-up authentication |

## MCP stretch goal

If MCP is enabled in your environment, expose:

- `get_credit_features(application_id)`
- `score_application(application_id)`
- `explain_application(application_id)`

Then the copilot can call Cloudera data services as native tools.
