# MCP filesystem — read Spark jobs in Agent Studio

Use a **stdio MCP server** so the Spark agent calls **`read_job_file`** / **`list_spark_job_files`** instead of catalog file read (bwrap).

```text
Agent Studio  →  MCP client  →  spark_jobs_mcp (stdio)  →  csa-apac/spark-migration-demo/
```

---

## Part 0 — Copy into project csa-apac

Ensure this tree exists on the workbench:

```text
spark-migration-demo/mcp/spark_jobs_mcp/
  server.py
  requirements.txt
  run_mcp.sh
spark-migration-demo/cde_jobs.yaml
spark-migration-demo/jobs/...
```

```bash
chmod +x spark-migration-demo/mcp/spark_jobs_mcp/run_mcp.sh
```

---

## Part 1 — Install MCP Python package (once per project)

In a **Session** for project **csa-apac**:

```bash
cd /home/cdsw/csa-apac
python3 -m venv .venv
source .venv/bin/activate
pip install -r spark-migration-demo/mcp/spark_jobs_mcp/requirements.txt
```

Quick test (server speaks MCP on stdio — will look idle; Ctrl+C to stop):

```bash
export CDSW_PROJECT=csa-apac
export SPARK_JOBS_ROOT=/home/cdsw/csa-apac/spark-migration-demo
python spark-migration-demo/mcp/spark_jobs_mcp/server.py
```

Optional: use **Inspector** / MCP CLI from your laptop only if you mount the same paths — not required for CAI.

---

## Part 2 — Register MCP server in Agent Studio

UI labels vary by CAI version; map to your screen.

1. **Agent Studio** → **MCP servers** (or workflow **Integrations** → **MCP**).
2. **Add server**
   - **Name:** `spark-jobs-mcp`
   - **Transport:** **stdio** (subprocess)
   - **Command:**

     ```text
     /home/cdsw/csa-apac/spark-migration-demo/mcp/spark_jobs_mcp/run_mcp.sh
     ```

     Or explicit:

     ```text
     /home/cdsw/csa-apac/.venv/bin/python
     ```

     **Args:**

     ```text
     /home/cdsw/csa-apac/spark-migration-demo/mcp/spark_jobs_mcp/server.py
     ```

   - **Environment variables:**

     ```text
     CDSW_PROJECT=csa-apac
     SPARK_JOBS_ROOT=/home/cdsw/csa-apac/spark-migration-demo
     ```

3. **Save** → **Test connection** (if available). You should see tools:
   - `read_job_file`
   - `list_spark_job_files`
   - `spark_jobs_root_info`

### If Agent Studio only supports `npx` MCP (alternative)

```text
npx -y @modelcontextprotocol/server-filesystem /home/cdsw/csa-apac/spark-migration-demo
```

Requires **Node/npx** on the workbench. Prefer **Python `spark_jobs_mcp`** if Node is missing.

---

## Part 3 — Attach MCP tools to Spark agent

1. Open Spark migration **workflow** → agent.
2. **Remove** catalog **file read** (bwrap).
3. **Remove** Plan B HTTP tool from agent if you are standardizing on MCP only (optional: keep as fallback).
4. **Enable MCP server** `spark-jobs-mcp` for this workflow/agent.
5. Allow tools: **`read_job_file`**, **`list_spark_job_files`**, **`spark_jobs_root_info`**.

---

## Part 4 — Agent Goal (MCP mandatory)

Paste into **Goal** (replace file-read / Plan B sections):

```text
MCP spark-jobs-mcp — MANDATORY for job source:
• First call spark_jobs_root_info if paths might be wrong.
• Read cde_jobs.yaml via read_job_file("cde_jobs.yaml").
• Read each job's source and meta paths from that registry with read_job_file.
• list_spark_job_files("") if you need to discover paths.
• Never invent file contents. Never use catalog file read.
• If MCP fails, report error; ask admin to fix MCP server command/env — do not ask user to paste full sources.

Then run safety, Spark version, SPARK3 ONLY vs CONVERT TO SPARK 4 (same as before).
```

Full goal template: [`AGENT-GOAL-MCP.md`](AGENT-GOAL-MCP.md)

---

## Part 5 — Deploy and test

1. **Save** agent → **Deploy** workflow → **Running**.
2. **Test** tab:

   ```text
   Review spark3-events-etl for Spark 4 migration. Use MCP read_job_file only.
   ```

Expected trace: MCP **`read_job_file`** for `cde_jobs.yaml`, then `events_etl_spark3.py`, then `job.meta.yaml` → safety → user choice question.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP server fails to start | Run `run_mcp.sh` in Session; fix `pip install mcp` / python path |
| `exists=false` in root_info | Wrong `SPARK_JOBS_ROOT`; confirm Files UI path |
| Agent does not call MCP | MCP not enabled on workflow; tools not selected |
| bwrap on MCP | Rare; MCP is separate process — if still broken, use Plan B app |
| `uvx` / npx errors | Use Python `server.py` path, not npx |

---

## Plan B fallback

If MCP registration is blocked on your CAI build, keep **spark-file-reader** CAI app + **`read_spark_file_via_cai_app`** ([`DEPLOY-PLAN-B-SPARK-FILE-READER.md`](DEPLOY-PLAN-B-SPARK-FILE-READER.md)).

MCP and Plan B both satisfy “agent must use tools.”
