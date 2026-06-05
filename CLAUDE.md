# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file Python MCP server (`whatsapp_server.py`) that exposes a `send_whatsapp` tool. It sends WhatsApp messages via the [CallMeBot](https://www.callmebot.com/) API.

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Required env vars
export CALLMEBOT_PHONE=+1234567890
export CALLMEBOT_APIKEY=your_api_key

# stdio transport (for Claude Code / local MCP clients)
python whatsapp_server.py

# HTTP transport (for remote MCP clients / Render deployment)
python whatsapp_server.py streamable-http
```

HTTP mode binds to `0.0.0.0:$PORT` (default 10000) and serves the MCP endpoint at `/mcp`. It also exposes a `GET /health` endpoint that returns `{"status": "ok"}` for plain HTTP health checks (e.g. `curl`, Render).

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CALLMEBOT_PHONE` | yes | — | Phone number to send messages to |
| `CALLMEBOT_APIKEY` | yes | — | CallMeBot API key |
| `PORT` | no | `10000` | HTTP listen port |

## Architecture

Everything lives in `whatsapp_server.py`:

- **`FastMCP` instance** — no auth, bound to `0.0.0.0`.

- **`send_whatsapp` tool** — the only MCP tool. Makes a GET request to the CallMeBot API and returns the response text. Apostrophes are passed as literal `'` (not percent-encoded) because CallMeBot silently drops `%27`.

- **Transport selection** — if `sys.argv[1] == "streamable-http"`, uvicorn serves `mcp.streamable_http_app()` with a `GET /health` route added; otherwise `mcp.run()` uses stdio.

## Deployment

The `render.yaml` deploys this as a Render web service using Python 3.13. After deploying, add `https://<your-app>.onrender.com/mcp` as a connector at claude.ai/customize/connectors.

## Waking the service (cold starts)

Render's free tier spins the service down after inactivity. The next request triggers a cold start (~30-60s, often a `502` mid-boot), which can cause the first MCP call from a cloud routine to fail.

`warmup.sh` handles this: it polls `/health` until it returns `200`, then exits `0` (or exits `1` after `MAX_WAIT` seconds). In a claude.ai cloud routine, connect this repo and have the agent run `./warmup.sh` first, only invoking the MCP server once it succeeds.

```bash
./warmup.sh
# Override defaults via env vars:
HEALTH_URL=https://<your-app>.onrender.com/health MAX_WAIT=240 INTERVAL=5 ./warmup.sh
```

This avoids a 24/7 keep-alive bot, which would burn the free tier's 750 monthly instance-hours.

> **Caveat:** this only helps if claude.ai connects to the MCP server *lazily* (on first tool call). If it connects eagerly at session start to enumerate tools, the cold-start failure happens before the script runs. Test by letting the service idle down (~15 min) and triggering the routine.
