# Insurance Demo — Gemini API (Phase 1)

Use Gemini first for the claim review agent. Swap to Cloudera AI Inference (Hugging Face) later.

## Architecture (Phase 1)

```text
Trino claim_features_v1  ──►  (manual or SQL tool) claim JSON
coverage_policy.md       ──►  policy text in prompt
                                    │
                                    ▼
                            Gemini API (reasoning + recommendation)
```

Later (Phase 2): replace Gemini with a CAI Inference endpoint hosting an open model from Hugging Face.

---

## Step 1 — Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Export it:

```bash
export GEMINI_API_KEY=your-key-here
```

---

## Step 2 — Install and run locally

```bash
cd insurance-demo
pip install google-generativeai pandas
python3 agent/gemini_adjudicator.py --claim-id CLM-50021
```

### Demo claims

| Claim | Story |
|---|---|
| `CLM-50005` | Fast approve |
| `CLM-50021` | Pre-existing reject |
| `CLM-50003` | Partial / missing prior auth |
| `CLM-50001` | Manual review |

### Try different Gemini models

| Model | Use when |
|---|---|
| **`gemini-3.1-pro-preview`** | **Best quality** — recommended for new API keys (default) |
| `gemini-2.5-flash` | Faster + cheaper fallback |
| `gemini-2.0-flash` | Widest availability fallback |

```bash
python3 agent/gemini_adjudicator.py --claim-id CLM-50021 --model gemini-3.1-pro-preview
python3 agent/gemini_adjudicator.py --claim-id CLM-50021 --model gemini-2.5-flash
```

**Note:** `gemini-2.5-pro` may return 404 for new API keys — use `gemini-3.1-pro-preview` instead.

---

## Step 3 — CAI Workbench with Trino (no CSV upload needed)

If your gold table is already in CDW, use Spark in CAI — **no local CSV required**:

```python
!pip install -q google-generativeai pandas

import os
os.environ["GEMINI_API_KEY"] = "your-key-here"

# Copy agent/gemini_from_trino.py into your CAI project, or paste its functions
from agent.gemini_from_trino import review_claim_with_gemini

print(review_claim_with_gemini("CLM-50021", model="gemini-3.1-pro-preview"))
```

Or inline in one notebook cell:

```python
!pip install -q google-generativeai pandas

import os, json
import google.generativeai as genai

os.environ["GEMINI_API_KEY"] = "your-key-here"
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

claim_id = "CLM-50021"
table = "hive.insurance_leo_trino.claim_features_v1"

df = spark.sql(f"SELECT * FROM {table} WHERE claim_id = '{claim_id}' LIMIT 1").toPandas()
features = df.iloc[0].to_dict()

policy = """
# MediShield Policy (paste full coverage_policy.md here, or upload the file)
- Waiting period must elapse.
- Prior auth required above threshold.
- Undisclosed pre-existing = reject.
- Experimental excluded unless covered.
"""

model = genai.GenerativeModel("gemini-3.1-pro-preview")
response = model.generate_content(
    f"Review claim. Features: {json.dumps(features, default=str)}\n\nPolicy:\n{policy}"
)
print(response.text)
```

---

## Step 4 — Wire to Trino (optional, in agent)

When building the full agent, replace local CSV lookup with SQL on gold table:

```sql
SELECT *
FROM hive.insurance_leo_trino.claim_features_v1
WHERE claim_id = 'CLM-50021'
LIMIT 1;
```

Pass the JSON result + `coverage_policy.md` into the Gemini prompt (same pattern as `agent/gemini_adjudicator.py`).

---

## Phase 2 — Cloudera AI Inference (Hugging Face)

See `DEPLOY-CAI.md` and model recommendations in `agent/claims_adjudicator_design.md`.

The tabular XGBoost model (`cai/train_and_register.py`) is optional. The LLM path (Gemini now, HF later) can reason directly from `claim_features_v1` without a separate classifier.
