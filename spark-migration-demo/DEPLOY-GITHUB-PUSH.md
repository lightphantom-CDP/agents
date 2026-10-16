# Agent Studio → GitHub push (for CDE Repository handoff)

After the Spark agent converts code, this tool commits the file to GitHub. CDE jobs that use a **CDE Repository** then run the updated path on the next job run.

```text
Agent converts  →  push_spark_job_to_github  →  GitHub main
                                                      ↓
                                              CDE Repository job run (Spark 4 VC)
```

---

## Step 1 — GitHub repo and token

1. Create a **public** repo (or use an existing one) with the same layout as `spark-migration-demo/`:
   - `jobs/spark3_events_etl/events_etl_spark3.py`
   - `jobs/spark4_events_etl/events_etl_spark4.py`
2. GitHub → **Settings → Developer settings → Personal access tokens**
   - Classic: scope **`repo`** (for private) or **`public_repo`** (public only)
   - Fine-grained: **Contents: Read and write** on that repository
3. Copy the token — you will set it only in CAI env, never in the repo.

---

## Step 2 — Register tool in Agent Studio

1. **Tools Catalog** → create Python tool **`push_spark_job_to_github`**
2. Upload from this repo:

   ```text
   spark-migration-demo/agent-tools/push_spark_job_to_github/
     tool.py
     requirements.txt
   ```

3. **User config (JSON)** example:

   ```json
   {
     "github_repo": "YOUR_GITHUB_USER/spark-migration-demo",
     "default_branch": "main"
   }
   ```

---

## Step 3 — Workflow / project environment variables

Set on the **workflow** or **project** (not in GitHub):

| Variable | Example | Required |
|----------|---------|----------|
| `GITHUB_TOKEN` | `ghp_...` | Yes |
| `GITHUB_REPO` | `your-user/spark-migration-demo` | Yes (or user config) |
| `GITHUB_DEFAULT_BRANCH` | `main` | Optional |
| `GITHUB_PUSH_ENABLED` | `true` | Yes — tool refuses push if not `true` |

Keep `GITHUB_PUSH_ENABLED=false` until you are ready to demo live pushes.

---

## Step 4 — Attach tool + update Spark agent Goal

Attach **`push_spark_job_to_github`** to your Spark migration agent.

Add to **Goal**:

```text
GitHub push (tool push_spark_job_to_github):
• Only call after the user explicitly says "push to GitHub" or "approve GitHub push".
• Pass user_confirmed=true only when they said so in this conversation.
• repo_path must match our repo layout, e.g. jobs/spark4_events_etl/events_etl_spark4.py
• file_content = full converted Spark 4 source (complete file, not a diff only).
• After success, tell the user to run the CDE job on Spark 4 VC linked to that repo path.
• If the tool returns error or pushed=false, report the error; do not claim success.
```

Optional: attach **file read** so the agent loads the canonical path before push.

---

## Step 5 — Redeploy workflow

1. Save agent → **Deploy** workflow → wait **Running**
2. Test in **Test** tab:

   ```text
   I approve GitHub push. Push converted events_etl_spark4.py to
   jobs/spark4_events_etl/events_etl_spark4.py with message "demo: spark4 conversion".
   (paste file content)
   ```

3. Verify on GitHub: file updated, new commit on `main`.

---

## Step 6 — CDE uses GitHub

1. CDE → **Repositories** → link the same GitHub repo + branch + credential (if private).
2. Spark 4 job definition → **Application file** from **Repository** →  
   `jobs/spark4_events_etl/events_etl_spark4.py`
3. **Run** on Spark 4 virtual cluster.

---

## Safety defaults

| Guard | Purpose |
|-------|---------|
| `GITHUB_PUSH_ENABLED=true` | Prevents accidental push in dev |
| `user_confirmed=true` | Agent must not push without user words |
| Goal: push only after convert + approve | Human in the loop |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| 401 / Bad credentials | Regenerate token; check `GITHUB_TOKEN` on workflow |
| 404 repo | Fix `GITHUB_REPO` owner/name |
| 422 path | File exists but SHA logic failed — retry; check branch name |
| Tool not called | Redeploy workflow; check tool attached to correct agent |

---

## Manual alternative (no tool)

In CAI project terminal:

```bash
git add jobs/spark4_events_etl/events_etl_spark4.py
git commit -m "spark4 conversion"
git push origin main
```

Same outcome for CDE Repository; agent does not perform the push.
