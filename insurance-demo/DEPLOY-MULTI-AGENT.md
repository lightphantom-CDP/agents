# Multi-agent workflow — without changing Agent 1 code

Keep **Insurance Claim Reviewer** exactly as today ([`AGENT-GOAL.md`](AGENT-GOAL.md)).
Add agents in Agent Studio UI only.

---

## Recommended layout

```text
User: "Review claim CLM-50001"
        │
        ▼
┌─────────────────────────────────────┐
│ Agent 1: Insurance Claim Reviewer   │  ← UNCHANGED
│ Tools: lookup + search_coverage     │
│        (+ notify if you keep it)    │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ Agent 2: QA Compliance Reviewer     │  ← Option A, no tools
│ Goal: AGENT-GOAL-QA.md              │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ Agent 3: Insurer escalation notify  │  ← optional, ntfy to adjuster queue
│ Tool: notify_manual_review          │
│ Goal: AGENT-GOAL-NOTIFICATIONS.md   │
└─────────────────────────────────────┘
        │
        ▼
   Combined answer to user / UI
```

---

## Minimal add (QA only)

Add **only Agent 2** if you want multi-agent without notifications split:

```text
Agent 1 (unchanged) → Agent 2 QA (no tools)
```

Copy goal from [`AGENT-GOAL-QA.md`](AGENT-GOAL-QA.md).

---

## Full add (QA + official ntfy)

```text
Agent 1 (unchanged) → Agent 2 QA → Agent 3 notify_manual_review
```

1. Create Agent 2 — no tools — [`AGENT-GOAL-QA.md`](AGENT-GOAL-QA.md)
2. Create Agent 3 — `notify_manual_review` — [`AGENT-GOAL-NOTIFICATIONS.md`](AGENT-GOAL-NOTIFICATIONS.md)
3. Workflow: **sequential** crew, each task gets prior output as context
4. Remove `notify_manual_review` from Agent 1 **tool attach list** (optional, avoids double push)

Notify tool setup: [`DEPLOY-NOTIFY-TOOL.md`](DEPLOY-NOTIFY-TOOL.md)

---

## Agent Studio steps

1. **Workflow** → add agents to crew (order: 1 → 2 → 3)
2. **Task 1** — user message → Agent 1
3. **Task 2** — context = Task 1 output → Agent 2
4. **Task 3** — context = Task 1 + Task 2 output → Agent 3
5. **Save** → **Deploy** → test CLM-50005, CLM-50021, CLM-50001

---

## Actors (insurance company platform)

| Actor | Role in demo |
|-------|----------------|
| **MediShield Insurance** | Platform owner — adjusters use CAI |
| **Leon Hospital** | Provider on the claim (data only) |
| **Senior adjuster / clinical queue** | Receives ntfy when Agent 3 escalates |

## What each agent does (elevator pitch)

| Agent | One line |
|-------|----------|
| **1 Claim Reviewer** | Insurer adjuster copilot — Trino facts + policy → decision |
| **2 QA Reviewer** | Internal insurer audit — PASSED / FLAGGED |
| **3 Escalation notify** | Insurer alert to supervisor queue on manual review only |

---

## claim-review-ui

No code change required. UI still calls one workflow kickoff; the crew runs all agents internally.

Env (unchanged):

```text
WORKFLOW_APP_URL=...
CDSW_API_KEY=...
NTFY_TOPIC=leon-hospital-claims
```

---

## Test matrix

| Claim | Agent 1 | Agent 2 | Agent 3 |
|-------|---------|---------|---------|
| CLM-50005 | Approved | PASSED | no push |
| CLM-50021 | Rejected | PASSED | no push |
| CLM-50001 | Manual review | PASSED | ntfy push |
