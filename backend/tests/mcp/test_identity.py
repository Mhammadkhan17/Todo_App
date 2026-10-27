import pytest
from mcp.server.auth.provider import AccessToken
from mcp.server.mcpserver.exceptions import ToolError

from src.mcp import identity


def test_reads_user_id_from_environment(monkeypatch):
    monkeypatch.setenv("MCP_USER_ID", "42")
    assert identity.resolve_user_id() == 42


def test_rejects_missing_identity(monkeypatch):
    monkeypatch.delenv("MCP_USER_ID", raising=False)
    monkeypatch.setattr(identity, "get_access_token", lambda: None)
    with pytest.raises(ToolError, match="No MCP user identity"):
        identity.resolve_user_id()


def test_rejects_non_integer_environment(monkeypatch):
    monkeypatch.setenv("MCP_USER_ID", "abc")
    with pytest.raises(ToolError, match="MCP_USER_ID must be an integer"):
        identity.resolve_user_id()


def test_reads_subject_from_verified_token(monkeypatch):
    monkeypatch.delenv("MCP_USER_ID", raising=False)
    token = AccessToken(
        token="verified",
        client_id="todoflow",
        scopes=["todo"],
        subject="7",
    )
    monkeypatch.setattr(identity, "get_access_token", lambda: token)
    assert identity.resolve_user_id() == 7
