#!/usr/bin/env python3
"""CAI Application entry — Ray + Qwen (vLLM) demo (separate from claim-review)."""

import os
import runpy
import subprocess
import sys
from pathlib import Path


def _app_dir() -> Path:
    """Locate ray-test/ (or ray-qwen-demo/) when CAI runs this as a notebook cell.

    In that mode __file__ is missing and cwd is often /home/cdsw — not the project tree.
    """
    override = os.getenv("RAY_APP_DIR", "").strip()
    if override:
        path = Path(override).resolve()
        if (path / "app.py").is_file():
            return path
        raise RuntimeError(f"RAY_APP_DIR set but no app.py in {path}")

    script_path = globals().get("__file__")
    if script_path:
        here = Path(script_path).resolve().parent
        if (here / "app.py").is_file():
            return here

    project_dir = os.getenv("CDSW_PROJECT_DIR", "").strip()
    project = os.getenv("CDSW_PROJECT", "").strip()

    bases: list[Path] = []
    if project_dir:
        bases.append(Path(project_dir).resolve())
    if project:
        bases.append(Path(f"/home/cdsw/{project}"))
    cwd = Path.cwd().resolve()
    if cwd not in bases:
        bases.append(cwd)

    subdirs = ("ray-test", "ray-qwen-demo", "cai-applications/ray-qwen-demo")

    for base in bases:
        if not base.is_dir():
            continue
        for sub in subdirs:
            candidate = (base / sub).resolve()
            if (candidate / "app.py").is_file():
                return candidate
        for name in ("ray-test", "ray-qwen-demo"):
            for candidate in base.glob(f"**/{name}"):
                if candidate.is_dir() and (candidate / "app.py").is_file():
                    return candidate.resolve()

    raise RuntimeError(
        "Could not find ray app directory (expected ray-test/ or ray-qwen-demo/ with app.py). "
        f"CDSW_PROJECT={project or '(unset)'} CDSW_PROJECT_DIR={project_dir or '(unset)'} cwd={cwd}. "
        "Set RAY_APP_DIR=/home/cdsw/<project>/ray-test on the CAI Application."
    )


def _ensure_deps(app_dir: Path) -> None:
    """Install requirements if missing — CAI does not always run cdsw-build.sh."""
    if os.getenv("RAY_SKIP_PIP", "").strip().lower() in ("1", "true", "yes"):
        return
    missing = []
    for mod in ("flask", "requests", "ray"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        return
    req = app_dir / "requirements.txt"
    print(f"[ray-qwen-demo] Missing {missing} — installing {req}", flush=True)
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir"]
    cmd += ["-r", str(req)] if req.is_file() else ["flask>=3.0,<4", "requests>=2.31,<3", "ray[default]>=2.9,<3"]
    subprocess.check_call(cmd)
    print("[ray-qwen-demo] Dependency install complete.", flush=True)


def main() -> None:
    app_dir = _app_dir()
    _ensure_deps(app_dir)
    app_py = app_dir / "app.py"
    os.chdir(app_dir)
    sys.path.insert(0, str(app_dir))
    print(f"[ray-qwen-demo] start.py loading {app_py}", flush=True)
    runpy.run_path(str(app_py), run_name="__main__")


main()
