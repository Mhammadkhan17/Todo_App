"""Streamable HTTP transport for the TodoFlow MCP server (Phase 2.1).

Run it as a separate ASGI process next to the REST API:

    python -m src.mcp.http

Clients must present a JWT access token issued by the REST API
(`POST /api/auth/login`). Identity comes from the verified token's
subject claim — never from MCP_USER_ID, request headers, or tool
arguments.

Configuration (environment variables):

    MCP_HTTP_ISSUER_URL    OAuth issuer (the REST API base URL)
                           default: http://127.0.0.1:8000
    MCP_HTTP_RESOURCE_URL  This MCP server's public URL (RFC 8707 resource)
                           default: http://127.0.0.1:8001/mcp
    MCP_HTTP_HOST          Bind host, default 127.0.0.1
    MCP_HTTP_PORT          Bind port, default 8001
"""

import os

import uvicorn
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

from src.auth.jwt_service import JWTService
from src.exceptions.custom_exceptions import AuthenticationException
from src.mcp.server import SessionFactory, create_server


class JWTTokenVerifier(TokenVerifier):
    """Verify REST-issued JWT access tokens for MCP HTTP requests."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            data = JWTService.verify_access_token(token)
        except AuthenticationException:
            return None
        return AccessToken(
            token=token,
            client_id="todoflow",
            scopes=["todo"],
            subject=str(data.user_id),
        )


def create_http_server(
    session_factory: SessionFactory | None = None,
) -> MCPServer:
    issuer_url = os.getenv("MCP_HTTP_ISSUER_URL", "http://127.0.0.1:8000")
    resource_url = os.getenv("MCP_HTTP_RESOURCE_URL", "http://127.0.0.1:8001/mcp")
    return create_server(
        session_factory,
        token_verifier=JWTTokenVerifier(),
        auth=AuthSettings(
            issuer_url=issuer_url,
            resource_server_url=resource_url,
            # This verifier only accepts tokens signed with our own secret;
            # they carry no RFC 8707 resource claim to compare, and the SDK
            # will otherwise default to rejecting them in 3.0.
            validate_token_resource=False,
        ),
    )


def streamable_http_app(
    session_factory: SessionFactory | None = None,
):
    """Build the authenticated Streamable HTTP ASGI application."""
    return create_http_server(session_factory).streamable_http_app()


def main() -> None:
    # On HTTP, identity must come from the bearer token. A leftover stdio
    # MCP_USER_ID would pin every caller to one user (a cross-user leak).
    os.environ.pop("MCP_USER_ID", None)
    host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_HTTP_PORT", "8001"))
    uvicorn.run(streamable_http_app(), host=host, port=port)


if __name__ == "__main__":
    main()
