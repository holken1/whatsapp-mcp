import logging
import os
import sys
import time
import urllib.parse
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("whatsapp-mcp")

mcp = FastMCP("whatsapp", host="0.0.0.0")


def _client_ip(scope):
    """Real client IP, honoring X-Forwarded-For (Render sits behind a proxy)."""
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            return value.decode().split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "-"


class AccessLogMiddleware:
    """Log one line per HTTP request. Pure ASGI so it won't buffer MCP streams."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status = {"code": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                '%s "%s %s" %s %.1fms',
                _client_ip(scope),
                scope.get("method"),
                scope.get("path"),
                status["code"],
                duration_ms,
            )

PHONE = os.environ["CALLMEBOT_PHONE"]
API_KEY = os.environ["CALLMEBOT_APIKEY"]


@mcp.tool()
def send_whatsapp(message: str) -> str:
    """Send a WhatsApp message to the configured number via CallMeBot."""
    encoded = urllib.parse.quote(message, safe="'")
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={PHONE}&text={encoded}&apikey={API_KEY}"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return f"Sent: {response.text.strip()}"


@mcp.tool()
def get_weather(location: str) -> str:
    """Get current weather for a location using wttr.in."""
    encoded = urllib.parse.quote(location)
    url = f"https://wttr.in/{encoded}?format=3"
    response = httpx.get(url, timeout=10, headers={"User-Agent": "curl/7.0"})
    response.raise_for_status()
    return response.text.strip()


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        import uvicorn
        from starlette.responses import JSONResponse
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        port = int(os.environ.get("PORT", 10000))
        app = mcp.streamable_http_app()

        async def health(request):
            return JSONResponse({"status": "ok"})

        app.add_route("/health", health, methods=["GET"])
        app.add_middleware(AccessLogMiddleware)
        # access_log=False: our middleware already logs each request (with the
        # real client IP and latency), so skip uvicorn's duplicate line.
        uvicorn.run(app, host="0.0.0.0", port=port, access_log=False)
    else:
        mcp.run()
