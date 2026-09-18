# Connect Agent Studio → Live Trino

Hue/Trino works in the DWH UI. Agent Studio tools run in a **different pod** and must use the **Trino HTTP API** (`trino-python-client`), not Spark.

```text
Hue (browser)     →  Trino  ✅  you already have this
Agent Studio tool →  Trino  ⏳  configure trino_host below
```

---

## Step 1 — Find your Trino coordinator host

**Hue URL is NOT the Trino host.**

| URL | Role |
|---|---|
| `hue-dwhrtrino.dw-lhcai....cloudera.site` | Hue UI (SQL editor) |
| `trino-coordinator...` or similar | **Trino API host** (what the tool needs) |

Ask your Cloudera admin for:

- Trino coordinator hostname
- Port (usually **443** HTTPS or **8080** internal)
- Auth: password, JWT, or workload identity

Common patterns:

```text
trino.dw-lhcai.a465-9q4k.cloudera.site
coordinator.trino.svc.cluster.local   (internal K8s — Agent Studio may reach this)
```

---

## Step 2 — Test from CAI Sessions (before Agent Studio)

CDW Trino does **not** accept `/tmp/jwt` from CAI (that token is for CAI services only).

Use **workload password** (recommended) or a **Knox JWT** from CDW Token Generator.

### Option A — Workload password (recommended for CAI)

1. **CAI** → User Settings → Environment → set `WORKLOAD_PASSWORD`
2. **CDP Console** → your profile → **Set Workload Password** (same value)
3. Restart your session

```python
!pip install trino -q

import os
from trino.dbapi import connect
from trino.auth import BasicAuthentication

HOST = "dwhrtrino.dw-lhcai.a465-9q4k.cloudera.site"
USER = os.getenv("HADOOP_USER_NAME", "leonard")   # auto-set in CAI
PASSWORD = os.getenv("WORKLOAD_PASSWORD")

if not PASSWORD:
    raise ValueError("Set WORKLOAD_PASSWORD in CAI User Settings > Environment")

os.environ["NO_PROXY"] = f"{os.environ.get('NO_PROXY','')},{HOST}".strip(",")

conn = connect(
    host=HOST,
    port=443,
    user=USER,
    auth=BasicAuthentication(USER, PASSWORD),
    catalog="hive",
    schema="insurance_leo_trino",
    http_scheme="https",
)
```

### Option B — Knox JWT (from CDW Token Generator)

CDW → Virtual Warehouses → Trino VW → **JWT Auth Token Generator** (or Data Lake → Token Integration).

```python
from trino.auth import JWTAuthentication

conn = connect(
    host=HOST,
    port=443,
    user="leonard",
    auth=JWTAuthentication("PASTE_KNOX_JWT_HERE"),
    catalog="hive",
    schema="insurance_leo_trino",
    http_scheme="https",
)
```
cur = conn.cursor()
cur.execute("""
    SELECT claim_id, claim_outcome, undisclosed_pre_existing_flag
    FROM hive.insurance_leo_trino.claim_features_v1
    WHERE claim_id = 'CLM-50021'
    LIMIT 1
""")
print(cur.fetchone())
```

If this works in Sessions, use the **same HOST** in Agent Studio tool config.

If Sessions works but Agent Studio fails → network policy blocks Agent Studio pod; ask admin to allow outbound HTTPS to Trino coordinator.

---

## Step 3 — Configure `lookup_claim_features` tool

Upload updated `tool.py` + `requirements.txt` (includes `trino`).

**User parameters in Agent Studio:**

```json
{
  "gold_table": "hive.insurance_leo_trino.claim_features_v1",
  "trino_host": "YOUR_TRINO_COORDINATOR_HOST",
  "trino_port": 443,
  "trino_user": "leonard",
  "trino_password": "",
  "trino_catalog": "hive",
  "trino_schema": "insurance_leo_trino",
  "trino_http_scheme": "https",
  "use_demo_fallback": false
}
```

| Field | Notes |
|---|---|
| `use_demo_fallback` | **`false`** = Trino only (production story) |
| `trino_host` | Coordinator hostname only, no `https://` |
| `trino_user` | Your CDP login (`leonard`). Empty = `HADOOP_USER_NAME` |
| `trino_jwt` | Knox JWT from CDW Token Generator (optional) |
| `trino_password` | Optional; tool prefers `WORKLOAD_PASSWORD` env |

Alternative: set project env vars instead:

```bash
TRINO_HOST=your-coordinator.cloudera.site
TRINO_USER=cdsw
TRINO_PASSWORD=...
TRINO_HTTP_SCHEME=https
```

---

## Step 4 — Test the tool

**Test tool** with:

```json
{ "claim_id": "CLM-50021" }
```

**Success:**

```json
{
  "claim_id": "CLM-50021",
  "undisclosed_pre_existing_flag": 1,
  "data_source": "trino",
  "suggested_outcome": "rejected"
}
```

**Failure** (now shows real error):

```json
{
  "error": "Claim not found: CLM-50021",
  "errors": ["Trino error (bad-host:443): ..."],
  "trino_target": { "host": "...", "port": 443 }
}
```

Paste the `errors` list to your admin if connection fails.

---

## Load order (updated tool)

```text
1. Trino HTTP          ← primary (governed gold table)
2. Spark               ← if Agent Studio workload has Spark ON
3. Parquet             ← optional export
4. demo_claims.json    ← only if use_demo_fallback=true
```

---

## Demo claims to test (all in Trino)

| claim_id | claim_outcome (Trino) |
|---|---|
| CLM-50021 | rejected |
| CLM-50005 | approved |
| CLM-50003 | partial_approval |
| CLM-50001 | manual_review |

```sql
SELECT claim_id, claim_outcome
FROM hive.insurance_leo_trino.claim_features_v1
WHERE claim_id IN ('CLM-50021','CLM-50005','CLM-50003','CLM-50001');
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Trino not configured` | Set `trino_host` |
| `Connection refused` | Wrong host — not Hue URL |
| `401 Unauthorized` | `/tmp/jwt` won't work — set `WORKLOAD_PASSWORD` or use Knox JWT |
| `SSL` errors | Try `trino_http_scheme: "https"` or port 8080 internal |
| Works in Sessions, not Agent Studio | Ask admin: allow Agent Studio → Trino network |
| Still uses demo file | Set `use_demo_fallback: false`, remove `demo_claims.json` from tool folder |
