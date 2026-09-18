# Register MCP Server in Agent Studio (Tools Catalog)

Your screenshot path: **Agent Studio → Tools Catalog → MCP Servers → Register**

Agent Studio uses **Claude Desktop JSON format** and supports **`uvx`** (Python) or **`npx`** (Node.js).

---

## What you need

| Item | Purpose |
|------|---------|
| `mcp/` folder on CAI project | `notify_server.py`, `notify_lib.py`, `pyproject.toml` |
| ntfy app on phone | Subscribe to topic `leon-hospital-claims` (free) |
| Env vars | `NTFY_TOPIC`, `HOSPITAL_NAME` |

---

## Step 1 — Upload files to CAI project

Upload the whole folder:

```text
/home/cdsw/insuranceclaim/mcp/     ← adjust project name if different
  notify_server.py
  notify_lib.py
  pyproject.toml
  mcp_client.py
  requirements.txt
```

---

## Step 2 — Install `uvx` (required — not pre-installed on many CAI runtimes)

Agent Studio **only** accepts `uvx` (Python) or `npx` (Node.js) — not plain `python`.

If you see `FileNotFoundError: 'uvx'`, install it first.

**Terminal:**

```bash
cd /home/cdsw/<YOUR_PROJECT>/mcp
bash install_uvx.sh
export PATH="$HOME/.local/bin:$PATH"
which uvx
uvx --version
```

**Notebook:**

```python
import os, subprocess, shutil

!bash /home/cdsw/$CDSW_PROJECT/mcp/install_uvx.sh
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", "")
print("uvx:", shutil.which("uvx"))
subprocess.run(["uvx", "--version"], check=False)
```

> **Important:** Agent Studio spawns `uvx` from the **workflow runtime**, not your notebook.
> After install, note the full path (usually `/home/cdsw/.local/bin/uvx`) and use it in registration JSON if plain `uvx` is not on the workflow PATH.

In a **terminal** or notebook:

```bash
cd /home/cdsw/<YOUR_PROJECT>/mcp
which uvx
uvx --version
```

Smoke test (must start without traceback; it will wait on stdio — press Ctrl+C):

```bash
uvx --from /home/cdsw/<YOUR_PROJECT>/mcp leon-hospital-notify
```

**Notebook equivalent:**

```python
import os, subprocess, sys
mcp_dir = f"/home/cdsw/{os.environ['CDSW_PROJECT']}/mcp"
subprocess.run(["uvx", "--from", mcp_dir, "leon-hospital-notify"], timeout=3)
```

(`TimeoutExpired` after ~3s is OK — means the MCP server started.)

Optional: test notification via MCP client (notebook):

```python
%cd /home/cdsw/$CDSW_PROJECT/mcp
!pip install -q mcp requests pydantic
from mcp_client import notify_via_mcp
print(notify_via_mcp("CLM-50001", "clinical review"))
```

---

## Step 3 — Register in Tools Catalog (your screenshot)

1. **Agent Studio** → **Tools Catalog** → **MCP Servers** tab  
2. Click **Register →**  
3. Paste this JSON (change project path if needed):

```json
{
  "mcpServers": {
    "leon_hospital_notify": {
      "command": "uvx",
      "args": [
        "--from",
        "/home/cdsw/insuranceclaim/mcp",
        "leon-hospital-notify"
      ],
      "env": {
        "NTFY_TOPIC": "leon-hospital-claims",
        "HOSPITAL_NAME": "Leon Hospital",
        "PATH": "/home/cdsw/.local/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

If registration still cannot find `uvx`, use the **full path** to the binary:

```json
"command": "/home/cdsw/.local/bin/uvx",
```

4. Click **Register**  
5. Agent Studio will **validate** the server and **discover** tool: `notify_manual_review_ticket`

> **Note:** Env values at registration can be placeholders. Set real `NTFY_TOPIC` again when you attach the MCP server to your workflow agent.

---

## Step 4 — Attach MCP server to your agent

1. Open workflow → **Insurance Claim Reviewer** agent  
2. Scroll to **Add MCP Servers**  
3. Click **+ Add MCP Server to Agent**  
4. Select **`leon_hospital_notify`** from catalog  
5. Set env vars:
   ```text
   NTFY_TOPIC=leon-hospital-claims
   HOSPITAL_NAME=Leon Hospital
   ```
6. **Save** and **redeploy** workflow

Your agent now has:

```text
Tool 1: lookup_claim_features
Tool 2: search_coverage_policy
MCP:    notify_manual_review_ticket   ← manual review only
```

---

## Step 5 — Update agent prompt

Paste from `AGENT-GOAL.md`:

```text
If recommendation is Manual review, call MCP tool notify_manual_review_ticket
with claim_id and a one-line reason (no PII).
Do NOT call it for approved, rejected, or partial claims.
```

---

## Step 6 — Test

| Prompt | Expected |
|--------|----------|
| `Review claim CLM-50001` | Manual review + **phone push** + ticket ID |
| `Review claim CLM-50021` | Rejected — **no** push |

In Agent Studio **Test** tab, confirm `notify_manual_review_ticket` appears in available tools.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Only uvx and npx are supported` | Use `"command": "uvx"` — do **not** use `python` / `python3` in registration JSON |
| `We could not figure out the tools` | Re-upload fixed `pyproject.toml`; run `uvx --from .../mcp leon-hospital-notify` — must start with no traceback |
| Registration fails / No data | Check path `/home/cdsw/<project>/mcp` exists; all files uploaded |
| `uvx` not found / FileNotFoundError | Run `bash mcp/install_uvx.sh`; use `"command": "/home/cdsw/.local/bin/uvx"` in JSON |
| `leon-hospital-notify` not found | Script name must match `[project.scripts]` in `pyproject.toml` exactly |
| `Distribution not found at: file:///home/cdsw/.../mcp` | Wrong path or `pyproject.toml` not uploaded — run `bash mcp/verify_mcp_package.sh` |
| `No module named mcp.server.fastmcp` | Re-upload `pyproject.toml` (`mcp>=1.2.0,<2` pin) and rebuild |
| No phone push | Subscribe to `leon-hospital-claims` in ntfy app; set `NTFY_TOPIC` on workflow |
| Agent ignores MCP | Add Goal rule to call `notify_manual_review_ticket` on manual review only |

### If `uvx --from` still fails

Pre-install into the session, then register with the same `uvx --from` path (uvx will reuse the build):

```bash
cd /home/cdsw/<YOUR_PROJECT>/mcp
uv pip install -e .
uvx --from . leon-hospital-notify   # must start cleanly
```

---

## Architecture

```text
Gemini Agent
  ├── lookup_claim_features     (Python tool — Trino)
  ├── search_coverage_policy    (Python tool — Qdrant)
  └── leon_hospital_notify      (MCP — ntfy push, manual review only)
```
