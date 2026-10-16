#!/usr/bin/env python3
"""CAI Application entry — works when Script is run as a file or from a JupyterLab app runtime.

Self-bootstraps Flask if the application runtime did not install requirements.txt.
"""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path


def _app_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        # PBJ / JupyterLab application runtime may exec without __file__
        slug = os.getenv("CDSW_PROJECT", "csa-apac").strip() or "csa-apac"
        candidates = [
            Path.cwd() / "spark-migration-demo/cai-applications/spark-file-reader",
            Path(f"/home/cdsw/{slug}/spark-migration-demo/cai-applications/spark-file-reader"),
            Path("/home/cdsw/spark-migration-demo/cai-applications/spark-file-reader"),
        ]
        for base in candidates:
            if (base / "app.py").is_file():
                return base.resolve()
        return Path.cwd()


def _ensure_flask() -> None:
    try:
        import flask  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    print("[spark-file-reader] Flask not found — installing...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "flask>=3.0.0"],
        check=True,
    )
    # make freshly installed --user packages importable in this process
    import site
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.insert(0, user_site)


_ensure_flask()
runpy.run_path(str(_app_dir() / "app.py"), run_name="__main__")
