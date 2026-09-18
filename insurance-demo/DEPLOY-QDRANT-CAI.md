# Deploy Qdrant on CAI Application (no RAG Studio)

Your expert's approach: run **Qdrant as its own CAI Application**, then your **Agent Studio + Gemini** calls it from Python.

```text
coverage_policy.md
        ↓
CAI notebook / agent  →  OpenAI embeddings  →  vectors
        ↓
Qdrant CAI Application  →  store + search vectors
        ↓
Gemini (Agent Studio)  →  final claim review answer
```

---

## Architecture

```text
┌─────────────────────┐     ┌──────────────────────┐
│  Qdrant Application │     │  Agent Studio        │
│  (vector database)  │◄────│  Gemini + SQL tool   │
│  port 6333          │     │  + policy RAG code   │
└─────────────────────┘     └──────────────────────┘
         ▲                            │
         │                            ▼
    store/search              claim_features_v1 (Trino)
    policy vectors
```

| Component | Role |
|---|---|
| **Qdrant app** | Vector database only (storage + search) |
| **OpenAI embedding API** | Text → vectors (index + query time) |
| **Gemini (Agent Studio)** | Claim review reasoning |
| **RAG Studio** | **Not used** |

---

## Step 1 — Deploy Qdrant as CAI Application

### Option A — Docker application (recommended)

Avoids PBJ Workbench port 8100 conflicts from the Python script approach.

1. **Stop** or delete the old Python `qdrant` application
2. **Applications** → **New Application** → **Docker**
3. Fill in:

| Field | Value |
|---|---|
| **Name** | `qdrant` |
| **Subdomain** | `qdrant` |
| **Docker Image** | `qdrant/qdrant:v1.11.3` |
| **Container Port** | `6333` |
| **vCPU / Memory** | 1 vCPU / 2–4 GiB |

4. **Create** → **Start** → wait for **Running**
5. Copy **Application URL**: `https://qdrant.<your-cai-domain>`

Test from a CAI session:

```bash
curl -s https://qdrant.<your-cai-domain>/collections
```

Expected: `{"result":{"collections":[]},...}` (empty until you index).

Set in notebook:

```python
os.environ["QDRANT_URL"] = "https://qdrant.<your-cai-domain>"
```

### Option B — Local embedded Qdrant (no Application)

If Docker is not available, use file-based Qdrant under `/workflow_data`:

```python
os.environ["QDRANT_PATH"] = "medishield_policy_qdrant"
from agent.qdrant_policy_rag import index_policy
index_policy()
```

Agent Studio tool config: `qdrant_path` (not `qdrant_url`). See `agent/tools/README.md`.

### Option C — Script application (Python 3.10)

Use the latest `cai-applications/qdrant/run_qdrant.py` (daemon on **6333**, exits 0 → **Running** status).

| Field | Value |
|---|---|
| **Name** | `qdrant` |
| **Subdomain** | `qdrant` |
| **Script** | `agent-studio/run_qdrant.py` |
| **Kernel** | **Python 3.10** (NOT Agent Studio / RAG Studio) |
| **Spark** | OFF |
| **Editor** | PBJ Workbench is OK — Qdrant uses **6333**, not 8100 |

**Your cluster URL:**

```text
https://qdrant.lhworkbench.lhcai.a465-9q4k.cloudera.site:6333
```

Pattern: `https://qdrant.<project>.<CDSW_DOMAIN>:6333`

After **Start**, Application Logs should show:

```text
Qdrant is ready on port 6333
Startup complete — application should show Running.
```

Then index from a **notebook session** (not this script).

### Option D — Ask admin / Kubernetes

If Docker apps are not allowed, admin deploys Qdrant on the cluster and gives you URL:

```text
http://qdrant.<your-cluster-internal>:6333
```

---

## Step 2 — Test Qdrant is up

From a **CAI session** or terminal:

```bash
curl http://qdrant-<subdomain>.<your-cai-domain>/healthz
# or internal URL your admin provides
```

Or open Qdrant dashboard: `http://<qdrant-url>:6333/dashboard`

