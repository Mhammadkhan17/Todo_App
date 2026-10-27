"""Shared fixtures and helpers for MCP server tests."""

import json
import os
from contextlib import contextmanager

import pytest
from sqlmodel import Session

from src.mcp.server import create_server
from src.models.user import User


@pytest.fixture
def mcp_server(test_db, monkeypatch):
    from tests.helpers import create_user

    with Session(test_db) as setup:
        user = create_user(setup)
        user_id = user.id

    monkeypatch.setenv("MCP_USER_ID", str(user_id))

    @contextmanager
    def session_factory():
        session = Session(bind=test_db)
        try:
            yield session
        finally:
            session.close()

    return create_server(session_factory)


def payload(result):
    return json.loads(result.content[0].text)


def mcp_user(session: Session) -> User:
    return session.get(User, int(os.environ["MCP_USER_ID"]))
