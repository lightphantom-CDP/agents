# Leon Hospital MCP Servers

Real **Model Context Protocol** servers for the insurance demo.

## MCP server: `leon_hospital_notify`

| File | Role |
|------|------|
| `notify_server.py` | MCP server (stdio) — tool `notify_manual_review_ticket` |
| `notify_lib.py` | ntfy.sh + Slack HTTP (shared) |
| `mcp_client.py` | Python MCP client (Flask + Agent Studio bridge) |
| `mcp_params.py` | OpenAI Agents SDK server params |
| `demo_mcp_agent.py` | Local agent demo with `MCPServerStdio` |

---

## Quick start (local)

```bash
cd insurance-demo/mcp
pip install -r requirements.txt
export NTFY_TOPIC=leon-hospital-claims

# Test MCP tool call
python -c "from mcp_client import notify_via_mcp; print(notify_via_mcp('CLM-50001', 'clinical review'))"

# Run MCP server standalone (stdio — for Cursor)
python notify_server.py
```

---

## CAI deployment

See [`../DEPLOY-MCP.md`](../DEPLOY-MCP.md).

Upload the whole `mcp/` folder. Both **claim-review-ui** and **notify_manual_review** Agent Studio tool call `mcp_client.py` → `notify_server.py`.

---

## Cursor MCP config

See `cursor-mcp.json.example`.

---

## When notifications fire

**Only manual review** (e.g. CLM-50001). Not for approved / rejected / partial.

Channels: **ntfy.sh** (free) and optional **Slack webhook**.
