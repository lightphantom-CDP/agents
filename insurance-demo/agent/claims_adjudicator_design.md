# Claim Review Copilot — Agent Design

## Phased approach

| Phase | Brain | Status |
|---|---|---|
| **Phase 1** | **Gemini API** | `agent/gemini_adjudicator.py`, `DEPLOY-GEMINI.md` |
| **Policy RAG** | **Qdrant CAI App + OpenAI embeddings** | `agent/qdrant_policy_rag.py`, `DEPLOY-QDRANT-CAI.md` (not RAG Studio) |
| **Phase 2** | **CAI Inference + Hugging Face** | Llama 3.1 8B replaces external Gemini |

Data layer is the same in both phases: `hive.insurance_leo_trino.claim_features_v1` + `coverage_policy.md`.

The optional tabular model (`cai/train_and_register.py`) is separate — only needed if you want ML probability scores alongside the LLM.

---

## Hugging Face model picks for CAI Inference (Phase 2)

Cloudera AI Inference supports **text-generation LLMs** via Model Hub (NVIDIA NIM) or Hugging Face import (vLLM backend). Pick based on your GPU.

| Priority | Model | Hugging Face repo | Best for | Typical GPU |
|---|---|---|---|---|
| **Recommended** | Llama 3.1 8B Instruct | `meta-llama/Llama-3.1-8B-Instruct` | Agent reasoning, policy citations, structured output | 1× GPU (Model Hub NIM) |
| Budget / fast demo | Llama 3.2 3B Instruct | `meta-llama/Llama-3.2-3B-Instruct` | Workshop, lower latency | 1× small GPU |
| Strong reasoning | Qwen2.5 7B Instruct | `Qwen/Qwen2.5-7B-Instruct` | Complex multi-flag claim review, good JSON | 1× GPU |
| Proven NIM option | Mistral 7B Instruct v0.3 | `mistralai/Mistral-7B-Instruct-v0.3` | Stable instruct model in Model Hub | 1× GPU |
| Higher quality | Qwen2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct` | Best open-model quality for demo | 2+ GPUs |

**Our pick for your insurance claim review demo:** start with **`meta-llama/Llama-3.1-8B-Instruct`** — best balance of quality, Model Hub support, and single-GPU deploy.

**Notes:**
- Llama models are **gated** — accept license on Hugging Face + use HF token on import.
- Prefer models listed in **Cloudera Model Hub** first (pre-tested GPU profiles).
- CAI Inference HF import is for **LLM reasoning**, not tabular XGBoost — keep those as different artifacts.
- Do **not** import embedding-only or vision-only models for this text claim review use case.

### Phase 2 import flow

```text
Cloudera Console → Model Hub → Import (e.g. Llama 3.1 8B)
    → AI Registry → Deploy on CAI Inference
    → Agent Studio: point LLM tool to inference endpoint instead of Gemini API
```

---

## Goal

Give a claims adjuster an AI copilot that can:

1. Look up a hospital claim by `claim_id`
2. Return model prediction + confidence
3. Explain top risk flags (prior auth, pre-existing, waiting period)
4. Cite insurer policy from RAG
5. Recommend approve / partial / reject / manual review with reasons

## Recommended workflow

```text
User question
    -> Manager Agent
        -> Feature Lookup Tool (SQL on gold table)
        -> LLM Reasoning Tool (Gemini API in Phase 1, CAI Inference in Phase 2)
        -> Policy RAG Tool (coverage_policy.md)  [optional — can inline policy in prompt for demo]
        -> Response Composer
```

Optional: add **Scoring Tool** (XGBoost on CAI) for probability scores alongside LLM reasoning.

## Manager Agent system prompt

```text
You are MediClaim Review Copilot for hospital insurance claims.

Rules:
- Never recommend approve/reject without showing predicted outcome and top 3 risk flags.
- Always cite specific policy sections when denying or partially approving.
- If undisclosed_pre_existing_flag = 1, explain the pre-existing condition rule.
- If missing_prior_auth_flag = 1, cite prior authorization requirements.
- If experimental_not_covered_flag = 1, cite experimental treatment exclusion.
- If the model says manual_review, say so explicitly and list what a human should check.
- If data is missing, ask for claim_id.
```

## Tools to configure

### 1. Feature Lookup Tool

- **Type:** SQL tool (Trino / CDW)
- **Input:** `claim_id`
- **Source:** `hive.insurance_leo_trino.claim_features_v1`

```sql
SELECT *
FROM hive.insurance_leo_trino.claim_features_v1
WHERE claim_id = '{{claim_id}}'
LIMIT 1;
```

### 2. Scoring Tool

- **Type:** Inference endpoint tool
- **Endpoint:** `claim-adjudication-xgb-v1`
- **Input:** feature vector from gold table
- **Output:** `predicted_outcome`, `class_probabilities`

### 3. Policy RAG Tool

- **Type:** RAG Studio knowledge base
- **Documents:** `data/policy/coverage_policy.md` (uploaded to S3 / RAG index)
- **Use for:** waiting period, prior auth thresholds, pre-existing rules, experimental exclusions

### 4. Bill Detail Tool (optional)

- **Type:** SQL tool on silver/raw for line-item drill-down

```sql
SELECT line_category, description, amount, is_experimental
FROM hive.insurance_leo_trino.raw_hospital_bills
WHERE claim_id = '{{claim_id}}'
ORDER BY amount DESC
LIMIT 20;
```

## Demo prompts

1. `Review claim CLM-50005 — should we approve?`
2. `Why was CLM-50021 rejected? Cite policy.`
3. `CLM-50003 is partial approval — what flags triggered it?`
4. `What policy rule applies to experimental treatment on CLM-50001?`

## Sample expected response shape

```text
Claim: CLM-50021
Predicted outcome: rejected (confidence 0.87)

Key flags:
- undisclosed_pre_existing_flag = 1
- missing_prior_auth_flag = 1
- experimental_not_covered_flag = 1

Policy citations:
- Section 4.2: Pre-existing conditions not disclosed at enrollment
- Section 6.1: Prior authorization required above threshold

Recommendation: Reject. Draft denial letter citing undisclosed pre-existing condition.
```
