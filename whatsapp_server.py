import json
import os
import secrets
import sys
import time
import urllib.parse

import httpx
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

PHONE = os.environ["CALLMEBOT_PHONE"]
API_KEY = os.environ["CALLMEBOT_APIKEY"]
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("BASE_URL", "http://localhost:10000")
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "claude-ai")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")


class SimpleOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self):
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.access_tokens: dict[str, AccessToken] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}

    def preregister_client(self, client_id: str, client_secret: str) -> None:
        from pydantic import AnyUrl
        self.clients[client_id] = OAuthClientInformationFull(
            client_id=client_id,
            client_secret=client_secret or None,
            redirect_uris=[AnyUrl("https://claude.ai/api/mcp/auth_callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none" if not client_secret else "client_secret_post",
        )

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self.clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        code = secrets.token_urlsafe(32)
        self.auth_codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + 300,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self.auth_codes.get(authorization_code)
        if code and code.client_id == client.client_id:
            return code
        return None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        del self.auth_codes[authorization_code.code]
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        self.access_tokens[access_token] = AccessToken(
            token=access_token, client_id=client.client_id, scopes=authorization_code.scopes, expires_at=None
        )
        self.refresh_tokens[refresh_token] = RefreshToken(
            token=refresh_token, client_id=client.client_id, scopes=authorization_code.scopes
        )
        return OAuthToken(access_token=access_token, token_type="bearer", refresh_token=refresh_token)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        token = self.refresh_tokens.get(refresh_token)
        if token and token.client_id == client.client_id:
            return token
        return None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        del self.refresh_tokens[refresh_token.token]
        self.access_tokens = {k: v for k, v in self.access_tokens.items() if v.client_id != client.client_id}
        access_token = secrets.token_urlsafe(32)
        new_refresh_token = secrets.token_urlsafe(32)
        used_scopes = scopes or refresh_token.scopes
        self.access_tokens[access_token] = AccessToken(
            token=access_token, client_id=client.client_id, scopes=used_scopes, expires_at=None
        )
        self.refresh_tokens[new_refresh_token] = RefreshToken(
            token=new_refresh_token, client_id=client.client_id, scopes=used_scopes
        )
        return OAuthToken(access_token=access_token, token_type="bearer", refresh_token=new_refresh_token)

    async def load_access_token(self, token: str) -> AccessToken | None:
        return self.access_tokens.get(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self.access_tokens.pop(token.token, None)
        else:
            self.refresh_tokens.pop(token.token, None)


auth_provider = SimpleOAuthProvider()
auth_provider.preregister_client(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET)

mcp = FastMCP(
    "whatsapp",
    auth=AuthSettings(
        issuer_url=BASE_URL,
        resource_server_url=BASE_URL,
        client_registration_options=ClientRegistrationOptions(enabled=True),
    ),
    auth_server_provider=auth_provider,
)


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
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        import uvicorn
        port = int(os.environ.get("PORT", 10000))
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        mcp.run()
