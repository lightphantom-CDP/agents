# Upload example Spark jobs to CDE (before GitHub)

Two PySpark jobs in this folder:

| Job | Path | CDE virtual cluster |
|-----|------|---------------------|
| **Spark 3** | `jobs/spark3_events_etl/events_etl_spark3.py` | Spark **3** VC |
| **Spark 4** | `jobs/spark4_events_etl/events_etl_spark4.py` | Spark **4** VC (e.g. 4.1.1 definition) |

Both use **synthetic data** (no input file required). Optional args only set output path.

## 1. Upload as CDE Resource

1. CDE → **Resources** → upload `events_etl_spark3.py` and `events_etl_spark4.py` (keep version in the resource name on CDE if you like).
2. Single `.py` per resource is enough.

## 2. Create job definition — Spark 3

1. Pick runtime / definition compatible with **Spark 3** VC.
2. **Name:** `spark3-events-etl`
3. **Application file:** Resource → select `events_etl_spark3.py`.
4. **Main class:** leave empty for Python if the UI allows; otherwise use your CDE docs for PySpark (often the application file is the entrypoint).
5. **Arguments** (example):

   ```text
   --output s3a://YOUR-BUCKET/demo/spark3_out
   ```

   For a quick test without S3, ask your admin if local paths are allowed, or use your environment’s default staging bucket.

6. Assign to **Spark 3 virtual cluster** → Save → Run.

Expected driver log line:

```text
spark3_events_etl OK enriched_rows=... daily_rows=... output=...
```

## 3. Create job definition — Spark 4

Same steps on **Spark 4.1.x** (or your Spark 4) definition screen:

1. **Name:** `spark4-events-etl`
2. **Application file:** `events_etl_spark4.py` resource.
3. **Arguments:**

   ```text
   --output s3a://YOUR-BUCKET/demo/spark4_out
   ```

4. Assign to **Spark 4 virtual cluster** → Run.

Expected:

```text
spark4_events_etl OK enriched_rows=... daily_rows=... output=...
```

With the same `--seed 42`, enriched/daily **row counts should match** between Spark 3 and Spark 4 runs (good parity story for the agent).

## 4. Agent Studio (no tools)

Paste into chat:

- `events_etl_spark3.py` + `job.meta.yaml` for review → agent should detect **Spark 3**, ask **SPARK3 ONLY** vs **CONVERT TO SPARK 4**.
- `events_etl_spark4.py` as the native Spark 4 reference.

## 5. Later: GitHub + CDE Repository

When ready, push this `spark-migration-demo/` tree to GitHub and register the repo under CDE **Repositories**; point job definitions at repo paths instead of Resources.
