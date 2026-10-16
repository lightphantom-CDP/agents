# Plan B — spark-file-reader app + HTTP read tool

Agent Studio Python tools hit **bwrap** on disk; this app reads project files and exposes HTTP. The agent tool only calls the app — still a **tool**, not paste.

```text
Agent Studio  →  read_spark_file_via_cai_app  →  HTTP  →  spark-file-reader (CAI App)
                                                              ↓
                                         /home/cdsw/csa-apac/spark-migration-demo/
```

---

## Prerequisites

- [ ] Project **csa-apac** has folder **Files → spark-migration-demo** (you already have this)
- [ ] Spark agent workflow lives in **csa-apac**
- [ ] Remove **catalog file read** from the agent

Copy these into the project (upload or git clone from repo):

```text
spark-migration-demo/cai-applications/spark-file-reader/
  app.py
  start.py
  requirements.txt
spark-migration-demo/agent-tools/read_spark_file_via_cai_app/
  tool.py
  requirements.txt
```

---

## Part 1 — Deploy CAI Application (≈10 min)

1. Open workbench **wb-shashank** → project **csa-apac**.
2. **Applications** → **New Application** (or equivalent).
3. **Name:** `spark-file-reader`
4. **Script / entry:** `spark-migration-demo/cai-applications/spark-file-reader/start.py`  
   (or browse to `start.py` under your uploaded tree)
5. **Engine / runtime:** Python 3 (default project runtime is fine).
6. **Requirements:** point to  
   `spark-migration-demo/cai-applications/spark-file-reader/requirements.txt`  
   or paste: `flask>=3.0.0`
7. **Environment variables** (application or project):

   ```text
   CDSW_PROJECT=csa-apac
   ```

8. **Create** → **Run** (wait until **Running** / green).
9. Open the application → copy the **Application URL** (public base URL, ends with `/spark-file-reader/` or similar).

### Smoke test (browser or curl)

Replace `APP_URL` with your base URL (no trailing slash issues — tool adds paths).

```text
APP_URL/health
```

Expect JSON: `"status": "ok"`, `"spark_demo_exists": true`.

```text
APP_URL/read?path=spark-migration-demo/cde_jobs.yaml
```

Expect JSON with `"content"` containing `spark3-events-etl`.

If `spark_demo_exists: false` → fix **Files** path or `CDSW_PROJECT`.

---

## Part 2 — Register Python tool (≈5 min)

1. **Agent Studio** → **Tools Catalog** → **New tool**
2. **Name:** `read_spark_file_via_cai_app`
3. Upload:
   - `agent-tools/read_spark_file_via_cai_app/tool.py`
   - `requirements.txt` (`requests`, `pydantic`)
4. **User parameters (JSON):**

   ```json
   {
     "base_url": "https://YOUR-WORKBENCH-HOST/.../spark-file-reader"
   }
   ```

   Use the same URL as Part 1 (no `/read` suffix).

5. **Test tool** in catalog:

   **Tool params:**

   ```json
   {"file_path": "spark-migration-demo/cde_jobs.yaml"}
   ```

   Expect `content` in output, not bwrap error.

6. If your app requires auth, set on **workflow/project** env:

   ```text
   CDSW_API_KEY=<your API key>
   ```

---

## Part 3 — Wire Agent Studio workflow

1. Open Spark migration **workflow** → your agent.
2. **Attach tools:**
   - `read_spark_file_via_cai_app` (**required** for Plan B)
   - Optional: `read_spark_project_file` (can leave off if only Plan B)
   - Optional later: `push_spark_job_to_github`
3. **Remove** catalog **file read** from agent.
4. Paste **Goal** from [`AGENT-GOAL.md`](AGENT-GOAL.md) (tools mandatory section).
5. **Workflow / project environment:**

   ```text
   SPARK_FILE_READER_URL=https://YOUR-WORKBENCH-HOST/.../spark-file-reader
   CDSW_PROJECT=csa-apac
   ```

   (`SPARK_FILE_READER_URL` overrides user config if set.)

6. **Save** → **Deploy** workflow → status **Running**.

---

## Part 4 — Test agent

**Agent Studio → Test:**

```text
Review spark3-events-etl for Spark 4 migration. Use read tools only.
```

Expected:

1. Tool call `read_spark_file_via_cai_app` with `cde_jobs.yaml`
2. More tool calls for `events_etl_spark3.py` and `job.meta.yaml`
3. Safety + Spark 3 + question **SPARK3 ONLY** vs **CONVERT TO SPARK 4**

---

## Operations

| Item | Note |
|------|------|
| App must stay **Running** during demos | Stopped app → tool HTTP errors |
| Code updates in **Files** | App reads live files; no app redeploy needed for `.py` edits |
| App redeploy | Only when changing `app.py` / Flask routes |
| Cost | One small always-on app; stop when not demoing |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tool still shows bwrap | Agent still using catalog file read — remove it |
| HTTP connection error | App not running; wrong `SPARK_FILE_READER_URL` |
| 404 file_not_found | Path typo; use `spark-migration-demo/cde_jobs.yaml` |
| 401 on /read | Set `CDSW_API_KEY` on workflow to match CAI auth |
| health ok but spark_demo_exists false | Wrong project slug; set `CDSW_PROJECT=csa-apac` on app |

---

## Summary

| Component | Count |
|-----------|--------|
| **New CAI Application** | **Yes** — `spark-file-reader` |
| **New Agent Studio tool** | **Yes** — `read_spark_file_via_cai_app` |
| **Second app for Spark agent** | No — only this reader app (+ your existing Agent Studio workflow app) |

Plan B = **one extra app** + **one custom tool**; CDE unchanged.
