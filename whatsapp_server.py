import os
import urllib.parse
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("whatsapp")

PHONE = os.environ["CALLMEBOT_PHONE"]
API_KEY = os.environ["CALLMEBOT_APIKEY"]


@mcp.tool()
def send_whatsapp(message: str) -> str:
    """Send a WhatsApp message to the configured number via CallMeBot."""
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={PHONE}&text={urllib.parse.quote(message)}&apikey={API_KEY}"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return f"Sent: {response.text.strip()}"


if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
