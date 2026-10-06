"""
Todo Agent Implementation for Phase 3 using Model Context Protocol (MCP)
Follows the specification from Hackathon II document for AI-powered todo chatbot.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import httpx
import asyncio
from sqlmodel import select
from ..models.task import Task, Status as TaskStatus, Priority as TaskPriority
from ..models.user import User
from ..database.engine import database_engine


class AddTaskParams(BaseModel):
    user_id: str = Field(description="User ID")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(None, description="Task description")


def add_task(params: AddTaskParams) -> Dict[str, Any]:
    """
    Create a new task with title and optional description
    """
    try:
        with database_engine.get_session() as db:
            # Verify user exists
            user = db.exec(select(User).where(User.id == int(params.user_id))).first()
            if not user:
                return {"error": "User not found", "status": "failed"}

            # Create new task
            task = Task(
                title=params.title,
                description=params.description,
                user_id=int(params.user_id)
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            return {
                "task_id": task.id,
                "status": "created",
                "title": task.title,
                "user_id": params.user_id
            }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


class ListTasksParams(BaseModel):
    user_id: str = Field(description="User ID")
    status: Optional[str] = Field(None, description="Filter by status: 'all', 'pending', 'completed'")


def list_tasks(params: ListTasksParams) -> List[Dict[str, Any]]:
    """
    Retrieve tasks from the list with optional status filter
    """
    try:
        with database_engine.get_session() as db:
            # Verify user exists
            user = db.exec(select(User).where(User.id == int(params.user_id))).first()
            if not user:
                return [{"error": "User not found"}]

            # Build query
            query = select(Task).where(Task.user_id == int(params.user_id))

            if params.status:
                if params.status.lower() == "completed":
                    query = query.where(Task.status == TaskStatus.COMPLETED)
                elif params.status.lower() == "pending":
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


class CompleteTaskParams(BaseModel):
    user_id: str = Field(description="User ID")
    task_id: int = Field(description="Task ID to mark as complete")


def complete_task(params: CompleteTaskParams) -> Dict[str, Any]:
    """
    Mark a task as complete by task_id
    """
    try:
        with database_engine.get_session() as db:
            # Verify user exists
            user = db.exec(select(User).where(User.id == int(params.user_id))).first()
            if not user:
                return {"error": "User not found", "status": "failed"}

            # Find task and verify it belongs to the user
            task = db.exec(
                select(Task).where(Task.id == params.task_id).where(Task.user_id == int(params.user_id))
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


class DeleteTaskParams(BaseModel):
    user_id: str = Field(description="User ID")
    task_id: int = Field(description="Task ID to delete")


def delete_task(params: DeleteTaskParams) -> Dict[str, Any]:
    """
    Remove a task from the list by task_id
    """
    try:
        with database_engine.get_session() as db:
            # Verify user exists
            user = db.exec(select(User).where(User.id == int(params.user_id))).first()
            if not user:
                return {"error": "User not found", "status": "failed"}

            # Find task and verify it belongs to the user
            task = db.exec(
                select(Task).where(Task.id == params.task_id).where(Task.user_id == int(params.user_id))
            ).first()

            if not task:
                return {"error": "Task not found or doesn't belong to user", "status": "failed"}

            # Delete the task
            db.delete(task)
            db.commit()

            return {
                "task_id": params.task_id,
                "status": "deleted",
                "title": task.title
            }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


class UpdateTaskParams(BaseModel):
    user_id: str = Field(description="User ID")
    task_id: int = Field(description="Task ID to update")
    title: Optional[str] = Field(None, description="New task title")
    description: Optional[str] = Field(None, description="New task description")


def update_task(params: UpdateTaskParams) -> Dict[str, Any]:
    """
    Modify task title or description by task_id
    """
    try:
        with database_engine.get_session() as db:
            # Verify user exists
            user = db.exec(select(User).where(User.id == int(params.user_id))).first()
            if not user:
                return {"error": "User not found", "status": "failed"}

            # Find task and verify it belongs to the user
            task = db.exec(
                select(Task).where(Task.id == params.task_id).where(Task.user_id == int(params.user_id))
            ).first()

            if not task:
                return {"error": "Task not found or doesn't belong to user", "status": "failed"}

            # Update fields if provided
            if params.title is not None:
                task.title = params.title
            if params.description is not None:
                task.description = params.description

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


def get_todo_tools():
    """
    Return all todo management tools for the agent.
    """
    return [
        add_task,
        list_tasks,
        complete_task,
        delete_task,
        update_task
    ]


def get_todo_agent(openai_api_key: Optional[str] = None):
    """
    Create and return an agent with the todo management tools that integrates with MCP.

    Args:
        openai_api_key: Optional OpenAI API key. If not provided, expects it in environment.

    Returns:
        Agent configured for todo management with MCP integration
    """
    # For MCP integration, we'll use the tools directly rather than OpenAI's function_tool
    # The actual MCP server is in the mcp/todo_mcp_server.py file
    tools = get_todo_tools()

    # Agent instructions for the LLM
    instructions = """
    You are a helpful assistant for managing todo lists.
    You can add, list, complete, update, and delete tasks.
    Use the appropriate tools based on the user's request.
    Always respond in a helpful, friendly manner.
    """

    return {
        "name": "Todo Assistant",
        "instructions": instructions,
        "tools": tools
    }


def process_natural_language_command(user_id: str, command: str, openai_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a natural language command using MCP-integrated tools.

    Args:
        user_id: ID of the user issuing the command
        command: Natural language command to process
        openai_api_key: Optional OpenAI API key

    Returns:
        Dictionary with the result of processing the command
    """
    # This function can be called by the API layer to process commands
    # In a real MCP setup, the LLM would call the MCP server directly
    # For this implementation, we'll simulate the processing

    # The actual MCP server is available at mcp/todo_mcp_server.py
    # This function would typically make a call to that server

    # For now, we'll return a placeholder response that indicates
    # the command would be processed by the MCP server
    return {
        "status": "mcp_integration_ready",
        "message": f"Command '{command}' would be processed by MCP server with user_id {user_id}",
        "mcp_server": "available_at_/mcp/todo_mcp_server.py"
    }


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a specific MCP tool by name with given arguments.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Arguments to pass to the tool

    Returns:
        Result of the tool call
    """
    # Get the appropriate tool function
    tools_map = {
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "update_task": update_task
    }

    if tool_name not in tools_map:
        return {"error": f"Unknown tool: {tool_name}", "status": "failed"}

    tool_func = tools_map[tool_name]

    # Create the appropriate parameter model based on the tool
    try:
        if tool_name == "add_task":
            params = AddTaskParams(**arguments)
            return tool_func(params)
        elif tool_name == "list_tasks":
            params = ListTasksParams(**arguments)
            return tool_func(params)
        elif tool_name == "complete_task":
            params = CompleteTaskParams(**arguments)
            return tool_func(params)
        elif tool_name == "delete_task":
            params = DeleteTaskParams(**arguments)
            return tool_func(params)
        elif tool_name == "update_task":
            params = UpdateTaskParams(**arguments)
            return tool_func(params)
        else:
            return {"error": f"Unknown tool: {tool_name}", "status": "failed"}
    except Exception as e:
        return {"error": f"Error calling tool {tool_name}: {str(e)}", "status": "failed"}