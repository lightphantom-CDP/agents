#!/usr/bin/env python3
"""Minimal CAI Application entry point — use this as Script instead of app.py on PBJ Workbench."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "app.py"), run_name="__main__")
