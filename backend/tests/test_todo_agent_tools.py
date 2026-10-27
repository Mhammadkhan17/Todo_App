"""
Tests for the chatbot's todo tool adapters (src/agents/todo_agent.py).

The five chat tools must run through the shared TaskService, and
call_mcp_tool("update_task", ...) must persist changes without errors.
"""

from contextlib import contextmanager

import pytest
from sqlmodel import Session

from src.agents.todo_agent import call_mcp_tool, get_todo_tools
from src.models.task import Task
from src.services.task_service import TaskService
from tests.helpers import create_user


def test_five_chat_tools_registered():
    tools = get_todo_tools()
    assert len(tools) == 5
    assert {f.__name__ for f in tools} == {
        "add_task",
        "list_tasks",
        "complete_task",
        "delete_task",
        "update_task",
    }


@pytest.fixture
def chat_db(test_db, monkeypatch):
    """Wire todo_agent's database_engine.get_session to the shared test DB."""

    @contextmanager
    def _session():
        session = Session(bind=test_db)
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(
        "src.agents.todo_agent.database_engine.get_session", _session
    )
    return test_db


def test_add_list_update_complete_delete_via_taskservice(chat_db):
    with Session(chat_db) as session:
        user = create_user(session)
    uid = str(user.id)

    created = call_mcp_tool("add_task", {"user_id": uid, "title": "Original"})
    assert created["status"] == "created"
    task_id = created["task_id"]

    updated = call_mcp_tool(
        "update_task",
        {"user_id": uid, "task_id": task_id, "title": "Renamed"},
    )
    assert updated["status"] == "updated"
    assert updated["title"] == "Renamed"

    with Session(chat_db) as session:
        stored = TaskService.get(session, user_id=user.id, task_id=task_id)
        assert stored.title == "Renamed"
        assert stored.user_id == user.id

    completed = call_mcp_tool(
        "complete_task", {"user_id": uid, "task_id": task_id}
    )
    assert completed["status"] == "completed"

    listed = call_mcp_tool("list_tasks", {"user_id": uid, "status": "completed"})
    assert isinstance(listed, list)
    assert listed[0]["title"] == "Renamed"

    deleted = call_mcp_tool("delete_task", {"user_id": uid, "task_id": task_id})
    assert deleted["status"] == "deleted"

    # hard delete: the row is gone
    with Session(chat_db) as session:
        assert session.get(Task, task_id) is None


def test_update_task_cross_user_returns_error_dict(chat_db):
    with Session(chat_db) as session:
        owner = create_user(session)
        stranger = create_user(session)
        task = TaskService.create(session, user_id=owner.id, title="Mine")
        stranger_id = stranger.id
        task_id = task.id

    result = call_mcp_tool(
        "update_task",
        {
            "user_id": str(stranger_id),
            "task_id": task_id,
            "title": "Hijacked",
        },
    )
    assert result["status"] == "failed"
    assert "not found" in result["error"]


def test_unknown_tool_returns_error_dict():
    result = call_mcp_tool("no_such_tool", {})
    assert result["status"] == "failed"
    assert "Unknown tool" in result["error"]
