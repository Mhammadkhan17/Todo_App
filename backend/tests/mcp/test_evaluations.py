"""
Phase 2.4: scripted evaluation suite.

Seeds a deterministic five-task database (documented in evaluations.xml) and
runs every evaluation question in that file through the MCP server with a
scripted Client — one tool call, one exact expected answer per case.
"""

import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pytest
from sqlmodel import Session

from mcp import Client
from src.models.task import Priority
from src.services.task_service import TaskService
from tests.mcp.conftest import mcp_user


def _load_cases() -> list[dict]:
    root = ET.parse(Path(__file__).with_name("evaluations.xml")).getroot()
    return [
        {
            "name": case.get("name"),
            "question": case.findtext("question"),
            "tool": case.find("call").get("tool"),
            "args": json.loads(case.findtext("call")),
            "path": case.find("expect").get("path"),
            "expected": case.findtext("expect"),
        }
        for case in root.findall("evaluation")
    ]


CASES = _load_cases()


def _extract(payload: dict, path: str):
    current = payload
    for part in path.split("."):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


@pytest.fixture
def eval_seed(mcp_server, test_db):
    """The five deterministic tasks from evaluations.xml, per test case."""
    with Session(test_db) as session:
        user_id = mcp_user(session).id
        TaskService.create(
            session,
            user_id=user_id,
            title="Pay electricity bill",
            priority=Priority.HIGH,
            due_date=date(2000, 1, 15),
        )
        TaskService.create(
            session,
            user_id=user_id,
            title="Buy groceries",
            priority=Priority.MEDIUM,
            due_date=date(2099, 12, 31),
        )
        TaskService.create(
            session,
            user_id=user_id,
            title="Call the dentist",
            priority=Priority.LOW,
        )
        passport = TaskService.create(
            session,
            user_id=user_id,
            title="Renew passport",
            priority=Priority.HIGH,
            due_date=date(2000, 1, 20),
        )
        plants = TaskService.create(session, user_id=user_id, title="Water the plants")
        TaskService.set_completed(
            session, user_id=user_id, task_id=passport.id, completed=True
        )
        TaskService.set_completed(
            session, user_id=user_id, task_id=plants.id, completed=True
        )


def _assert_case(case: dict, actual) -> None:
    assert str(actual) == case["expected"], (
        f"{case['id']} {case['name']}: {case['question']}\n"
        f"  path {case['path']} = {actual!r}, expected {case['expected']!r}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_evaluation(case, mcp_server, eval_seed):
    async with Client(mcp_server) as client:
        result = await client.call_tool(case["tool"], case["args"])

    assert result.is_error is False, f"{case['name']}: tool errored"
    payload = json.loads(result.content[0].text)
    _assert_case(case, _extract(payload, case["path"]))
