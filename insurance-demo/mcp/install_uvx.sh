#!/usr/bin/env bash
# Install uv/uvx for Agent Studio MCP registration (CAI project session).
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

if command -v uvx >/dev/null 2>&1; then
  echo "uvx already on PATH: $(command -v uvx)"
  uvx --version
  exit 0
fi

echo "Installing uv (provides uvx)..."
python3 -m pip install --user -U uv

if command -v uvx >/dev/null 2>&1; then
  echo "uvx installed: $(command -v uvx)"
  uvx --version
  exit 0
fi

# pip --user may not be on PATH in notebooks
if [[ -x "${BIN_DIR}/uvx" ]]; then
  echo "uvx at ${BIN_DIR}/uvx"
  "${BIN_DIR}/uvx" --version
  exit 0
fi

if [[ -x "${BIN_DIR}/uv" ]]; then
  cat > "${BIN_DIR}/uvx" <<'EOF'
#!/usr/bin/env bash
exec "$(dirname "$0")/uv" tool run "$@"
EOF
  chmod +x "${BIN_DIR}/uvx"
  echo "Created uvx shim at ${BIN_DIR}/uvx"
  "${BIN_DIR}/uvx" --version
  exit 0
fi

echo "ERROR: uv/uvx not found after install. Try:"
echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
exit 1
