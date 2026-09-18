#!/usr/bin/env bash
# Diagnose uvx --from path issues on CAI.
set -euo pipefail

PROJECT="${CDSW_PROJECT:-unknown}"
CANDIDATES=(
  "/home/cdsw/${PROJECT}/mcp"
  "/home/cdsw/${PROJECT}/insurance-demo/mcp"
  "$(pwd)"
)

echo "CDSW_PROJECT=${PROJECT}"
echo "Looking for MCP package..."

FOUND=""
for dir in "${CANDIDATES[@]}"; do
  if [[ -f "${dir}/pyproject.toml" && -f "${dir}/notify_server.py" ]]; then
    FOUND="${dir}"
    break
  fi
done

if [[ -z "${FOUND}" ]]; then
  echo "ERROR: No valid mcp/ folder found."
  echo "Expected pyproject.toml + notify_server.py in one of:"
  printf '  - %s\n' "${CANDIDATES[@]}"
  echo ""
  echo "Upload the mcp/ folder from insurance-demo/mcp/ to your CAI project."
  exit 1
fi

echo "OK: package dir = ${FOUND}"
ls -la "${FOUND}"

if grep -q 'name = "agents"' "${FOUND}/pyproject.toml" 2>/dev/null; then
  echo "ERROR: pyproject.toml has name = agents (wrong file). Upload insurance-demo/mcp/pyproject.toml"
  exit 1
fi

echo "Removing stray notebook files that break setuptools..."
rm -f "${FOUND}/Untitled.py" "${FOUND}/=1.2.0" 2>/dev/null || true

export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uvx >/dev/null 2>&1; then
  echo "Installing uv..."
  python3 -m pip install --user -U uv
  export PATH="${HOME}/.local/bin:${PATH}"
fi

echo ""
echo "Building wheel..."
(cd "${FOUND}" && uv build)

WHEEL="$(ls -1 "${FOUND}"/dist/*.whl | tail -1)"
echo "Wheel: ${WHEEL}"

echo ""
echo "Smoke test (5s timeout is OK)..."
if command -v timeout >/dev/null 2>&1; then
  timeout 5 uvx --from "${FOUND}" leon-hospital-notify || true
else
  uvx --from "${FOUND}" leon-hospital-notify &
  sleep 5
  kill $! 2>/dev/null || true
fi

echo ""
echo "=== Use this path in Agent Studio MCP JSON ==="
echo "${FOUND}"
echo ""
echo "=== Or register from the built wheel ==="
echo "${WHEEL}"
