#!/usr/bin/env bash
# Run in CAI Terminal while the ray app engine is up (or from a project session).
# PBJ ipykernel uses Python 3.10 (ipykernel under /usr/local/lib/python3.10/...).
# Default `python3` is often 3.13 — do not treat that as "kernel OK".
set -euo pipefail

find_kernel_python() {
  local c
  for c in \
    "${PY:-}" \
    /usr/local/bin/python3.10 \
    /usr/bin/python3.10 \
    /usr/local/lib/python3.10/bin/python3 \
    /usr/local/lib/python3.10/bin/python3.10; do
    [[ -z "${c:-}" || ! -x "$c" ]] && continue
    if "$c" -c "import ipykernel" 2>/dev/null; then
      echo "$c"
      return 0
    fi
  done
  if command -v python3.10 >/dev/null 2>&1; then
    c="$(command -v python3.10)"
    if "$c" -c "import ipykernel" 2>/dev/null; then
      echo "$c"
      return 0
    fi
  fi
  return 1
}

if ! PY="$(find_kernel_python)"; then
  echo "ERROR: Could not find Python 3.10 with ipykernel (PBJ kernel)."
  echo "Checked: /usr/local/bin/python3.10, python3.10 on PATH, /usr/local/lib/python3.10/bin/python3"
  echo ""
  echo "Available interpreters:"
  ls -la /usr/local/bin/python* 2>/dev/null || true
  echo ""
  echo "Workaround: set CAI Application Editor to Standard and run start.py (no Jupyter kernel)."
  exit 1
fi

echo "=== PBJ kernel Python (must be 3.10 + ipykernel): $PY ==="
"$PY" -c "import sys, site; print('version:', sys.version); print('executable:', sys.executable); print('usersite:', site.getusersitepackages())"

diag() {
  "$PY" <<'PY'
import sys
if sys.version_info[:2] != (3, 10):
    print("WRONG interpreter for PBJ kernel (expected 3.10):", sys.version)
    raise SystemExit(1)
print("--- sys.path (first 10) ---")
for p in sys.path[:10]:
    print(" ", p)
try:
    import pygments
    print("pygments module:", pygments.__file__)
    import pygments.formatters  # noqa: F401
    from pygments.formatters.terminal256 import Terminal256Formatter
    print("pygments.formatters: OK on Python 3.10")
except Exception as exc:
    print("pygments check FAILED:", exc)
    raise SystemExit(1)
PY
}

if diag; then
  echo "Pygments OK for PBJ kernel (3.10). Restart the CAI Application."
  exit 0
fi

echo "=== Removing broken user-site pygments for 3.10 (shadowing) ==="
rm -rf \
  "${HOME}/.local/lib/python3.10/site-packages/pygments" \
  "${HOME}/.local/lib/python3.10/site-packages/pygments-"*.dist-info \
  "${HOME}/.local/lib/python3.10/site-packages/Pygments-"*.dist-info

echo "=== Installing pygments==2.18.0 for $PY (--user) ==="
"$PY" -m pip install --user --no-cache-dir --force-reinstall "pygments==2.18.0"

if ! diag; then
  echo "=== User install not visible; trying system site-packages for 3.10 ==="
  "$PY" -m pip install --no-cache-dir --force-reinstall "pygments==2.18.0"
  diag
fi

echo "=== Success. Restart the ray CAI Application (full restart). ==="
