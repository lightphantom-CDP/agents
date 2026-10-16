# Agent must use tools — fix bwrap + working read path

The catalog **file read** tool often fails on AWC with:

```text
bwrap: Failed to make / slave: Permission denied
```

That is **tool sandbox** on the node, not missing files in **Files → spark-migration-demo**.

---

## Strategy (in order)

### 1. Stop using catalog file read for Spark

Remove the heavy catalog **file read** from the agent. Use **custom** tools only.

### 2. Try minimal direct read tool

Upload **`read_spark_project_file`** (only `pathlib`, no OCR/PDF).

Tools Catalog → **Test** with:

```json
{"file_path": "spark-migration-demo/cde_jobs.yaml"}
```

User config:

```json
{"project_slug": "csa-apac"}
```

- **Works** → attach only this tool to the agent.
- **Same bwrap error** → go to step 3 (CAI app + HTTP tool).

### 3. Deploy CAI Application `spark-file-reader` (recommended when bwrap blocks disk read in tools)

1. In project **csa-apac**, create **Application** from:
   `cai-applications/spark-file-reader/` (`start.py`, `app.py`, `requirements.txt`)
2. **Run** application → copy public **Application URL**
3. Workflow env:

   ```text
   SPARK_FILE_READER_URL=https://.../spark-file-reader/
   CDSW_PROJECT=csa-apac
   ```

4. Upload tool **`read_spark_file_via_cai_app`** to Tools Catalog
5. User config:

   ```json
   {"base_url": "https://.../spark-file-reader/"}
   ```

6. Test tool with `file_path`: `spark-migration-demo/cde_jobs.yaml`
7. Attach **`read_spark_file_via_cai_app`** to Spark agent (not catalog file read)

The app reads `/home/cdsw/csa-apac/spark-migration-demo/...`; the tool only does HTTP.

### 4. Platform fix (so direct read tools work too)

Ask admin for workbench **wb-shashank** / Agent Studio tool executor:

- `bwrap` / user namespaces on Kubernetes workers
- Often: enable unprivileged user namespaces, or adjust tool pod `securityContext`
- Cloudera support: Agent Studio Python tool sandbox failure

---

## Agent tools (attach)

| Tool | When |
|------|------|
| `read_spark_project_file` | Try first if Test passes |
| `read_spark_file_via_cai_app` | When bwrap blocks direct read |
| `push_spark_job_to_github` | Optional, after convert |

**Do not attach** catalog file read if it throws bwrap.

---

## Agent Goal rule (tools mandatory)

```text
You MUST load job files using read_spark_project_file or read_spark_file_via_cai_app only.
Never ask the user to paste full job source unless every read tool returns a platform/sandbox error — then report bwrap/admin fix and retry after fix.
Always read spark-migration-demo/cde_jobs.yaml first, then source_file and meta_file from that registry.
```

Full Goal: [`AGENT-GOAL.md`](AGENT-GOAL.md) — update tools section to match what you attached.

---

## Verify CAI app before agent test

Browser or curl:

```text
GET <APP_URL>/health
GET <APP_URL>/read?path=spark-migration-demo/cde_jobs.yaml
```

Should return JSON with `content`.
