#!/usr/bin/env python3
"""
Ray + Qwen (vLLM) demo — separate CAI Application.

Does NOT replace your medical-review vLLM app. MediShield / Agent Studio keep their
existing Manager endpoint until you deliberately point them here.

Traffic paths:
  Production-style (later Manager cutover):
    POST /v1/chat/completions  →  vLLM only (no Ray in the hot path)

  Demo (Ray load / "mini dashboard"):
    POST /api/burst            →  Ray parallel tasks → same vLLM backend
    GET  /api/ray/status       →  cluster resources + optional Serve replicas
    GET  /                     →  mini dashboard (resource panel + burst table)

Environment:
  VLLM_BASE_URL          External vLLM OpenAI base, e.g. https://<qwen-app>/v1
  VLLM_MODEL_NAME        OpenAI model id exposed (default: qwen-ray-demo)
  RAY_QWEN_START_VLLM    true → spawn `vllm serve` locally (GPU app required)
  VLLM_MODEL             Model id/path for subprocess mode
  VLLM_INTERNAL_PORT     Local vLLM port (default 8101)
  RAY_INIT_ON_START      false (default) → ray.init on first burst (faster boot)
  RAY_NUM_CPUS           ray.init(num_cpus=...) (default 4)
  RAY_SERVE_REPLICAS     If >0, start Ray Serve replicas (CPU demo)
  RAY_DEMO_BURST_WORKERS Max parallel Ray tasks in flight per burst (default 8)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import threading
from typing import Any

import requests
from flask import Flask, Response, jsonify, request

APP = Flask(__name__)

_VLLM_PROC: subprocess.Popen[Any] | None = None
_RAY_INITIALIZED = False
_SERVE_STARTED = False


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _bool(name: str, default: bool = False) -> bool:
    v = _env(name, "true" if default else "false").lower()
    return v in ("1", "true", "yes", "on")


def _parse_port(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw or raw == "0":
        return None
    try:
        p = int(raw)
        return p if p > 0 else None
    except ValueError:
        return None


def _flask_host_port() -> tuple[str, int]:
    """Match Cloudera Flask rules (same idea as claim-review-ui)."""
    override = _parse_port(_env("RAY_QWEN_DEMO_PORT"))
    if override:
        return _env("CDSW_APP_HOST", "0.0.0.0") or "0.0.0.0", override

    readonly = _parse_port(_env("CDSW_READONLY_PORT", ""))
    if readonly:
        return "127.0.0.1", readonly

    editor = _env("ML_RUNTIME_EDITOR", "").lower()
    try:
        get_ipython()  # type: ignore[name-defined]
        in_pbj = True
    except NameError:
        in_pbj = False
    if "pbj" in editor or in_pbj:
        return "127.0.0.1", 8090

    app_port = _parse_port(_env("CDSW_APP_PORT", ""))
    if app_port:
        return _env("CDSW_APP_HOST", "0.0.0.0") or "0.0.0.0", app_port
    return "0.0.0.0", 8095


def vllm_internal_port() -> int:
    try:
        return int(_env("VLLM_INTERNAL_PORT", "8101"))
    except ValueError:
        return 8101


def vllm_base_url() -> str:
    """OpenAI-compatible base URL (must end with /v1 for chat/completions)."""
    explicit = _env("VLLM_BASE_URL").rstrip("/")
    if explicit:
        if not explicit.endswith("/v1"):
            explicit = f"{explicit}/v1"
        return explicit
    return f"http://127.0.0.1:{vllm_internal_port()}/v1"


def exposed_model_name() -> str:
    return _env("VLLM_MODEL_NAME", "qwen-ray-demo")


def _vllm_probe_urls() -> list[str]:
    root = vllm_base_url().rstrip("/").removesuffix("/v1")
    return [f"{root}/health", f"{root}/v1/models", f"{vllm_base_url().rstrip('/')}/models"]


def _probe_vllm() -> bool:
    for url in _vllm_probe_urls():
        try:
            if requests.get(url, timeout=5).status_code == 200:
                return True
        except requests.RequestException:
            continue
    return False


def _wait_vllm_ready(timeout_sec: int = 600) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _probe_vllm():
            return True
        time.sleep(3)
    return False


def _start_vllm_subprocess() -> None:
    global _VLLM_PROC
    if _VLLM_PROC is not None or not _bool("RAY_QWEN_START_VLLM"):
        return
    model = _env("VLLM_MODEL")
    if not model:
        print("[ray-qwen-demo] RAY_QWEN_START_VLLM=true but VLLM_MODEL empty — skip", file=sys.stderr)
        return
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--host", "127.0.0.1",
        "--port", str(vllm_internal_port()),
        "--served-model-name", exposed_model_name(),
    ]
    if _env("VLLM_GPU_MEMORY_UTILIZATION"):
        cmd += ["--gpu-memory-utilization", _env("VLLM_GPU_MEMORY_UTILIZATION")]
    if _env("VLLM_TENSOR_PARALLEL_SIZE"):
        cmd += ["--tensor-parallel-size", _env("VLLM_TENSOR_PARALLEL_SIZE")]
    print("[ray-qwen-demo] Starting vLLM:", " ".join(cmd), flush=True)
    _VLLM_PROC = subprocess.Popen(cmd)
    if not _wait_vllm_ready():
        print("[ray-qwen-demo] vLLM not healthy in time", file=sys.stderr)


def _init_ray() -> None:
    global _RAY_INITIALIZED, _SERVE_STARTED
    if _RAY_INITIALIZED:
        return
    import ray

    try:
        cpus = max(1, int(_env("RAY_NUM_CPUS", "4")))
    except ValueError:
        cpus = 4
    ray.init(
        num_cpus=cpus,
        ignore_reinit_error=True,
        include_dashboard=_bool("RAY_DASHBOARD", False),
        logging_level=_env("RAY_LOGGING_LEVEL", "warning") or "warning",
    )
    _RAY_INITIALIZED = True

    try:
        replicas = int(_env("RAY_SERVE_REPLICAS", "0"))
    except ValueError:
        replicas = 0
    if replicas > 0 and not _SERVE_STARTED:
        _start_serve_replicas(replicas)
        _SERVE_STARTED = True


def _serve_http_port() -> int:
    try:
        return int(_env("RAY_SERVE_HTTP_PORT", "8120"))
    except ValueError:
        return 8120


def _start_serve_replicas(num_replicas: int) -> None:
    from ray import serve

    base = vllm_base_url()
    serve.start(detached=True, http_options={"host": "127.0.0.1", "port": _serve_http_port()})

    @serve.deployment(num_replicas=num_replicas, ray_actor_options={"num_cpus": 0.25})
    class VllmFanout:
        def __init__(self) -> None:
            self._base = base

        async def __call__(self, request: Any) -> Any:
            payload = await request.json()
            r = requests.post(f"{self._base}/chat/completions", json=payload, timeout=120)
            r.raise_for_status()
            return r.json()

    serve.run(VllmFanout.bind(), name="qwen_vllm_fanout", route_prefix="/ray-serve")


def _chat_completion(payload: dict[str, Any], via_serve: bool = False) -> tuple[int, dict[str, Any]]:
    if via_serve and _SERVE_STARTED:
        url = f"http://127.0.0.1:{_serve_http_port()}/ray-serve/"
    else:
        url = f"{vllm_base_url()}/chat/completions"
    try:
        resp = requests.post(url, json=payload, timeout=180)
        try:
            body = resp.json()
        except json.JSONDecodeError:
            body = {"error": resp.text}
        return resp.status_code, body
    except requests.RequestException as exc:
        return 502, {"error": str(exc), "url": url}


def _startup() -> None:
    if _bool("RAY_QWEN_START_VLLM"):
        threading.Thread(target=_start_vllm_subprocess, daemon=True).start()
    elif not _env("VLLM_BASE_URL"):
        print("[ray-qwen-demo] No VLLM_BASE_URL and RAY_QWEN_START_VLLM=false", file=sys.stderr)
    if _bool("RAY_INIT_ON_START", False):
        try:
            _init_ray()
        except Exception as exc:
            print(f"[ray-qwen-demo] Ray init skipped/failed: {exc}", file=sys.stderr)


@APP.get("/health")
@APP.get("/healthcheck")
def health() -> Response:
    return jsonify(
        {
            "status": "ok",
            "app": "ray-qwen-demo",
            "vllm_base_url": vllm_base_url(),
            "vllm_healthy": _probe_vllm(),
            "ray_initialized": _RAY_INITIALIZED,
            "ray_serve_replicas": _env("RAY_SERVE_REPLICAS", "0"),
            "exposed_model": exposed_model_name(),
            "note": "MediShield claim-review is unchanged — this is a separate app.",
        }
    )


@APP.get("/v1/models")
def list_models() -> Response:
    return jsonify(
        {"object": "list", "data": [{"id": exposed_model_name(), "object": "model", "owned_by": "ray-qwen-demo"}]}
    )


@APP.post("/v1/chat/completions")
def chat_completions() -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    if not payload.get("model"):
        payload["model"] = exposed_model_name()
    status, body = _chat_completion(payload, via_serve=_bool("USE_RAY_SERVE_FOR_V1", False))
    return jsonify(body), status


@APP.get("/api/ray/status")
def ray_status() -> Response:
    if not _RAY_INITIALIZED:
        try:
            _init_ray()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
    import ray

    return jsonify(
        {
            "cluster_resources": ray.cluster_resources(),
            "available_resources": ray.available_resources(),
            "serve_enabled": _SERVE_STARTED,
            "ray_initialized": _RAY_INITIALIZED,
            "vllm_base_url": vllm_base_url(),
        }
    )


@APP.post("/api/burst")
def api_burst() -> Response:
    if not _RAY_INITIALIZED:
        _init_ray()
    import ray

    body = request.get_json(force=True, silent=True) or {}
    try:
        n = min(32, max(1, int(body.get("n", 5))))
    except (TypeError, ValueError):
        n = 5
    prompt = str(body.get("prompt") or "Reply with exactly: OK")
    try:
        max_tokens = int(body.get("max_tokens", 8))
    except (TypeError, ValueError):
        max_tokens = 8

    base = vllm_base_url()
    model = exposed_model_name()

    @ray.remote
    def _one(i: int) -> dict[str, Any]:
        t0 = time.perf_counter()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": f"[{i}] {prompt}"}],
            "max_tokens": max_tokens,
        }
        try:
            r = requests.post(f"{base}/chat/completions", json=payload, timeout=180)
            return {"index": i, "status_code": r.status_code, "latency_sec": round(time.perf_counter() - t0, 3), "ok": r.ok}
        except requests.RequestException as exc:
            return {"index": i, "ok": False, "error": str(exc), "latency_sec": round(time.perf_counter() - t0, 3)}

    try:
        max_workers = max(1, int(_env("RAY_DEMO_BURST_WORKERS", "8")))
    except ValueError:
        max_workers = 8

    t0 = time.perf_counter()
    pending = [_one.remote(i) for i in range(n)]
    results: list[dict[str, Any]] = []
    remaining = list(pending)
    while remaining:
        done, remaining = ray.wait(remaining, num_returns=min(max_workers, len(remaining)), timeout=300)
        if not done:
            break
        results.extend(ray.get(done))
    wall = time.perf_counter() - t0
    results.sort(key=lambda x: x.get("index", 0))

    lat_sum = round(sum(float(r.get("latency_sec", 0)) for r in results), 3)
    ok_count = sum(1 for r in results if r.get("ok"))
    speedup = round(lat_sum / wall, 2) if wall > 0 else 0.0
    return jsonify(
        {
            "n": n,
            "wall_sec": round(wall, 3),
            "latency_sum_sec": lat_sum,
            "parallel_speedup": speedup,
            "ok": ok_count,
            "failed": n - ok_count,
            "results": results,
            "vllm_base_url": base,
            "model": model,
        }
    )


@APP.get("/")
def index() -> Response:
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Ray + Qwen — mini dashboard</title>
<style>
  :root { --bg:#0b1020; --card:#151c33; --line:#263150; --fg:#e6ebff; --mut:#8ea0c9;
          --ok:#2ecc71; --bad:#ff5a5f; --accent:#4c8dff; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; margin:0; background:var(--bg); color:var(--fg); }
  header { padding:18px 24px; border-bottom:1px solid var(--line); display:flex; align-items:center; gap:12px; }
  header h1 { font-size:18px; margin:0; }
  .tag { font-size:12px; color:var(--mut); border:1px solid var(--line); padding:2px 8px; border-radius:999px; }
  main { padding:24px; display:grid; gap:18px; max-width:1000px; margin:0 auto; }
  .grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .kpi .v { font-size:26px; font-weight:700; }
  .kpi .l { font-size:12px; color:var(--mut); margin-top:4px; }
  .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  button { background:var(--accent); color:#fff; border:0; padding:10px 16px; border-radius:8px; font-size:14px; cursor:pointer; }
  button.secondary { background:#223; border:1px solid var(--line); }
  input { width:70px; background:#0e1427; color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:600; }
  .pill { font-size:11px; padding:2px 8px; border-radius:999px; }
  .pill.ok { background:rgba(46,204,113,.15); color:var(--ok); }
  .pill.bad { background:rgba(255,90,95,.15); color:var(--bad); }
  .bar { height:8px; background:#0e1427; border-radius:6px; overflow:hidden; min-width:120px; }
  .bar > span { display:block; height:100%; background:var(--accent); }
  .mut { color:var(--mut); font-size:12px; }
  code { background:#0e1427; padding:2px 6px; border-radius:4px; }
</style></head><body>
<header>
  <h1>Ray + Qwen (vLLM)</h1>
  <span class="tag" id="model">model …</span>
  <span class="tag" id="vllm">vLLM …</span>
  <span class="tag" id="vhealth">health …</span>
</header>
<main>
  <div class="card">
    <div class="row">
      <strong>Burst</strong>
      <label class="mut">requests <input id="n" type="number" value="8" min="1" max="32"></label>
      <button onclick="runBurst()">Run burst</button>
      <button class="secondary" onclick="refreshStatus()">Refresh resources</button>
      <span class="mut" id="busy"></span>
    </div>
  </div>

  <div class="grid">
    <div class="card kpi"><div class="v" id="k_wall">–</div><div class="l">Wall time (s) — parallel</div></div>
    <div class="card kpi"><div class="v" id="k_sum">–</div><div class="l">Σ latency (s) — if serial</div></div>
    <div class="card kpi"><div class="v" id="k_speed">–</div><div class="l">Parallel speedup ×</div></div>
    <div class="card kpi"><div class="v" id="k_ok">–</div><div class="l">OK / failed</div></div>
  </div>

  <div class="card">
    <strong>Per-request latency</strong>
    <div class="mut">Rising latency = requests queued on one Qwen GPU (max-num-seqs / burst workers).</div>
    <table id="tbl"><thead><tr><th>#</th><th>Status</th><th>Latency (s)</th><th>Relative</th></tr></thead>
    <tbody><tr><td colspan="4" class="mut">Run a burst to populate…</td></tr></tbody></table>
  </div>

  <div class="card">
    <strong>Ray cluster resources</strong>
    <div class="mut">Ray runs on CPU here. The GPU lives on your Qwen app, not this app.</div>
    <table id="res"><thead><tr><th>Resource</th><th>Total</th><th>Available</th></tr></thead>
    <tbody><tr><td colspan="3" class="mut">Click “Refresh resources”…</td></tr></tbody></table>
  </div>
</main>
<script>
async function boot() {
  try {
    const h = await (await fetch('/health')).json();
    document.getElementById('model').textContent = 'model: ' + h.exposed_model;
    document.getElementById('vllm').textContent = 'vLLM: ' + h.vllm_base_url;
    const ok = h.vllm_healthy;
    const el = document.getElementById('vhealth');
    el.textContent = ok ? 'vLLM healthy' : 'vLLM UNREACHABLE';
    el.style.color = ok ? 'var(--ok)' : 'var(--bad)';
  } catch(e) {}
}
async function refreshStatus() {
  const body = document.querySelector('#res tbody');
  body.innerHTML = '<tr><td colspan="3" class="mut">loading…</td></tr>';
  try {
    const s = await (await fetch('/api/ray/status')).json();
    if (s.error) { body.innerHTML = '<tr><td colspan="3" class="pill bad">'+s.error+'</td></tr>'; return; }
    const tot = s.cluster_resources || {}, av = s.available_resources || {};
    const keys = Object.keys(tot).sort();
    body.innerHTML = keys.map(k => {
      const t = typeof tot[k]==='number' ? (tot[k]>1e6 ? (tot[k]/1e9).toFixed(2)+' GB' : tot[k]) : tot[k];
      const a = av[k]!==undefined ? (typeof av[k]==='number' ? (av[k]>1e6 ? (av[k]/1e9).toFixed(2)+' GB' : av[k]) : av[k]) : '–';
      return '<tr><td><code>'+k+'</code></td><td>'+t+'</td><td>'+a+'</td></tr>';
    }).join('');
  } catch(e) { body.innerHTML = '<tr><td colspan="3" class="pill bad">'+e+'</td></tr>'; }
}
async function runBurst() {
  const n = parseInt(document.getElementById('n').value || '8', 10);
  const busy = document.getElementById('busy');
  busy.textContent = 'running '+n+' requests via Ray…';
  try {
    const r = await (await fetch('/api/burst', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ n, prompt:'Reply with exactly: OK', max_tokens:8 })
    })).json();
    document.getElementById('k_wall').textContent = r.wall_sec;
    document.getElementById('k_sum').textContent = r.latency_sum_sec;
    document.getElementById('k_speed').textContent = r.parallel_speedup + '×';
    document.getElementById('k_ok').textContent = r.ok + ' / ' + r.failed;
    const max = Math.max(...r.results.map(x => x.latency_sec || 0), 0.001);
    const body = document.querySelector('#tbl tbody');
    body.innerHTML = r.results.map(x => {
      const pct = Math.round((x.latency_sec||0)/max*100);
      const pill = x.ok ? '<span class="pill ok">'+(x.status_code||'ok')+'</span>'
                        : '<span class="pill bad">'+(x.status_code||'err')+'</span>';
      return '<tr><td>'+x.index+'</td><td>'+pill+'</td><td>'+(x.latency_sec||'–')+
             '</td><td><div class="bar"><span style="width:'+pct+'%"></span></div></td></tr>';
    }).join('');
    busy.textContent = 'done — wall '+r.wall_sec+'s vs Σ '+r.latency_sum_sec+'s';
  } catch(e) { busy.textContent = 'error: '+e; }
  refreshStatus();
}
boot();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


def main() -> None:
    _startup()
    bind_override = _env("RAY_QWEN_BIND")
    host, port = _flask_host_port()
    if bind_override:
        host = bind_override
    print(f"[ray-qwen-demo] Listening on http://{host}:{port}", flush=True)
    APP.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
