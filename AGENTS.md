# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **"Complete Agentic AI Engineering Course"** by Ed Donner: a Python monorepo
managed by [`uv`](https://docs.astral.sh/uv/) (Python 3.12+, pinned in `.python-version`). It is a
collection of teaching labs / demo apps organized by week:

| Dir | Week / topic |
| --- | --- |
| `1_foundations` | Raw LLM API calls + a Gradio chat app (`app.py`) |
| `2_openai` | OpenAI Agents SDK |
| `3_crew` | CrewAI projects (run via the `crewai` CLI tool) |
| `4_langgraph` | LangGraph |
| `5_autogen` | AutoGen |
| `6_mcp` | Model Context Protocol |

There is **no formal unit-test suite and no configured linter** (no `ruff`/`flake8`/`pytest`
config). "Testing" in this course means running the labs (Jupyter notebooks under each week and the
`community_contributions/` folders) and the demo apps. See `README.md` and `setup/SETUP-linux.md`
for the canonical setup, and `guides/` (esp. `guides/09_ai_apis_and_ollama.ipynb`) for API/Ollama
options.

### Environment (already provisioned by the update script)
- `uv sync` installs the venv (`.venv`) with all deps. Run any script/module with `uv run ...`
  (e.g. `uv run python 1_foundations/app.py`). Do **not** `pip install`; use `uv add` / `uv run`.
- `crewai` is installed as a **global `uv` tool** (`uv tool install crewai==0.130.0 --python 3.12`),
  NOT as a venv package. So `import crewai` inside `.venv` fails by design — use the `crewai` CLI
  (`crewai version`, `crewai run` from inside a crew project such as `3_crew/debate`). Confirm with
  `uv tool list`.
- `uv` is on `PATH` via `~/.local/bin` (added to `~/.bashrc` / `~/.profile`).

### API keys / running the real labs
- The labs call frontier LLM APIs and expect a project-root `.env` file (git-ignored), e.g.
  `OPENAI_API_KEY=...`, `ANTHROPIC_API_KEY=...`, `GOOGLE_API_KEY=...` (+ `GEMINI_API_KEY` for
  Gemini in Crew). No `.env` ships with the repo. Add the keys you need as Cursor secrets/`.env`.
- **Free / no-key alternative (Ollama)** — useful for smoke-testing without spending on APIs.
  The course code uses `OpenAI()` (default model `gpt-4o-mini` in `1_foundations/app.py`), so you
  can point it at a local Ollama server *without editing code*:
  1. `ollama serve` (systemd is NOT running in the VM, so start it manually, e.g. in a tmux session).
  2. `ollama pull llama3.2:3b` then alias it to the model name the code expects:
     `ollama cp llama3.2:3b gpt-4o-mini`.
  3. Run with `OPENAI_BASE_URL=http://127.0.0.1:11434/v1 OPENAI_API_KEY=ollama uv run python 1_foundations/app.py`.
  Note: small local models handle tool-calling less reliably than the real APIs; use real keys for
  faithful behavior.

### Running the Gradio apps (dev mode)
- `uv run python 1_foundations/app.py` serves on `http://127.0.0.1:7860`. It reads
  `1_foundations/me/linkedin.pdf` + `me/summary.txt` to build the system prompt, so run it from a
  context where those relative paths resolve (the script `cd`s are not needed since paths are
  relative to `1_foundations/`; launch from that dir or the repo root works because `app.py` uses
  `me/...`). Gradio keeps live SSE/websocket connections open, so browser automation should wait on
  `domcontentloaded` (NOT `networkidle`, which never settles).

### Notes
- `setup/diagnostics.py` runs a `speedtest-cli` bandwidth test that can hang/fail in a sandboxed
  VM — it's a student support tool, not required for development; skip it or expect the network step
  to be slow/noisy.
