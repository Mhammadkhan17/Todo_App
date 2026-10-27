from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
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


def create_server(
    session_factory: SessionFactory | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    auth: AuthSettings | None = None,
) -> MCPServer:
    factory = session_factory or database_engine.get_session
    mcp = MCPServer(
        name="todoflow",
        title="TodoFlow",
        version="1.0.0",
        instructions=(
            "Manage the authenticated user's tasks. Every tool is already scoped "
            "to that user. Never ask for a user id."
        ),
        token_verifier=token_verifier,
        auth=auth,
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

    @mcp.tool()
    async def todo_create_task(
        title: str,
        description: str | None = None,
        priority: Literal["high", "medium", "low"] | None = None,
        due_date: date | None = None,
    ) -> dict:
        """Create a task for the authenticated user."""

        def action(session: Session) -> dict:
            task = TaskService.create(
                session,
                user_id=resolve_user_id(),
                title=title,
                description=description,
                priority=_priority(priority) or Priority.MEDIUM,
                due_date=due_date,
            )
            return TaskService.to_dict(task)

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(idempotent_hint=True))
    async def todo_update_task(
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        priority: Literal["high", "medium", "low"] | None = None,
        due_date: date | None = None,
    ) -> dict:
        """Update selected fields on a task."""

        def action(session: Session) -> dict:
            changes = {}
            if title is not None:
                changes["title"] = title
            if description is not None:
                changes["description"] = description
            if priority is not None:
                changes["priority"] = _priority(priority)
            if due_date is not None:
                changes["due_date"] = due_date

            task = TaskService.update(
                session,
                user_id=resolve_user_id(),
                task_id=task_id,
                changes=changes,
            )
            return TaskService.to_dict(task)

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(idempotent_hint=True))
    async def todo_complete_task(task_id: int) -> dict:
        """Mark a task completed. Safe to call more than once."""

        def action(session: Session) -> dict:
            task = TaskService.set_completed(
                session,
                user_id=resolve_user_id(),
                task_id=task_id,
                completed=True,
            )
            return TaskService.to_dict(task)

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(idempotent_hint=True))
    async def todo_reopen_task(task_id: int) -> dict:
        """Mark a completed task active again. Safe to call more than once."""

        def action(session: Session) -> dict:
            task = TaskService.set_completed(
                session,
                user_id=resolve_user_id(),
                task_id=task_id,
                completed=False,
            )
            return TaskService.to_dict(task)

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(destructive_hint=True))
    async def todo_delete_task(task_id: int) -> dict:
        """Permanently delete a task. This cannot be undone."""

        def action(session: Session) -> dict:
            TaskService.delete(
                session,
                user_id=resolve_user_id(),
                task_id=task_id,
            )
            return {"task_id": task_id, "status": "deleted"}

        return run(action)

    return mcp


def main() -> None:
    mcp = create_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
