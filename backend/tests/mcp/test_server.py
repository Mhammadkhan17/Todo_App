import json
import os
from contextlib import contextmanager

import pytest
from sqlmodel import Session

from src.mcp.server import create_server
from src.models.task import Priority, Status
from src.models.user import User
from src.services.task_service import TaskService
from tests.helpers import create_user


@pytest.fixture
def mcp_server(test_db, monkeypatch):
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


def _payload(result):
    return json.loads(result.content[0].text)


def _mcp_user(session: Session) -> User:
    return session.get(User, int(os.environ["MCP_USER_ID"]))


@pytest.mark.asyncio
async def test_list_tasks_is_scoped_to_identity(mcp_server, test_db):
    with Session(test_db) as session:
        user = _mcp_user(session)
        TaskService.create(session, user_id=user.id, title="Buy milk")

    result = await mcp_server.call_tool("todo_list_tasks", {})
    payload = _payload(result)

    assert result.is_error is False
    assert payload["total"] == 1
    assert payload["tasks"][0]["title"] == "Buy milk"


@pytest.mark.asyncio
async def test_get_task_returns_full_task(mcp_server, test_db):
    with Session(test_db) as session:
        user = _mcp_user(session)
        task = TaskService.create(
            session,
            user_id=user.id,
            title="Write report",
            priority=Priority.HIGH,
        )
        task_id = task.id

    result = await mcp_server.call_tool("todo_get_task", {"task_id": task_id})
    payload = _payload(result)

    assert result.is_error is False
    assert payload["id"] == task_id
    assert payload["title"] == "Write report"
    assert payload["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_summary_counts(mcp_server, test_db):
    with Session(test_db) as session:
        user = _mcp_user(session)
        TaskService.create(session, user_id=user.id, title="One")
        done = TaskService.create(session, user_id=user.id, title="Two")
        TaskService.set_completed(session, user_id=user.id, task_id=done.id, completed=True)

    result = await mcp_server.call_tool("todo_summary", {})
    payload = _payload(result)

    assert result.is_error is False
    assert payload["total"] == 2
    assert payload["active"] == 1
    assert payload["completed"] == 1