Expected: healthy response / dashboard loads.

---

## Step 3 — Index policy into Qdrant (one-time)

In CAI Workbench notebook or session:

```bash
pip install qdrant-client openai
```

```python
import os
os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["QDRANT_URL"] = "http://qdrant-<subdomain>.<your-cai-domain>"  # your Qdrant app URL

from agent.qdrant_policy_rag import index_policy

index_policy(
    policy_path="data/policy/coverage_policy.md",
    collection_name="medishield-policy",
)
```

This chunks `coverage_policy.md`, embeds with OpenAI, stores in Qdrant.

---

## Step 4 — Test policy search

```python
from agent.qdrant_policy_rag import search_policy

chunks = search_policy(
    "What are rejection rules for undisclosed pre-existing conditions?",
    collection_name="medishield-policy",
    top_k=3,
)
for c in chunks:
    print(c["score"], c["text"][:200])
```

---

## Step 5 — Wire into Agent Studio

### Python tool for Agent Studio

**Tool name:** `search_coverage_policy`

Use `agent/qdrant_policy_rag.py` → function `search_policy(query, top_k=3)`.

Returns relevant policy sections for Gemini to cite.

### Agent workflow

```text
User: "Review claim CLM-50021"
  1. lookup_claim_features (SQL)     → claim data
  2. search_coverage_policy (Qdrant) → policy sections
  3. Gemini                          → recommend outcome + citations
```

### System prompt addition

```text
Before deciding, call search_coverage_policy with the main issue
(e.g. "pre-existing condition rejection", "prior authorization standard plan").
Cite section numbers from retrieved policy chunks.
```

---

## Environment variables

| Variable | Example | Purpose |
|---|---|---|
| `QDRANT_URL` | `http://qdrant-....` | Qdrant CAI app URL |
| `QDRANT_API_KEY` | optional | If Qdrant auth enabled |
| `OPENAI_API_KEY` | `sk-...` | Embeddings (`text-embedding-3-small`) |
| `GEMINI_API_KEY` | already set | Agent Studio chat |

---

## vs RAG Studio

| | RAG Studio | Qdrant CAI App (your path) |
|---|---|---|
| Vector DB | Embedded Qdrant inside RAG | **Your own Qdrant app** |
| Embeddings | RAG Studio model provider | **OpenAI API** (you control) |
| Chat | RAG Studio UI | **Agent Studio Gemini** |
| Flexibility | Low-code, bundled | **Custom code, full control** |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Stuck on **Starting** | Qdrant must bind to `CDSW_APP_PORT` (see `run_qdrant.py`). Check logs — if HTTP port is 8080/6333 instead of `CDSW_APP_PORT`, update script and Restart |
| App **Failed** / exit code 1 | Open **Application Logs** — look for `FATAL:` or `Cannot execute`. Re-upload latest `run_qdrant.py`, **Stop** app, delete `~/qdrant` in a one-off session if corrupt, **Restart** |
| `Cannot execute` binary | Wrong CPU/arch — try **Docker** app with image `qdrant/qdrant:v1.11.3` port `6333` mapped to app port, or ask admin |
| `SystemExit: 1` in notebook | You ran `run_qdrant.py` in a session — only run it as an **Application** |
| `Jupyter kernel stopped` | Script used `os.execve` or crashed — use latest `run_qdrant.py` (subprocess, not execve) |
| `Address in use (os error 98)` | Port 8100 held by Jupyter/PBJ or stale Qdrant — use latest `run_qdrant.py` (Qdrant on 6333 + TCP proxy). Or use **Docker** app |
| Cannot reach Qdrant URL | Check application is Running; use Application URL from Overview (not localhost) |
| Collection not found | Run `index_policy()` first |
| OpenAI embedding error | Set `OPENAI_API_KEY` |
| Agent can't call Qdrant | Expose `search_policy` as Python tool in Tools Catalog |

---

## Next steps

1. Deploy Qdrant application ✅
2. Run `index_policy()` ✅
3. Test `search_policy()` ✅
4. Add Python tool to Agent Studio
5. Test: `Review claim CLM-50021`
