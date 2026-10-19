#!/usr/bin/env bash
set -euo pipefail

PY="${PYTHON:-python3}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[ray-qwen-demo] Installing Python dependencies..."
$PY -m pip install --upgrade pip
$PY -m pip install -r "$DIR/requirements.txt"
echo "[ray-qwen-demo] Build complete."
