from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Literal

from dotenv import load_dotenv

load_dotenv()

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from sqlmodel import Session, select

from src.database.engine import database_engine
from src.exceptions.custom_exceptions import TodoException
from src.mcp.identity import resolve_user_id
from src.models.rag import Document
from src.models.task import Priority, Status
from src.services.task_service import TaskService

if TYPE_CHECKING:
    from src.rag.chatbot import RAGChatbot

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
    rag: "RAGChatbot | None" = None,
) -> MCPServer:
    factory = session_factory or database_engine.get_session
    mcp = MCPServer(
        name="todoflow",
        title="TodoFlow",
        version="1.0.0",
        instructions=(
            "Manage the authenticated user's tasks and indexed documents. "
            "Every tool is already scoped to that user. Never ask for a user id."
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

    def read(action):
        """Run a read-only resource action, mapping domain errors to ResourceError."""
        try:
            with factory() as session:
                return action(session)
        except TodoException as exc:
            raise ResourceError(str(exc.detail)) from exc
        except (ToolError, ValueError) as exc:
            raise ResourceError(str(exc)) from exc

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

    # --- Resources (read-only) ------------------------------------------

    @mcp.resource(
        "todo://tasks/active",
        name="Active tasks",
        description="The signed-in user's tasks that are not completed yet.",
        mime_type="application/json",
    )
    def resource_active_tasks() -> list[dict]:
        def action(session: Session) -> list[dict]:
            tasks, _ = TaskService.list(
                session,
                user_id=resolve_user_id(),
                status=Status.ACTIVE,
                size=200,
            )
            return [TaskService.to_dict(task) for task in tasks]

        return read(action)

    @mcp.resource(
        "todo://tasks/completed",
        name="Completed tasks",
        description="The signed-in user's completed tasks.",
        mime_type="application/json",
    )
    def resource_completed_tasks() -> list[dict]:
        def action(session: Session) -> list[dict]:
            tasks, _ = TaskService.list(
                session,
                user_id=resolve_user_id(),
                status=Status.COMPLETED,
                size=200,
            )
            return [TaskService.to_dict(task) for task in tasks]

        return read(action)

    @mcp.resource(
        "todo://tasks/{task_id}",
        name="Task",
        description="A single task by id, scoped to the signed-in user.",
        mime_type="application/json",
    )
    def resource_task(task_id: int) -> dict:
        def action(session: Session) -> dict:
            task = TaskService.get(session, user_id=resolve_user_id(), task_id=task_id)
            return TaskService.to_dict(task)

        return read(action)

    # --- Prompts (read-only) --------------------------------------------

    def active_tasks(session: Session) -> list:
        tasks, _ = TaskService.list(
            session,
            user_id=resolve_user_id(),
            status=Status.ACTIVE,
            size=200,
        )
        return tasks

    @mcp.prompt(
        name="daily_review",
        description="Review today's active tasks with overdue work flagged.",
    )
    def prompt_daily_review() -> str:
        def action(session: Session) -> str:
            tasks = active_tasks(session)
            today = datetime.now(timezone.utc).date()
            lines = [f"Daily review: {len(tasks)} active task(s)."]
            overdue = 0
            for task in tasks:
                marker = ""
                if task.due_date and task.due_date < today:
                    overdue += 1
                    marker = " [OVERDUE]"
                due = f" (due {task.due_date})" if task.due_date else ""
                lines.append(f"- [{task.priority.value}] {task.title}{marker}{due}")
            if overdue:
                lines.append(f"{overdue} task(s) overdue.")
            return "\n".join(lines)

        return run(action)

    @mcp.prompt(
        name="prioritize_my_day",
        description="Rank the signed-in user's active tasks by priority.",
    )
    def prompt_prioritize_my_day() -> str:
        def action(session: Session) -> str:
            order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
            ranked = sorted(
                active_tasks(session), key=lambda t: order.get(t.priority, 3)
            )
            lines = ["Help me prioritize my day. Tackle these in order:"]
            for position, task in enumerate(ranked, start=1):
                lines.append(f"{position}. [{task.priority.value}] {task.title}")
            if not ranked:
                lines.append("No active tasks.")
            return "\n".join(lines)

        return run(action)

    @mcp.prompt(
        name="weekly_plan",
        description="Plan the week around active tasks and their due dates.",
    )
    def prompt_weekly_plan() -> str:
        def action(session: Session) -> str:
            tasks = sorted(
                active_tasks(session),
                key=lambda t: (t.due_date is None, t.due_date),
            )
            lines = [f"Weekly plan: {len(tasks)} active task(s)."]
            for task in tasks:
                due = f" (due {task.due_date})" if task.due_date else ""
                lines.append(f"- {task.title}{due}")
            return "\n".join(lines)

        return run(action)

    # --- RAG tools (read-only) ------------------------------------------

    def active_document_ids(session: Session, user_id: str) -> list[str]:
        """Same retrieval allow-list as /api/rag: this user's active documents."""
        rows = session.exec(
            select(Document.id)
            .where(Document.user_id == user_id)
            .where(Document.is_active.is_(True))
        ).all()
        return [str(row_id) for row_id in rows]

    def rag_bot():
        if rag is not None:
            return rag
        from src.rag.chatbot import RAGChatbot  # lazy: keeps stdio startup light

        return RAGChatbot()

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def todo_search_documents(query: str, limit: int = 5) -> dict:
        """Semantic search across the signed-in user's indexed documents."""

        def action(session: Session) -> dict:
            user_id = str(resolve_user_id())
            allowed = active_document_ids(session, user_id)
            try:
                results = rag_bot().search_similar(
                    query, user_id, k=limit, document_ids=allowed
                )
            except Exception as exc:
                raise ToolError(str(exc)) from exc
            return {"query": query, "results": results}

        return run(action)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    async def todo_ask_documents(question: str) -> dict:
        """Answer a question grounded only in the signed-in user's documents."""

        def action(session: Session) -> dict:
            user_id = str(resolve_user_id())
            allowed = active_document_ids(session, user_id)
            try:
                outcome = rag_bot().generate_response(
                    question, user_id, document_ids=allowed
                )
            except Exception as exc:
                raise ToolError(str(exc)) from exc
            return {
                "response": outcome["response"],
                "sources": outcome.get("sources", []),
            }

        return run(action)

    return mcp


def main() -> None:
    mcp = create_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
