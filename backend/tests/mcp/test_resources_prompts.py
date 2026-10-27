"""
Phase 2.2: MCP resources and prompts.

Resources expose read-only task views (todo://tasks/...); prompts render
read-only summaries for chat. Both reuse TaskService and resolve the caller
from MCP identity — never from arguments.
"""

import json

import pytest
from mcp.shared.exceptions import MCPError
from sqlmodel import Session

from mcp import Client
from src.models.task import Priority
from src.services.task_service import TaskService
from tests.helpers import create_user
from tests.mcp.conftest import mcp_user


def _payload(result) -> dict:
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_resources_and_templates_are_listed(mcp_server):
    async with Client(mcp_server) as client:
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

    uris = {str(r.uri) for r in resources.resources}
    assert uris == {"todo://tasks/active", "todo://tasks/completed"}
    assert [t.uri_template for t in templates.resource_templates] == [
        "todo://tasks/{task_id}"
    ]


@pytest.mark.asyncio
async def test_read_active_and_completed_resources(mcp_server, test_db):
    with Session(test_db) as session:
        user = mcp_user(session)
        TaskService.create(session, user_id=user.id, title="Still open")
        done = TaskService.create(session, user_id=user.id, title="All done")
        TaskService.set_completed(
            session, user_id=user.id, task_id=done.id, completed=True
        )

    async with Client(mcp_server) as client:
        active = await client.read_resource("todo://tasks/active")
        completed = await client.read_resource("todo://tasks/completed")

    active_titles = [t["title"] for t in json.loads(active.contents[0].text)]
    completed_titles = [t["title"] for t in json.loads(completed.contents[0].text)]
    assert active_titles == ["Still open"]
    assert completed_titles == ["All done"]


@pytest.mark.asyncio
async def test_task_resource_is_scoped_to_identity(mcp_server, test_db):
    with Session(test_db) as session:
        user = mcp_user(session)
        own = TaskService.create(session, user_id=user.id, title="Mine")
        other = create_user(session)
        foreign = TaskService.create(
            session, user_id=other.id, title="Not mine", priority=Priority.HIGH
        )
        own_id, foreign_id = own.id, foreign.id

    async with Client(mcp_server) as client:
        result = await client.read_resource(f"todo://tasks/{own_id}")
        task = json.loads(result.contents[0].text)
        assert task["title"] == "Mine"

        with pytest.raises(MCPError, match="not found"):
            await client.read_resource(f"todo://tasks/{foreign_id}")


@pytest.mark.asyncio
async def test_prompts_are_listed(mcp_server):
    async with Client(mcp_server) as client:
        prompts = await client.list_prompts()

    assert {p.name for p in prompts.prompts} == {
        "daily_review",
        "prioritize_my_day",
        "weekly_plan",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt_name", ["daily_review", "prioritize_my_day", "weekly_plan"]
)
async def test_prompts_summarize_the_users_tasks(mcp_server, test_db, prompt_name):
    with Session(test_db) as session:
        user = mcp_user(session)
        TaskService.create(session, user_id=user.id, title="Buy milk")
        TaskService.create(
            session, user_id=user.id, title="Write report", priority=Priority.HIGH
        )

    async with Client(mcp_server) as client:
        result = await client.get_prompt(prompt_name)

    assert result.messages
    text = " ".join(m.content.text for m in result.messages)
    assert "Buy milk" in text
    assert "Write report" in text
    assert all(m.role == "user" for m in result.messages)
