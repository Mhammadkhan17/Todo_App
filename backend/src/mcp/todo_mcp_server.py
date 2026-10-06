"""
Model Context Protocol (MCP) Server for Todo Management Tools
Implements the Model Context Protocol to expose todo management tools to LLMs.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
    ToolExecution,
    TASK_OPTIONAL
)
from sqlmodel import select

from ..models.task import Task, Status as TaskStatus
from ..models.user import User
from ..database.engine import database_engine


class TodoMCPService:
    """Service class to handle todo operations for MCP server."""

    def __init__(self):
        self.db_engine = database_engine

    def add_task(self, user_id: str, title: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new task with title and optional description."""
        try:
            with self.db_engine.get_session() as db:
                # Verify user exists
                user = db.exec(select(User).where(User.id == int(user_id))).first()
                if not user:
                    return {"error": "User not found", "status": "failed"}

                # Create new task
                task = Task(
                    title=title,
                    description=description,
                    user_id=int(user_id)
                )
                db.add(task)
                db.commit()
                db.refresh(task)

                return {
                    "task_id": task.id,
                    "status": "created",
                    "title": task.title,
                    "user_id": user_id
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def list_tasks(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve tasks from the list with optional status filter."""
        try:
            with self.db_engine.get_session() as db:
                # Verify user exists
                user = db.exec(select(User).where(User.id == int(user_id))).first()
                if not user:
                    return [{"error": "User not found"}]

                # Build query
                query = select(Task).where(Task.user_id == int(user_id))

                if status:
                    if status.lower() == "completed":
                        query = query.where(Task.status == TaskStatus.COMPLETED)
                    elif status.lower() == "pending":
                        query = query.where(Task.status == TaskStatus.ACTIVE)

                tasks = db.exec(query.order_by(Task.created_at.desc())).all()

                return [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value,
                        "priority": task.priority.value,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "created_at": task.created_at.isoformat()
                    }
                    for task in tasks
                ]
        except Exception as e:
            return [{"error": str(e)}]

    def complete_task(self, user_id: str, task_id: int) -> Dict[str, Any]:
        """Mark a task as complete by task_id."""
        try:
            with self.db_engine.get_session() as db:
                # Verify user exists
                user = db.exec(select(User).where(User.id == int(user_id))).first()
                if not user:
                    return {"error": "User not found", "status": "failed"}

                # Find task and verify it belongs to the user
                task = db.exec(
                    select(Task).where(Task.id == task_id).where(Task.user_id == int(user_id))
                ).first()

                if not task:
                    return {"error": "Task not found or doesn't belong to user", "status": "failed"}

                # Mark as complete
                task.toggle_completion()
                db.add(task)
                db.commit()
                db.refresh(task)

                return {
                    "task_id": task.id,
                    "status": "completed",
                    "title": task.title,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def delete_task(self, user_id: str, task_id: int) -> Dict[str, Any]:
        """Remove a task from the list by task_id."""
        try:
            with self.db_engine.get_session() as db:
                # Verify user exists
                user = db.exec(select(User).where(User.id == int(user_id))).first()
                if not user:
                    return {"error": "User not found", "status": "failed"}

                # Find task and verify it belongs to the user
                task = db.exec(
                    select(Task).where(Task.id == task_id).where(Task.user_id == int(user_id))
                ).first()

                if not task:
                    return {"error": "Task not found or doesn't belong to user", "status": "failed"}

                # Delete the task
                db.delete(task)
                db.commit()

                return {
                    "task_id": task_id,
                    "status": "deleted",
                    "title": task.title
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def update_task(self, user_id: str, task_id: int, title: Optional[str] = None,
                   description: Optional[str] = None) -> Dict[str, Any]:
        """Modify task title or description by task_id."""
        try:
            with self.db_engine.get_session() as db:
                # Verify user exists
                user = db.exec(select(User).where(User.id == int(user_id))).first()
                if not user:
                    return {"error": "User not found", "status": "failed"}

                # Find task and verify it belongs to the user
                task = db.exec(
                    select(Task).where(Task.id == task_id).where(Task.user_id == int(user_id))
                ).first()

                if not task:
                    return {"error": "Task not found or doesn't belong to user", "status": "failed"}

                # Update fields if provided
                if title is not None:
                    task.title = title
                if description is not None:
                    task.description = description

                task.updated_at = task.__class__.updated_at.field.default_factory()
                db.add(task)
                db.commit()
                db.refresh(task)

                return {
                    "task_id": task.id,
                    "status": "updated",
                    "title": task.title
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}


@asynccontextmanager
async def server_lifespan(_server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize resources on startup
    service = TodoMCPService()
    try:
        yield {"service": service}
    finally:
        # Cleanup on shutdown if needed
        pass


# Initialize the MCP server
server = Server("todo-mcp-server", lifespan=server_lifespan)


@server.list_tools()
async def list_todo_tools() -> List[Tool]:
    """List all available todo management tools."""
    return [
        Tool(
            name="add_task",
            description="Create a new task with title and optional description",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description (optional)"}
                },
                "required": ["user_id", "title"]
            },
            execution=ToolExecution(taskSupport=TASK_OPTIONAL)
        ),
        Tool(
            name="list_tasks",
            description="Retrieve tasks from the list with optional status filter",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "status": {"type": "string", "description": "Filter by status: 'all', 'pending', 'completed' (optional)"}
                },
                "required": ["user_id"]
            },
            execution=ToolExecution(taskSupport=TASK_OPTIONAL)
        ),
        Tool(
            name="complete_task",
            description="Mark a task as complete by task_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "task_id": {"type": "integer", "description": "Task ID to mark as complete"}
                },
                "required": ["user_id", "task_id"]
            },
            execution=ToolExecution(taskSupport=TASK_OPTIONAL)
        ),
        Tool(
            name="delete_task",
            description="Remove a task from the list by task_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "task_id": {"type": "integer", "description": "Task ID to delete"}
                },
                "required": ["user_id", "task_id"]
            },
            execution=ToolExecution(taskSupport=TASK_OPTIONAL)
        ),
        Tool(
            name="update_task",
            description="Modify task title or description by task_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "task_id": {"type": "integer", "description": "Task ID to update"},
                    "title": {"type": "string", "description": "New task title (optional)"},
                    "description": {"type": "string", "description": "New task description (optional)"}
                },
                "required": ["user_id", "task_id"]
            },
            execution=ToolExecution(taskSupport=TASK_OPTIONAL)
        )
    ]


@server.call_tool()
async def handle_todo_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle calls to todo management tools."""
    # Access the service from lifespan context
    ctx = server.request_context
    service = ctx.lifespan_context["service"]

    try:
        if name == "add_task":
            result = service.add_task(
                user_id=arguments["user_id"],
                title=arguments["title"],
                description=arguments.get("description")
            )
        elif name == "list_tasks":
            result = service.list_tasks(
                user_id=arguments["user_id"],
                status=arguments.get("status")
            )
        elif name == "complete_task":
            result = service.complete_task(
                user_id=arguments["user_id"],
                task_id=arguments["task_id"]
            )
        elif name == "delete_task":
            result = service.delete_task(
                user_id=arguments["user_id"],
                task_id=arguments["task_id"]
            )
        elif name == "update_task":
            result = service.update_task(
                user_id=arguments["user_id"],
                task_id=arguments["task_id"],
                title=arguments.get("title"),
                description=arguments.get("description")
            )
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}",
                isError=True
            )]

        # Convert result to text content
        import json
        result_text = json.dumps(result, indent=2, default=str)
        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing tool {name}: {str(e)}",
            isError=True
        )]


async def run_mcp_server():
    """Run the MCP server over stdio."""
    import mcp.server.stdio
    from mcp.server.models import NotificationOptions

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="todo-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())