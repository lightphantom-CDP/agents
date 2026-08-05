#!/usr/bin/env bash
#
# Hourly runner for the Warren Buffett Investment Scorer.
#
# Add to your crontab to check every hour on the hour:
#
#   0 * * * * /full/path/to/warren_buffett_investment_scorer/run_hourly.sh >> \
#             /full/path/to/warren_buffett_investment_scorer/reports/cron.log 2>&1
#
# Set PUSHOVER_TOKEN and PUSHOVER_USER in the environment to get phone alerts
# whenever a holding crosses into "BUY" territory.
#
set -euo pipefail

# Resolve this script's directory so cron can call it from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer uv (used throughout this course); fall back to plain python3.
if command -v uv >/dev/null 2>&1; then
    uv run python -m investment_scorer --notify --quiet "$@"
else
    python3 -m investment_scorer --notify --quiet "$@"
fi
