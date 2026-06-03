import os
import sys
import urllib.parse
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("whatsapp", host="0.0.0.0")

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


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        import uvicorn
        port = int(os.environ.get("PORT", 10000))
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        mcp.run()
