# Deploy ray-qwen-demo (Ray burst → existing Qwen vLLM)

Separate CAI Application from MediShield / Qwen. Ray runs on **CPU** in this app; GPU stays on your vLLM app.

## CAI Application settings

| Setting | Value |
|---------|--------|
| **Script** | `ray-test/start.py` or `ray-qwen-demo/start.py` |
| **Kernel** | **Python 3.13** (matches default `python3` + user pygments) or 3.10 if you fix pygments on 3.10 |
| **Editor** | PBJ Workbench (Flask uses `CDSW_READONLY_PORT`, e.g. 8100) or **Standard** if PBJ kernel is broken |
| **Spark** | OFF |

## Environment (typical)

```text
VLLM_BASE_URL=https://<your-qwen-cai-app-host>/v1
VLLM_MODEL_NAME=<exact id from GET .../v1/models>
RAY_NUM_WORKERS=8
RAY_BURST_PROMPT=Say hello in one short sentence.
```

`VLLM_BASE_URL` may omit `/v1` (the Ray app adds it). If burst shows **404** but **vLLM healthy**, set `VLLM_MODEL_NAME` to the exact `id` from the Qwen app’s `/v1/models`.

Optional: `RAY_APP_DIR=/home/cdsw/<project>/ray-test` if path auto-detect fails.

Do **not** set `CDSW_APP_PORT=0` or any port to `0` (engine log: `Duplicate port 0`).

## If the app is stuck / kernel dies (pygments)

Symptom in engine logs:

```text
ModuleNotFoundError: No module named 'pygments.formatters'
KernelRestarter: restart failed
```

Your stack trace loads ipykernel from **`/usr/local/lib/python3.10/site-packages/`**. On many runtimes **`/usr/local/bin/python3` is Python 3.13** (pygments under `~/.local/lib/python3.13/...`) while the **PBJ kernel is still 3.10** — so a test with `python3` can print `KERNEL OK` and the app still dies.

### Option A: align kernel with Python 3.13 (recommended on mixed runtimes)

If Terminal `python3` is **3.13** and pygments already works there, set the CAI Application **runtime/kernel to Python 3.13** (same as ML runtime when offered). Restart the app. The PBJ kernel then uses the same site-packages as your `pip install`.

Verify after restart:

```bash
python3 -c "import sys; print(sys.version); from pygments.formatters.terminal256 import Terminal256Formatter; print('OK')"
```

### Option B: use Standard editor instead of PBJ

In the CAI Application settings:

| Setting | Change |
|---------|--------|
| **Editor** | **Standard** (not PBJ Workbench) |
| **Script** | `ray-test/start.py` |

Standard mode runs your script without a healthy Jupyter kernel. Flask still binds **`CDSW_READONLY_PORT`** (8100) when PBJ is off, or **`CDSW_APP_PORT`** per `app.py`.

### Option C: fix pygments on Python 3.10 (only if you stay on 3.10 kernel)

In **Terminal** for this project (while the app pod is running):

```bash
cd ray-test   # or ray-qwen-demo
bash fix-pbj-pygments.sh
```

Or manually — **must** use **Python 3.10** (kernel), not `python3` if it is 3.13:

```bash
/usr/local/bin/python3.10 -c "import sys; print(sys.version); from pygments.formatters.terminal256 import Terminal256Formatter; print('KERNEL OK')"
/usr/local/bin/python3.10 -m pip install --user --force-reinstall 'pygments==2.18.0'
```

If that fails, run the script above, then **Restart** the application. Success in logs: `[ray-qwen-demo] start.py loading` and the read-only URL on **8100** (`ray-testing-leon`).

### Env cleanup

Remove any application env var that sets a port to **`0`** (`Duplicate port 0` in engine logs). Do not set `CDSW_APP_PORT=0`.

## Demo URLs

| URL | Purpose |
|-----|---------|
| `/` | Mini dashboard (burst button / KPIs) |
| `/health` | Health check |
| `/api/burst` | Parallel Ray workers → Qwen |
| `/api/ray/status` | Ray init status |
