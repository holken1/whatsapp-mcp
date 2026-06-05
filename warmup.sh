#!/usr/bin/env bash
# Warm up the Render service before using the WhatsApp MCP server.
#
# Render's free tier spins the service down after inactivity; the next request
# triggers a cold start (~30-60s, often a 502 mid-boot). Run this first in a
# cloud routine and only invoke the MCP server once it exits 0.
#
# Polls /health until it returns 200, then exits 0. Exits 1 if the service
# does not come up within MAX_WAIT seconds.
set -euo pipefail

URL="${HEALTH_URL:-https://whatsapp-mcp-s9zs.onrender.com/health}"
MAX_WAIT="${MAX_WAIT:-180}"   # give up after this many seconds total
INTERVAL="${INTERVAL:-5}"     # wait between attempts

deadline=$(( $(date +%s) + MAX_WAIT ))
attempt=0
while true; do
  attempt=$((attempt + 1))
  # --max-time 60 lets a single request ride the cold start
  if curl -fsS --max-time 60 "$URL" >/dev/null 2>&1; then
    echo "Service is up (after $attempt attempt(s))."
    exit 0
  fi
  if (( $(date +%s) >= deadline )); then
    echo "Service did not come up within ${MAX_WAIT}s." >&2
    exit 1
  fi
  echo "Attempt $attempt: not ready, sleeping ${INTERVAL}s..."
  sleep "$INTERVAL"
done
