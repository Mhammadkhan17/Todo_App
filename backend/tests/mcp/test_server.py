import os

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlmodel import Session

from src.models.task import Priority, Task
from src.services.task_service import TaskService
from tests.helpers import create_user
from tests.mcp.conftest import mcp_user as _mcp_user
from tests.mcp.conftest import payload as _payload


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
        TaskService.set_completed(
            session, user_id=user.id, task_id=done.id, completed=True
        )

    result = await mcp_server.call_tool("todo_summary", {})
    payload = _payload(result)

    assert result.is_error is False
    assert payload["total"] == 2
    assert payload["active"] == 1
    assert payload["completed"] == 1


@pytest.mark.asyncio
async def test_create_update_complete_reopen(mcp_server, test_db):
    created = await mcp_server.call_tool(
        "todo_create_task",
        {"title": "Buy milk", "priority": "high"},
    )
    task = _payload(created)
    assert created.is_error is False
    assert task["priority"] == "HIGH"

    # created for the MCP_USER_ID identity, not a hardcoded user
    with Session(test_db) as session:
        stored = session.get(Task, task["id"])
        assert stored is not None
        assert stored.user_id == int(os.environ["MCP_USER_ID"])

    updated = await mcp_server.call_tool(
        "todo_update_task",
        {"task_id": task["id"], "title": "Buy oat milk"},
    )
    assert _payload(updated)["title"] == "Buy oat milk"

    completed = await mcp_server.call_tool(
        "todo_complete_task",
        {"task_id": task["id"]},
    )
    assert _payload(completed)["status"] == "COMPLETED"

    # idempotent: completing again succeeds and keeps the same state
    completed_again = await mcp_server.call_tool(
        "todo_complete_task",
        {"task_id": task["id"]},
    )
    assert completed_again.is_error is False
    assert _payload(completed_again)["status"] == "COMPLETED"

    reopened = await mcp_server.call_tool(
        "todo_reopen_task",
        {"task_id": task["id"]},
    )
    assert _payload(reopened)["status"] == "ACTIVE"

    reopened_again = await mcp_server.call_tool(
        "todo_reopen_task",
        {"task_id": task["id"]},
    )
    assert reopened_again.is_error is False
    assert _payload(reopened_again)["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_delete_task_is_permanent(mcp_server):
    created = await mcp_server.call_tool(
        "todo_create_task",
        {"title": "Temporary"},
    )
    task_id = _payload(created)["id"]

    deleted = await mcp_server.call_tool(
        "todo_delete_task",
        {"task_id": task_id},
    )
    assert deleted.is_error is False

    # call_tool raises ToolError on failure in SDK 2.x instead of
    # returning a CallToolResult with is_error=True.
    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool("todo_get_task", {"task_id": task_id})


@pytest.mark.asyncio
async def test_unknown_task_returns_actionable_error(mcp_server):
    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool("todo_get_task", {"task_id": 999999})


@pytest.mark.asyncio
async def test_cross_user_task_returns_error(mcp_server, test_db):
    with Session(test_db) as session:
        other = create_user(session)
        other_task = TaskService.create(session, user_id=other.id, title="Not yours")

    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool("todo_get_task", {"task_id": other_task.id})

    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool(
            "todo_update_task",
            {"task_id": other_task.id, "title": "Hijacked"},
        )

    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool("todo_delete_task", {"task_id": other_task.id})


@pytest.mark.asyncio
async def test_delete_task_is_annotated_destructive(mcp_server):
    tools = await mcp_server.list_tools()
    delete = next(t for t in tools if t.name == "todo_delete_task")
    assert delete.annotations is not None
    assert delete.annotations.destructive_hint is True

    read_only = next(t for t in tools if t.name == "todo_list_tasks")
    assert read_only.annotations is not None
    assert read_only.annotations.read_only_hint is True
