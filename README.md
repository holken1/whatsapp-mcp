# whatsapp-mcp

A minimal MCP server that sends WhatsApp messages via [CallMeBot](https://www.callmebot.com/).

## Setup

Set the following environment variables:

```
CALLMEBOT_PHONE=+1234567890
CALLMEBOT_APIKEY=your_api_key
```

## Running locally (stdio, for Claude Code)

```bash
python whatsapp_server.py
```

## Running as HTTP server (for remote MCP clients)

```bash
python whatsapp_server.py streamable-http
```

The MCP endpoint will be available at `http://localhost:8000/mcp`.

## Deploying to Render

Push to GitHub and connect the repo in [Render](https://render.com). The `render.yaml` configures everything automatically — just set the two environment variables in the Render dashboard.

Once deployed, add `https://your-app.onrender.com/mcp` as a connector at [claude.ai/customize/connectors](https://claude.ai/customize/connectors).
