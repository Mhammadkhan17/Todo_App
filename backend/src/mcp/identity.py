import os

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver.exceptions import ToolError


def resolve_user_id() -> int:
    """Resolve the authenticated user for an MCP request.

    stdio uses MCP_USER_ID. HTTP uses the subject of a verified bearer token.
    Tool callers must never supply a user id themselves.
    """
    raw = os.getenv("MCP_USER_ID")
    if raw is not None:
        try:
            return int(raw)
        except ValueError as exc:
            raise ToolError("MCP_USER_ID must be an integer") from exc

    token = get_access_token()
    subject = token.subject if token is not None else None
    if subject is not None:
        try:
            return int(subject)
        except ValueError as exc:
            raise ToolError(
                "Verified token subject must be an integer user id"
            ) from exc

    raise ToolError(
        "No MCP user identity. Set MCP_USER_ID for stdio, "
        "or connect with a verified bearer token for HTTP."
    )
