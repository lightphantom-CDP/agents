# Agent Studio Python Tools

Each tool = one folder with `tool.py` + `requirements.txt`.

Copy into Agent Studio workflow **Tools** (same structure as `lookup_claim_features_nk6Ff7Wa/`).

## Tool 1 — `lookup_claim_features`

| File | Purpose |
|---|---|
| `tool.py` | Fetch one claim from `claim_features_v1` |
| `requirements.txt` | pandas, pyarrow, pydantic |

**User config (live Trino — preferred):**

```json
{
  "gold_table": "hive.insurance_leo_trino.claim_features_v1",
  "trino_host": "YOUR_TRINO_COORDINATOR_HOST",
  "trino_port": 443,
  "trino_user": "cdsw",
  "use_demo_fallback": false
}
```

See `DEPLOY-TRINO-AGENT.md` for how to find the Trino host (not the Hue URL).

**Tool input:** `claim_id` e.g. `CLM-50021`

## Tool 2 — `search_coverage_policy`

| File | Purpose |
|---|---|
| `tool.py` | Search policy in Qdrant |
| `requirements.txt` | qdrant-client, openai, pydantic |

**User config (local Qdrant — recommended, no CAI Application):**

```json
{
  "qdrant_path": "medishield_policy_qdrant",
  "collection_name": "medishield-policy",
  "openai_api_key": ""
}
```

**Or remote Qdrant (Docker app):**

```json
{
  "qdrant_url": "https://qdrant.<your-cai-domain>",
  "collection_name": "medishield-policy"
}
```

Leave `openai_api_key` empty if `OPENAI_API_KEY` is set as project env var.
Index once in notebook: `index_policy()` with `QDRANT_PATH=medishield_policy_qdrant`.

**Tool input:** `query` e.g. `"pre-existing condition rejection"`

## Tool 3 — `notify_manual_review`

| File | Purpose |
|---|---|
| `tool.py` | Free ntfy/Slack alert when claim needs **human manual review** |
| `requirements.txt` | requests, pydantic |

**User config:**

```json
{
  "ntfy_topic": "leon-hospital-claims",
  "hospital_name": "Leon Hospital"
}
```

Or set project env `NTFY_TOPIC=leon-hospital-claims`. Upload `tool.py`, `notify_lib.py`, and `requirements.txt` to Agent Studio. See [`DEPLOY-NOTIFY-TOOL.md`](../../DEPLOY-NOTIFY-TOOL.md).

**Tool input:** `claim_id`, `reason` (one line, no PII), optional `trace_id`

**Call only when** recommendation is `manual_review` (e.g. CLM-50001).

## Setup order

1. Qdrant app running ✅
2. Index policy: `index_policy()` in notebook
3. Paste `tool.py` + `requirements.txt` into each tool folder in Agent Studio
4. **Remove MCP** from agent (use Python tool instead — see [`DEPLOY-NOTIFY-TOOL.md`](../../DEPLOY-NOTIFY-TOOL.md))
5. Attach tools to workflow (lookup + policy + notify_manual_review)
6. Test: `Review claim CLM-50021` (rejected, no notify) · `Review claim CLM-50001` (manual review + notify)
