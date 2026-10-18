#!/usr/bin/env bash
#
# InvestRadar hourly runner.
#
# Refreshes the scores and reports. Intended for cron, e.g.:
#   0 * * * * /path/to/agents/invest_radar/run_hourly.sh >> /tmp/invest_radar.log 2>&1
#
# Set COMMIT=1 to also commit the refreshed reports on your own machine.
set -euo pipefail

# Resolve the repo root (this script lives in <repo>/invest_radar/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] Running InvestRadar..."
"${PYTHON_BIN}" -m invest_radar

if [[ "${COMMIT:-0}" == "1" ]]; then
  git add invest_radar/reports invest_radar/index.html
  if ! git diff --cached --quiet; then
    git commit -m "chore(invest_radar): refresh hourly scores $(date -u '+%Y-%m-%dT%H:%MZ')"
    echo "Committed refreshed reports."
  else
    echo "No report changes to commit."
  fi
fi
