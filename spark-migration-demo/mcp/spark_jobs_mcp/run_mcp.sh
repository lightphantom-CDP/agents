#!/usr/bin/env bash
# Run MCP server from CAI project (stdio). Used in Agent Studio MCP server command line.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CDSW_PROJECT="${CDSW_PROJECT:-csa-apac}"
export SPARK_JOBS_ROOT="${SPARK_JOBS_ROOT:-/home/cdsw/${CDSW_PROJECT}/spark-migration-demo}"
# Prefer project venv if present
if [[ -x "/home/cdsw/${CDSW_PROJECT}/.venv/bin/python" ]]; then
  PY="/home/cdsw/${CDSW_PROJECT}/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
exec "$PY" "$SCRIPT_DIR/server.py"
