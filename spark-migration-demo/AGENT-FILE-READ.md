# Spark agent — file read tool + paths

The agent cannot see project files until you attach the catalog **file read** tool (or the user pastes content).

## 1. Copy files into the CAI project

Clone or copy the whole `spark-migration-demo/` folder into the **same CAI project** that hosts your Agent Studio workflow, for example:

```text
/home/cdsw/<YOUR_PROJECT>/spark-migration-demo/
  cde_jobs.yaml
  jobs/spark3_events_etl/events_etl_spark3.py
  jobs/spark3_events_etl/job.meta.yaml
  jobs/spark4_events_etl/events_etl_spark4.py
  ...
```

## 2. Attach tools in Agent Studio

| Tool | Purpose |
|------|---------|
| **File read** (catalog) | OK if you pass **absolute** paths under `/home/cdsw/csa-apac/...` |
| **`read_spark_project_file`** (optional, repo) | Easier paths like `spark-migration-demo/cde_jobs.yaml` |
| `push_spark_job_to_github` (optional) | After convert + user approval |

Redeploy the workflow after attaching tools.

## 3. Paths for `file_path` (important)

The catalog tool description says paths are **relative to the tool directory** (`/tool/`). Project files are usually **not** there, so the agent often needs **absolute paths** under the project:

```text
/home/cdsw/<YOUR_PROJECT>/spark-migration-demo/cde_jobs.yaml
/home/cdsw/<YOUR_PROJECT>/spark-migration-demo/jobs/spark3_events_etl/events_etl_spark3.py
/home/cdsw/<YOUR_PROJECT>/spark-migration-demo/jobs/spark3_events_etl/job.meta.yaml
```

Replace `<YOUR_PROJECT>` with your project slug (same as in the CAI URL).

**Test in a CAI Session** from the project root:

```bash
ls spark-migration-demo/cde_jobs.yaml
pwd
```

Use `pwd` + `/spark-migration-demo/...` in agent tests.

If relative paths fail with "File not found", switch to absolute paths only.

## 4. Paste into Spark agent Goal

```text
File read tool:
• You cannot review Spark job code without reading files via the file read tool (or user paste).
• When the user asks to review a CDE job or "our jobs", first read:
  /home/cdsw/<YOUR_PROJECT>/spark-migration-demo/cde_jobs.yaml
• For job spark3-events-etl also read source_file and meta_file paths from that YAML.
• For .py and .yaml the tool returns plain text — use that as the only source of code.
• If file read returns "File not found", ask the user for the correct project path or pasted content.
• Do not invent file contents.

After conversion, if push_spark_job_to_github is attached and user approves push, use file_content from the read result or your converted full file.
```

Replace `<YOUR_PROJECT>` once in Goal.

## 5. Test chat

```text
Read cde_jobs.yaml and review spark3-events-etl for Spark 4 migration.
```

Expected: agent calls file read twice or more, then safety / Spark 3 / convert question.

## 6. PySpark files

`.py` and `.yaml` use the text branch of the file read tool — no PDF/OCR needed. Extra dependencies in the tool script are for other formats only.

## 7. If file read fails (`bwrap` / Permission denied)

Agent Studio tool pods sometimes fail with:

```text
bwrap: Failed to make / slave: Permission denied
```

That is **not** fixable by changing `file_path`. Use one of these:

| Workaround | Action |
|------------|--------|
| **Demo now** | Paste `cde_jobs.yaml` + job `.py` + `job.meta.yaml` in chat |
| **Goal fallback** | Agent must not loop on file read; switch to paste after one tool failure |
| **Admin / platform** | Workbench admin: tool sandbox / `bwrap` on Agent Studio (CAI on AWC) |
| **Custom tool** | `read_spark_project_file` may hit the **same** sandbox — test once; if same error, use paste |

Update agent **Goal** (add at top of File read section):

```text
If file read or read_spark_project_file returns bwrap, permission denied, or slave errors:
stop calling read tools; ask the user to paste cde_jobs.yaml and the job source in one message, then continue Phase 2+.
```

**User message template:**

```text
Review spark3-events-etl. Registry and source below.

--- cde_jobs.yaml ---
(paste)

--- job.meta.yaml ---
(paste)

--- events_etl_spark3.py ---
(paste)
```

