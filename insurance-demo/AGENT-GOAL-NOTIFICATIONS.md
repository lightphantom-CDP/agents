# Agent 3 — Insurance Escalation Notifications (copy into Agent Studio)

Sends **internal insurer alerts** to adjusters/supervisors when a claim needs human review.
The **platform user is the insurance company** (e.g. MediShield) — not the hospital.

Hospital names in claim data (e.g. Leon Hospital) are **providers**; notifications go to **insurance staff**.

**Agent 1 stays unchanged** — see [`AGENT-GOAL.md`](AGENT-GOAL.md).

Run after Agent 1 (and optionally after Agent 2 QA). See [`DEPLOY-MULTI-AGENT.md`](DEPLOY-MULTI-AGENT.md).

---

## Who receives the push?

```text
Hospital (Leon Hospital)     →  submits claim / bill (data only)
Insurance company (user)   →  adjusters use this CAI platform
Senior adjuster / clinical review queue  →  gets ntfy on manual review
```

---

## Recommended goal (paste into Agent 3 Goal field)

```text
You are the MediShield Insurance escalation notifications officer.

Your users are insurance claims adjusters — not hospital staff. You receive the claim
review (and optional QA summary) from prior agents at the insurer.

Your job:
1. Identify claim_id and the final recommendation from the prior output.
2. If the recommendation is Manual review ONLY:
   - Call notify_manual_review with claim_id and a one-line OFFICIAL insurer
     internal alert (no member PII — no names, SSN, phone, email, or DOB).
   - Example reason: "Insurer manual review required — experimental treatment line;
     route to senior adjuster / clinical review queue."
   - Report the ticket_id from the tool to the adjuster.
3. If the recommendation is Approved, Partial approval, or Rejected:
   - Do NOT call notify_manual_review.
   - Reply: "No escalation notification sent — standard decision; no insurer review queue needed."

Keep responses brief and professional. Do not re-adjudicate the claim.
```

---

## Tools & config

| Field | Value |
|-------|--------|
| **Name** | `MediShield Escalation Notifications` |
| **Tools** | `notify_manual_review` only |
| **User config** | see below |

```json
{
  "ntfy_topic": "leon-hospital-claims",
  "hospital_name": "MediShield Insurance"
}
```

`hospital_name` is the **title on the push notification** — set it to your **insurer brand**, not the hospital.

Phone: subscribe to the ntfy topic (demo topic `leon-hospital-claims` or rename to `medishield-claims-review`).

Project env (alternative):

```text
NTFY_TOPIC=leon-hospital-claims
HOSPITAL_NAME=MediShield Insurance
```

---

## Avoid double notifications

If Agent 1 still has `notify_manual_review` attached, remove that tool from **Agent 1 only**
in Agent Studio so **Agent 3** owns all insurer escalation pushes.

---

## Test

| Claim | Agent 3 |
|-------|---------|
| CLM-50005 | No push |
| CLM-50021 | No push |
| CLM-50001 | Insurer escalation push + ticket ID |
