# Lab 6 Workarounds — Credit Scoring Workshop

Use this guide when the **official** Lab 6 path fails in Cloudera Cloud workshops.

## Official path (when it works)

1. Deploy model from code (`credit_scoring_api.py` + `cdsw-build.sh`)
2. CDE job `04_batch_score.py` calls HTTP model API with `--access-key`
3. Writes Iceberg `scores` table

## Known workshop issues

| Issue | Symptom | Workaround |
|-------|---------|------------|
| Model gateway timeout | `context deadline exceeded` after ~30s | CAI scoring + `04_load_scores.py` |
| CAI Spark + Iceberg | `unread block data` on `toPandas()` / `collect()` | Score from S3 parquet in CAI |
| CDE no `hadoop` CLI | `FileNotFoundError: hadoop` in batch job | Use `04_batch_score_local.py` (Spark S3 download) |
| CDE pip blocked | ML packages not importable after pip | Use CAI `score_in_cai.py` + `04_load_scores.py` |

## Recommended workaround (3 steps)

### Step A — Features parquet (skip if already exported)

CDE job `04_export_features.py`:

```
--db=workshop_credit_user_001
--output=s3a://<bucket>/workshop/credit_scoring/tmp/workshop_credit_user_001_features_parquet
```

Or reuse an existing export under `.../tmp/..._features_parquet/`.

### Step B — Score in CAI (no Spark)

```bash
# In CAI session
hadoop fs -get -f s3a://<bucket>/.../features_parquet /home/cdsw/features_parquet
python score_in_cai.py
hadoop fs -put -f /home/cdsw/scores_out.parquet s3a://<bucket>/.../scores_out.parquet
```

Requires `/home/cdsw/model_files` from `export_model.py`.

### Step C — Load scores in CDE

CDE job `04_load_scores.py`:

```
--db=workshop_credit_user_001
--input=s3a://<bucket>/.../scores_out.parquet
```

Verify:

```python
spark.table("workshop_credit_user_001.scores").count()
```

## Deploy-from-code files (Lab 5)

| File | Purpose |
|------|---------|
| `labs/cai/export_model.py` | Best MLflow run → `/home/cdsw/model_files` |
| `labs/cai/credit_scoring_api.py` | `predict()` for deployment |
| `labs/cai/cdsw-build.sh` | Build script for deployment |

Upload model to S3 for CDE local scoring:

```bash
cd /home/cdsw && tar czf model_files.tgz model_files/
hadoop fs -put -f model_files.tgz s3a://<bucket>/workshop/credit_scoring/models/<user>/model_files.tgz
```

## Alternative: CDE local model job

`04_batch_score_local.py` — downloads model from S3 via Spark, scores on driver.

May fail if CDE blocks `pip install` for xgboost/sklearn; prefer Step B+C in that case.

## Architecture layers (production mental model)

| Layer | Workshop location |
|-------|-------------------|
| Features | Iceberg `features` (CDE `02_build_features.py`) |
| Model training | CAI `04_train_credit_model.py` + MLflow Experiments |
| Model artifact | `/home/cdsw/model_files` + optional S3 tgz |
| Scores | Iceberg `scores` |
| SHAP explainability | CAI `06_explainability.py` |
| Bank policy / agent | Not in workshop — add Iceberg policy tables in production |
