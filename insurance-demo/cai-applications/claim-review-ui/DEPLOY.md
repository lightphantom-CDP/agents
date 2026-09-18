# Deploy Claim Review UI — CAI Application

Professional MediShield adjudication UI (Cloudera orange theme) that calls your **deployed Agent Studio workflow**.

```text
Browser  →  CAI Application (this UI)
              →  Agent Studio workflow API
                    → lookup_claim_features (Trino)
                    → search_coverage_policy (Qdrant)
                    → Gemini
```

---

## Step 1 — Deploy Agent Studio workflow first

1. Finish workflow `insuranceagentic-v2` (or your name)
2. **Deploy** from Agent Studio
3. Note the **deployed Application URL** (e.g. `https://insuranceagentic-v2....cloudera.site`)

---

## Step 2 — Create CAI Application

| Setting | Value |
|---|---|
| **Name** | `claim-review-ui` |
| **Subdomain** | `claimreview` (or your choice) |
| **Script** | `cai-applications/claim-review-ui/app.py` |
| **Kernel** | Python 3.10 |
| **Editor** | Script / Workbench (not Jupyter-only) |
| **Spark** | OFF |
| **Resources** | 1 vCPU / 2 GiB |

Upload folder:

```text
cai-applications/claim-review-ui/
  ├── app.py
  ├── guardrails_check.py
  ├── requirements.txt
  ├── static/                    ← REQUIRED for logos (broken images if missing)
  │   ├── cloudera-logo.png
  │   └── leon-hospital-logo.png
  └── templates/
      └── index.html
```

---

## Step 3 — Environment variables

**Application** or **Project** → Environment:

| Variable | Example |
|---|---|
| `WORKFLOW_APP_URL` | From workflow **API Documentation** sidebar (base URL only) |
| `CDSW_API_KEY` | API key from User Settings → API Keys → Create API key |
| `WORKFLOW_INPUT_KEY` | `user_input` (conversational workflow) |
| `WORKFLOW_USE_SESSION` | `false` (only if your deployment requires createSession first) |
| `GUARDRAILS_MODE` | `simple` (or `guardrails_ai` / `off`) — see [`DEPLOY-GUARDRAILS-GUARDRAILSAI.md`](../../DEPLOY-GUARDRAILS-GUARDRAILSAI.md) |
| `CLAIM_REVIEW_UI_DIR` | **Usually omit.** Only for PBJ if auto-detect fails. Must be full path to folder containing `templates/index.html`, e.g. `/home/cdsw/insuranceclaim/claim-review-ui` |

**Do not set `CLAIM_REVIEW_UI_DIR`** unless logos still 404 after upload — a wrong path causes **Internal Server Error**.

**Your workflow base URL (from API docs):**

```text
WORKFLOW_APP_URL=https://workflow-a414db83-6181-42ac-aeb5-bc103129868c.lhworkbench.lhcai.a465-9q4k.cloudera.site
```

Restart the application after saving.

---

## API flow (what the UI does)

**Step 1 — start workflow** (`app.py` calls this on **Run AI review**):

```bash
curl -X POST "https://workflow-a414db83-6181-42ac-aeb5-bc103129868c.lhworkbench.lhcai.a465-9q4k.cloudera.site/api/workflow/kickoff" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CDSW_API_KEY" \
  -d '{"inputs": {
  "user_input": "Review hospital insurance claim CLM-50021.",
  "context": ""
}}'
```

Response includes `trace_id` — use it in step 2.

**Optional — create session** (only when API docs say you need `session_id`):

```bash
curl -X POST "https://workflow-a414db83-6181-42ac-aeb5-bc103129868c.lhworkbench.lhcai.a465-9q4k.cloudera.site/api/workflow/createSession" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CDSW_API_KEY" \
  -d '{}'
```

Set `WORKFLOW_USE_SESSION=true` if your deployment requires this before kickoff.

**Step 2 — get workflow events** (poll until `Crew.complete`):

```bash
curl -X GET "https://workflow-a414db83-6181-42ac-aeb5-bc103129868c.lhworkbench.lhcai.a465-9q4k.cloudera.site/api/workflow/events?trace_id=<trace_id>" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer $CDSW_API_KEY"
```

You do **not** need to run these manually when using the claim-review UI — it runs kickoff + poll on **Run AI review**.

---

## Step 4 — Open UI

Open the application URL from CAI **Applications** tab.

**Chat-style UI (Cloudera theme):**
- Type a message: `Please review claim CLM-50021`
- Or click a **demo claim** in the left sidebar
- **Enter** to send · **Shift+Enter** for new line
- Guardrail blocks show as red system messages

API: `POST /api/chat` with `{"message": "..."}` (also `/api/review` with `claim_id`)

---

## Design tokens (Cloudera)

| Token | Hex | Use |
|---|---|---|
| Cloudera Orange | `#F96702` | Primary actions, accent bar |
| Navy | `#0F1419` | Text |
| Slate | `#1E293B` | Secondary text |
| Background | `#F8FAFC` | Page |
| Success | `#0D7C4E` | Approved |
| Warning | `#B45309` | Partial |
| Danger | `#DC2626` | Rejected |

Font: **IBM Plex Sans** (enterprise, pairs well with CDP UI).

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "Workflow not configured" | Set `WORKFLOW_APP_URL` + `CDSW_API_KEY` |
| 502 / HTTP error on review | Check deployed workflow app is **Running** |
| Timeout | Increase workflow resources; test workflow in Agent Studio first |
| Wrong input field | Set `WORKFLOW_INPUT_KEY` to match workflow Start task input |

---

## Agent test prompts

See [`AGENT-TEST-PROMPTS.md`](../../AGENT-TEST-PROMPTS.md) for full QA checklist.
