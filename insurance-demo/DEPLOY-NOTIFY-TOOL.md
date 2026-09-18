# Manual review notifications — Python tool (no MCP)

Use this path for the demo when MCP/`uvx` blocks the workflow.

```text
Insurance Claim Reviewer (Gemini)
  ├── lookup_claim_features
  ├── search_coverage_policy
  └── notify_manual_review          ← ntfy push (manual review only)
```

**No MCP server required.**

---

## Step 1 — Remove MCP from agent

1. Agent Studio → **Insurance Claim Reviewer**
2. **Remove** `leon_hospital_notify` MCP server
3. **Save**

---

## Step 2 — Create Python tool in Tools Catalog

**Name:** `notify_manual_review`

Upload from repo:

```text
agent/tools/notify_manual_review/
  tool.py
  notify_lib.py
  requirements.txt
```

**User config (JSON):**

```json
{
  "ntfy_topic": "leon-hospital-claims",
  "hospital_name": "Leon Hospital"
}
```

Or set on the **workflow / project** env:

```text
NTFY_TOPIC=leon-hospital-claims
HOSPITAL_NAME=Leon Hospital
```

---

## Step 3 — Attach tool to agent

Attach all **3 Python tools**:

| Tool | When |
|------|------|
| `lookup_claim_features` | Every claim |
| `search_coverage_policy` | Every claim |
| `notify_manual_review` | **Manual review only** (e.g. CLM-50001) |

Update **Goal** from [`AGENT-GOAL.md`](AGENT-GOAL.md) (notify section references `notify_manual_review`, not MCP).

---

## Step 4 — Phone setup

1. Install [ntfy app](https://ntfy.sh)
2. Subscribe to topic: **`leon-hospital-claims`**

---

## Step 5 — Redeploy workflow

1. **Save** agent
2. **Deploy** workflow → wait **Running**
3. **Test tab:** `Review claim CLM-50005` → should answer in ~30–60s
4. **Test tab:** `Review claim CLM-50001` → manual review + ticket ID + phone push

---

## claim-review-ui (optional backup notify)

The UI can also push when it detects "manual review" in the agent response:

```text
NTFY_TOPIC=leon-hospital-claims
HOSPITAL_NAME=Leon Hospital
NOTIFY_ENABLED=true
USE_MCP_NOTIFY=false
```

Restart claim-review-ui after changing env vars.

---

## Test prompts

| Prompt | Expected | ntfy? |
|--------|----------|-------|
| `Review claim CLM-50005` | Approved | No |
| `Review claim CLM-50021` | Rejected | No |
| `Review claim CLM-50001` | Manual review | **Yes** |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Workflow timeout / loop | Confirm MCP is **removed**; redeploy |
| `dry_run: true` in tool output | Set `NTFY_TOPIC` in tool user config or project env |
| No phone push | Subscribe to `leon-hospital-claims` in ntfy app |
| Agent skips notify on CLM-50001 | Goal must say call `notify_manual_review` on manual review only |
