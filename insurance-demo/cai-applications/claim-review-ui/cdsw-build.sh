#!/usr/bin/env bash
# CAI Application build hook — runs before app starts.
set -euo pipefail

PY="${PYTHON:-python3}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[claim-review-ui] Installing Python dependencies..."
$PY -m pip install --upgrade pip
$PY -m pip install -r "$DIR/requirements.txt"

if [[ "${GUARDRAILS_MODE:-simple}" == "guardrails_ai" ]]; then
  echo "[claim-review-ui] GUARDRAILS_MODE=guardrails_ai — downloading Presidio models..."
  $PY -m guardrails_ai.detect_pii.post_install || {
    echo "WARN: post_install failed — app falls back to simple PII regex if Presidio unavailable."
  }
fi

echo "[claim-review-ui] Build complete."
