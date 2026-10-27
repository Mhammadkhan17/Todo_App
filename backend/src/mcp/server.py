from contextlib import AbstractContextManager
from datetime import date
from typing import Callable, Literal

from dotenv import load_dotenv

load_dotenv()

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from sqlmodel import Session

from src.database.engine import database_engine
from src.exceptions.custom_exceptions import TodoException
from src.mcp.identity import resolve_user_id
from src.models.task import Priority, Status
from src.services.task_service import TaskService


SessionFactory = Callable[[], AbstractContextManager[Session]]


def _status(value: str | None) -> Status | None:
    if value in (None, "all"):
        return None
    return Status.ACTIVE if value == "active" else Status.COMPLETED


def _priority(value: str | None) -> Priority | None:
    if value is None:
        return None
    return Priority(value.upper())


def create_server(session_factory: SessionFactory | None = None) -> MCPServer:
    factory = session_factory or database_engine.get_session
    mcp = MCPServer(
        name="todoflow",
        title="TodoFlow",
        version="1.0.0",
        instructions=(
            "Manage the authenticated user's tasks. Every tool is already scoped "
            "to that user. Never ask for a user id."
        ),
    )

    def run(action):
        try:
            with factory() as session:
                return action(session)
        except TodoException as exc:
            raise ToolError(str(exc.detail)) from exc
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def todo_list_tasks(
        status: Literal["active", "completed", "all"] | None = None,
        priority: Literal["high", "medium", "low"] | None = None,
        due_date_from: date | None = None,
        due_date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """List tasks with optional filters, search, and pagination."""

        def action(session: Session) -> dict:
            tasks, total = TaskService.list(
                session,
                user_id=resolve_user_id(),
                status=_status(status),
                priority=_priority(priority),
                due_date_from=due_date_from,
                due_date_to=due_date_to,
                search=search,
                page=page,
                size=size,
            )
            return {
                "tasks": [TaskService.to_dict(task) for task in tasks],
                "total": total,
                "page": page,
                "size": size,
            }

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def todo_get_task(task_id: int) -> dict:
        """Fetch one task by id."""

        def action(session: Session) -> dict:
            task = TaskService.get(
                session,
                user_id=resolve_user_id(),
                task_id=task_id,
            )
            return TaskService.to_dict(task)

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def todo_summary() -> dict:
        """Count total, active, completed, high-priority, and overdue tasks."""

        def action(session: Session) -> dict:
            return TaskService.summary(session, user_id=resolve_user_id())

        return run(action)

    return mcp
