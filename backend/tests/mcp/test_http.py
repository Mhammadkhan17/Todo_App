"""
Phase 2.1: Streamable HTTP transport with per-user JWT identity.

The HTTP app requires a REST-issued bearer token. Identity comes from the
verified token subject — never from MCP_USER_ID, headers, or tool arguments.
"""

import json
from contextlib import contextmanager
from datetime import timedelta

import httpx2
import pytest
from mcp.client.streamable_http import streamable_http_client
from sqlmodel import Session

from mcp import Client
from src.auth.jwt_service import JWTService
from src.mcp.http import JWTTokenVerifier, streamable_http_app
from src.models.task import Task
from src.services.task_service import TaskService
from tests.helpers import create_user

MCP_URL = "http://127.0.0.1:8001/mcp"
TEST_BASE = "http://127.0.0.1:8001"


def _mint_token(user_id: int, username: str, *, expired: bool = False) -> str:
    expires = timedelta(seconds=-30) if expired else None
    return JWTService.create_access_token(
        {"sub": username, "user_id": user_id}, expires_delta=expires
    )["access_token"]


@pytest.fixture
def http_app(test_db, monkeypatch):
    # On HTTP, identity must come from the bearer token; the stdio dev
    # variable would otherwise pin every caller to a single user.
    monkeypatch.delenv("MCP_USER_ID", raising=False)

    @contextmanager
    def session_factory():
        with Session(bind=test_db) as session:
            yield session

    return streamable_http_app(session_factory)


def _transport(app, token: str):
    http = httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app),
        headers={"Authorization": f"Bearer {token}"},
        base_url=TEST_BASE,
    )
    return streamable_http_client(MCP_URL, http_client=http)


def _payload(result) -> dict:
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_verifier_accepts_valid_token():
    token = _mint_token(42, "alice")

    access = await JWTTokenVerifier().verify_token(token)

    assert access is not None
    assert access.subject == "42"
    assert access.client_id == "todoflow"
    assert access.scopes == ["todo"]


@pytest.mark.asyncio
async def test_verifier_rejects_expired_and_invalid_tokens():
    expired = _mint_token(42, "alice", expired=True)

    assert await JWTTokenVerifier().verify_token(expired) is None
    assert await JWTTokenVerifier().verify_token("not-a-jwt") is None


@pytest.mark.asyncio
async def test_http_endpoint_rejects_missing_expired_and_invalid_tokens(http_app):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    expired = _mint_token(42, "alice", expired=True)

    # The lifespan must open and close inside this test's task: the
    # session manager's anyio cancel scope cannot span fixture tasks.
    async with (
        http_app.router.lifespan_context(http_app),
        httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=http_app), base_url=TEST_BASE
        ) as raw,
    ):
        missing = await raw.post("/mcp", json=payload)
        invalid = await raw.post(
            "/mcp", json=payload, headers={"Authorization": "Bearer garbage"}
        )
        stale = await raw.post(
            "/mcp", json=payload, headers={"Authorization": f"Bearer {expired}"}
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert stale.status_code == 401


@pytest.mark.asyncio
async def test_http_tools_scope_to_token_subject(http_app, test_db):
    with Session(test_db) as session:
        alice = create_user(session)
        bob = create_user(session)
        TaskService.create(session, user_id=alice.id, title="Alice task")
        TaskService.create(session, user_id=bob.id, title="Bob task")
        alice_id, alice_name = alice.id, alice.username
        bob_id, bob_name = bob.id, bob.username

    async with http_app.router.lifespan_context(http_app):
        # Alice's token only ever sees Alice's tasks
        async with Client(
            _transport(http_app, _mint_token(alice_id, alice_name))
        ) as alice_client:
            result = await alice_client.call_tool("todo_list_tasks", {})
            assert [t["title"] for t in _payload(result)["tasks"]] == ["Alice task"]

            tools = await alice_client.list_tools()
            assert len(tools.tools) == 8
            schemas = json.dumps(
                [t.model_dump(mode="json", by_alias=True) for t in tools.tools]
            )
            assert "user_id" not in schemas

        # Bob's token sees only his tasks; his new task binds to his subject
        async with Client(
            _transport(http_app, _mint_token(bob_id, bob_name))
        ) as bob_client:
            result = await bob_client.call_tool("todo_list_tasks", {})
            assert [t["title"] for t in _payload(result)["tasks"]] == ["Bob task"]

            created = await bob_client.call_tool(
                "todo_create_task", {"title": "Bob new task"}
            )
            created_id = _payload(created)["id"]

    with Session(test_db) as session:
        stored = session.get(Task, created_id)
        assert stored is not None
        assert stored.user_id == bob_id
