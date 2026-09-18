#!/usr/bin/env python3
"""
CAI Application — Qdrant vector DB (Jupyter / PBJ runtime).

JUPYTER RUNTIME PATTERN (what your senior means)
------------------------------------------------
When the Application uses a Jupyter/PBJ editor:
  - Jupyter kernel gateway owns $CDSW_APP_PORT (usually 8100) — do NOT bind Qdrant there.
  - Start Qdrant as a detached background daemon on port 6333.
  - Return cleanly so the Jupyter kernel stays alive → Application shows "Running".
  - Connect from a notebook IN THIS SAME APPLICATION via:
        http://127.0.0.1:6333

Do NOT run this script from a separate Sessions notebook — that is a different pod.

APPLICATION SETTINGS
--------------------
  Name       : qdrant
  Subdomain  : qdrantleo
  Script     : agent-studio/run_qdrant.py
  Kernel     : Python 3.10
  Editor     : PBJ Workbench / Jupyter   ← senior's "runtime jupyter"
  Spark      : OFF
  Resources  : 1 vCPU / 2-4 GiB

AFTER THE APP IS RUNNING
------------------------
Open the Qdrant application's Workbench notebook and run:

    os.environ["QDRANT_URL"] = "http://127.0.0.1:6333"
    from agent.qdrant_policy_rag import index_policy
    index_policy(policy_path="data/policy/coverage_policy.md")
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

QDRANT_VERSION = "v1.11.3"
INSTALL_DIR = Path.home() / "qdrant"
DATA_DIR = Path.home() / "qdrant_storage"
BINARY = INSTALL_DIR / "qdrant"
DEFAULT_HTTP_PORT = 6333

TARBALLS = [
    f"https://github.com/qdrant/qdrant/releases/download/{QDRANT_VERSION}/"
    "qdrant-x86_64-unknown-linux-gnu.tar.gz",
    f"https://github.com/qdrant/qdrant/releases/download/{QDRANT_VERSION}/"
    "qdrant-x86_64-unknown-linux-musl.tar.gz",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def find_binary() -> Path | None:
    if BINARY.exists():
        return BINARY
    for path in INSTALL_DIR.glob("**/qdrant"):
        if path.is_file():
            return path
    return None


def download_binary() -> Path:
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for url in TARBALLS:
        archive = INSTALL_DIR / "qdrant.tar.gz"
        log(f"Downloading Qdrant {QDRANT_VERSION} from {url} ...")
        try:
            urllib.request.urlretrieve(url, archive)
        except Exception as exc:
            log(f"  download failed: {exc}")
            continue

        extract_to = INSTALL_DIR / "extract"
        shutil.rmtree(extract_to, ignore_errors=True)
        extract_to.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(path=extract_to)

        for candidate in extract_to.glob("**/qdrant"):
            if candidate.is_file():
                shutil.copy2(candidate, BINARY)
                BINARY.chmod(0o755)
                log(f"Installed Qdrant binary at {BINARY}")
                return BINARY

    raise RuntimeError("Could not download / extract a Qdrant binary")


def kill_stale_qdrant() -> None:
    log("Stopping stale Qdrant processes (if any) ...")
    subprocess.run(["pkill", "-9", "qdrant"], check=False)
    time.sleep(2)


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(port: int, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_is_open("127.0.0.1", port):
            return True
        time.sleep(0.5)
    return False


def http_port() -> int:
    return int(os.environ.get("QDRANT_HTTP_PORT", DEFAULT_HTTP_PORT))


def is_jupyter_runtime() -> bool:
    """Jupyter/PBJ holds CDSW_APP_PORT; Qdrant must use a separate port."""
    return bool(os.environ.get("CDSW_APP_PORT"))


def start_qdrant_daemon(binary: Path, http_port: int) -> subprocess.Popen:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / "qdrant.log"

    env = os.environ.copy()
    env["QDRANT__SERVICE__HOST"] = "0.0.0.0"
    env["QDRANT__SERVICE__HTTP_PORT"] = str(http_port)
    env["QDRANT__SERVICE__ENABLE_GRPC"] = "false"
    env["QDRANT__STORAGE__STORAGE_PATH"] = str(DATA_DIR)

    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [str(binary)],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # detached daemon — survives when startup cell returns
    )
    log(f"Qdrant daemon PID={proc.pid}, logs: {log_path}")
    return proc


def main() -> None:
    kill_stale_qdrant()

    binary = find_binary() or download_binary()
    port = http_port()
    app_port = os.environ.get("CDSW_APP_PORT", "not set")

    log(f"Platform      : {platform.platform()} / {platform.machine()}")
    log(f"Binary        : {binary}")
    log(f"Storage       : {DATA_DIR}")
    log(f"CDSW_APP_PORT : {app_port}  (Jupyter/PBJ — leave this to the kernel)")
    log(f"Qdrant port   : {port}")

    if is_jupyter_runtime():
        log("Runtime mode  : Jupyter/PBJ — starting Qdrant as background daemon on 6333")
        log("Do NOT bind Qdrant to CDSW_APP_PORT (kernel already uses it).")
    else:
        log("Runtime mode  : non-Jupyter — starting Qdrant as background daemon")

    if port_is_open("127.0.0.1", port):
        log(f"Qdrant already listening on 127.0.0.1:{port} — skipping start.")
    else:
        proc = start_qdrant_daemon(binary, port)
        if not wait_for_port(port):
            log("FATAL: Qdrant did not open port in time. Last log lines:")
            try:
                log((DATA_DIR / "qdrant.log").read_text(encoding="utf-8")[-4000:])
            except OSError:
                pass
            proc.terminate()
            raise RuntimeError(f"Qdrant did not open port {port}")

    log("")
    log("=" * 60)
    log("Qdrant is READY")
    log("=" * 60)
    log(f"  Inside this Application notebook:  http://127.0.0.1:{port}")
    log(f"  Health check:  curl http://127.0.0.1:{port}/collections")
    log("")
    log("Next — open THIS app's Workbench and index policy:")
    log('  os.environ["QDRANT_URL"] = "http://127.0.0.1:6333"')
    log('  from agent.qdrant_policy_rag import index_policy')
    log('  index_policy(policy_path="data/policy/coverage_policy.md")')
    log("")
    log("Startup complete. Jupyter kernel stays alive → app should show Running.")

    # CRITICAL for Jupyter runtime:
    #   - no os.execve  (kills kernel → "Jupyter kernel stopped")
    #   - no proc.wait() on CDSW_APP_PORT (address in use)
    #   - no sys.exit(0) (can kill PBJ engine)
    return


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FATAL: {exc}")
        raise
