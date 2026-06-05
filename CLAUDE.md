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
