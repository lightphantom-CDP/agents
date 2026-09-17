#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/datahub/env.workshopdelh.sh"

# Iceberg on Data Hub is usually preconfigured. Uncomment if your cluster needs explicit catalog conf.
SPARK_EXTRA_CONF=(
  # --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
  # --conf spark.sql.catalog.hive=org.apache.iceberg.spark.SparkCatalog
  # --conf spark.sql.catalog.hive.type=hive
)

run_py() {
  local script_path="$1"
  shift
  echo "============================================================"
  echo "Running: ${script_path}"
  echo "Args: $*"
  echo "============================================================"
  spark3-submit \
    --master yarn \
    --deploy-mode client \
    "${SPARK_EXTRA_CONF[@]}" \
    "${script_path}" \
    "$@"
}

case "${1:-all}" in
  bronze)
    run_py "${SCRIPT_BASE}/01_ingest_bronze.py" \
      --catalog "${CREDIT_CATALOG}" \
      --database "${CREDIT_DATABASE}" \
      --raw-base-path "${RAW_BASE_PATH}"
    ;;
  silver)
    run_py "${SCRIPT_BASE}/02_build_silver_features.py" \
      --catalog "${CREDIT_CATALOG}" \
      --database "${CREDIT_DATABASE}"
    ;;
  gold)
    run_py "${SCRIPT_BASE}/03_publish_gold_features.py" \
      --catalog "${CREDIT_CATALOG}" \
      --database "${CREDIT_DATABASE}" \
      --feature-version "${FEATURE_VERSION}"
    ;;
  all)
    bash "${ROOT}/datahub/run_spark_jobs.sh" bronze
    bash "${ROOT}/datahub/run_spark_jobs.sh" silver
    bash "${ROOT}/datahub/run_spark_jobs.sh" gold
    ;;
  *)
    echo "Usage: $0 [bronze|silver|gold|all]"
    exit 1
    ;;
esac
