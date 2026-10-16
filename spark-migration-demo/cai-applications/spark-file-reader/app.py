#!/usr/bin/env python3
"""
CAI Application — read spark-migration-demo files for Agent Studio tools.

Runs in the project context (same filesystem as Files UI), not in tool bwrap sandbox.
Bind: CDSW_APP_PORT

GET /read?path=spark-migration-demo/cde_jobs.yaml
GET /health
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

DEFAULT_PROJECT = "csa-apac"
SPARK_ROOT = "spark-migration-demo"
ALLOWED_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".txt", ".csv"}


def project_root() -> Path:
    slug = os.getenv("CDSW_PROJECT", DEFAULT_PROJECT).strip() or DEFAULT_PROJECT
    return Path(f"/home/cdsw/{slug}")


def resolve_path(raw: str) -> Path | None:
    raw = (raw or "").strip().lstrip("/")
    if not raw or ".." in raw:
        return None
    root = project_root()
    candidates = [
        root / raw,
        root / SPARK_ROOT / raw,
    ]
    for c in candidates:
        if c.is_file() and c.suffix.lower() in ALLOWED_SUFFIXES:
            try:
                c.resolve().relative_to(root.resolve())
            except ValueError:
                return None
            return c.resolve()
    return None


@app.get("/health")
def health():
    root = project_root()
    demo = root / SPARK_ROOT
    return jsonify(
        {
            "status": "ok",
            "project_root": str(root),
            "spark_demo_exists": demo.is_dir(),
        }
    )


@app.get("/read")
def read_file():
    path_param = request.args.get("path", "")
    resolved = resolve_path(path_param)
    if resolved is None:
        return jsonify(
            {
                "error": "file_not_found",
                "requested": path_param,
                "project_root": str(project_root()),
            }
        ), 404
    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return jsonify({"error": str(exc), "path": str(resolved)}), 500
    return jsonify(
        {
            "path": str(resolved),
            "size_bytes": resolved.stat().st_size,
            "content": content,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("CDSW_APP_PORT", "8090"))
    app.run(host="0.0.0.0", port=port, threaded=True)
