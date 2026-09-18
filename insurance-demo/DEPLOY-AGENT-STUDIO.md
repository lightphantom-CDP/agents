# Deploy Claim Review Copilot — Agent Studio

Build the agent after:
- ✅ Trino pipeline complete (`claim_features_v1`, 4912 rows)
- ✅ Gemini API tested in CAI Workbench

---

## Architecture

```text
User: "Review claim CLM-50021"
        │
        ▼
┌─────────────────────────────────────┐
│  Agent Studio — MediClaim Copilot   │
│                                     │
│  Tool 1: SQL Lookup (CDW/Trino)     │──► claim_features_v1
│  Tool 2: Policy RAG                 │──► coverage_policy.md
│  LLM: Gemini 3.1 Pro (or CAI later) │
└─────────────────────────────────────┘
        │
        ▼
Outcome + flags + policy citations + next action
```

---

## Step 1 — Upload policy document for RAG

Upload to your project or S3:

```text
insurance-demo/data/policy/coverage_policy.md
```

In **Agent Studio → Knowledge / RAG**:
1. Create knowledge base: `medishield-policy`
2. Add document: `coverage_policy.md`
3. Index / embed

---

## Step 2 — Create SQL tool (claim lookup)

**Tool name:** `lookup_claim_features`

**Type:** SQL tool (Trino / CDW connection — same as Hue)

**Parameter:** `claim_id` (string)

**SQL:**

```sql
SELECT
    claim_id,
    member_id,
    policy_id,
    icd10_code,
    diagnosis_category,
    admission_type,
    length_of_stay_days,
    total_billed_amount,
    procedure_total,
    plan_type,
    annual_coverage_limit,
    pre_auth_threshold,
    waiting_period_days,
    policy_status,
    has_prior_auth,
    has_experimental_treatment,
    days_since_coverage_start,
    undisclosed_pre_existing_flag,
    undisclosed_pre_existing_count,
    waiting_period_violation,
    missing_prior_auth_flag,
    experimental_not_covered_flag,
    maternity_not_covered_flag,
    mental_health_not_covered_flag,
    policy_inactive_flag,
    procedures_requiring_auth,
    age,
    smoker_flag,
    denial_reasons
FROM hive.insurance_leo_trino.claim_features_v1
WHERE claim_id = '{{claim_id}}'
LIMIT 1
```

**Important:** Do **not** include `claim_outcome` or `approved_amount` in the SQL — those are historical labels. The agent should **predict**, not read the answer.

---

## Step 3 — Optional SQL tool (bill lines)

**Tool name:** `lookup_hospital_bills`

```sql
SELECT line_category, description, amount, is_experimental
FROM hive.insurance_leo_trino.raw_hospital_bills
WHERE claim_id = '{{claim_id}}'
ORDER BY amount DESC
LIMIT 20
```

---

## Step 4 — Create the agent

**Name:** `MediClaim Review Copilot`

**Model:** Gemini `gemini-3.1-pro-preview` (or your CAI Inference endpoint later)

**System prompt** — use the human-friendly version in [`AGENT-GOAL.md`](AGENT-GOAL.md) (copy/paste into Agent Studio).

Key behavior change vs the old technical goal:
- Answers use **plain English** for adjusters, not raw field names
- On clean approvals, say **"All standard checks passed"** instead of listing every `= 0` flag
- Still calls `lookup_claim_features` + `search_coverage_policy` under the hood

**Tools to attach:**
- `lookup_claim_features` (required)
- `medishield-policy` RAG (required)
- `lookup_hospital_bills` (optional)

---

## Step 5 — Test prompts

| Prompt | Expected |
|---|---|
| `Review claim CLM-50005 — should we approve?` | **approved** — few flags |
| `Review claim CLM-50021` | **rejected** — pre-existing + prior auth + experimental |
| `Why partial approval on CLM-50003?` | cites `missing_prior_auth_flag` |
| `What should a human check on CLM-50001?` | **manual_review** — experimental + clinical |

---

## Step 6 — Guardrails (recommended)

Enable workflow guardrails in Agent Studio: **Configure → Configure Guardrails**.

See [`DEPLOY-GUARDRAILS.md`](DEPLOY-GUARDRAILS.md) for PII masking, LLM judges, and optional custom guardrail for this demo.

---

## Step 7 — Publish and demo

1. **Test** in Agent Studio chat
2. **Publish** agent for your team
3. **Demo script:**

> "Hospital submits claim CLM-50021. Watch the agent pull governed features from CDW, apply MediShield policy, and recommend reject with citations — in seconds instead of days."

---

## Troubleshooting

| Issue | Fix |
|---|---|
| SQL tool returns empty | Check catalog `hive`, schema `insurance_leo_trino` in tool config |
| SQL tool permission error | Same user/group as Hue — ask admin |
| RAG returns nothing | Re-index `coverage_policy.md` |
| Gemini 404 model error | Use `gemini-3.1-pro-preview`, not `gemini-2.5-pro` |
| Agent reads old outcome | Remove `claim_outcome` from SQL tool SELECT |

---

## Phase 2 upgrades

| Upgrade | When |
|---|---|
| Swap Gemini → CAI Inference (Llama 3.1 8B) | After Model Hub import |
| Add XGBoost scoring tool | Optional probability score |
| Auto-approve workflow | Rule engine on flags = 0 |
| Fix CAI Spark S3 access | Auto-fetch without Hue paste |
