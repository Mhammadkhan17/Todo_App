"""
Chat API Router for Todo Chatbot - Implements the stateless chat endpoint
Following the specification from Hackathon II document for Phase 3.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from sqlmodel import select
from ..models.user import User
from ..models.rag import ChatSession, ChatMessage
from ..database.engine import database_engine
from ..dependencies.auth import get_current_user
from ..agents.todo_agent import call_mcp_tool
import uuid
from datetime import datetime
import json
import openai
from dotenv import load_dotenv
from ..llm.provider import resolve_llm

load_dotenv()

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # If provided, continue existing conversation


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    tool_calls: Optional[List[Dict]] = []


def extract_todo_operations(message: str) -> List[Dict]:
    """
    Extract potential todo operations from a natural language message.
    This is a simple rule-based extractor that can be replaced with more sophisticated NLP.
    """
    import re

    operations = []

    # Patterns for different operations
    add_pattern = r"(add|create|make|new)\s+(?:a\s+)?(?:task|todo|to-do|item)\s+(?:to\s+)?(?:my\s+)?(.+?)(?:\s|$|\.|,)"
    list_pattern = r"(list|show|display|view|see|get)\s+(?:my\s+)?(?:tasks|todos|to-dos|items|list)"
    complete_pattern = r"(complete|finish|done|mark.*as.*done|check|tick)\s+(?:off\s+)?(?:task|todo|to-do)\s+(?:#|number\s+|#)?(\d+|\w+)"
    delete_pattern = r"(delete|remove|eliminate|cancel|trash)\s+(?:task|todo|to-do)\s+(?:#|number\s+|#)?(\d+|\w+)"

    message_lower = message.lower()

    # Add task detection
    add_match = re.search(add_pattern, message_lower)
    if add_match:
        task_desc = add_match.group(1).strip()
        operations.append({
            "operation": "add_task",
            "description": task_desc
        })

    # List tasks detection
    if re.search(list_pattern, message_lower):
        operations.append({
            "operation": "list_tasks"
        })

    # Complete task detection
    complete_match = re.search(complete_pattern, message_lower)
    if complete_match:
        task_ref = complete_match.group(1).strip()
        operations.append({
            "operation": "complete_task",
            "task_reference": task_ref
        })

    # Delete task detection
    delete_match = re.search(delete_pattern, message_lower)
    if delete_match:
        task_ref = delete_match.group(1).strip()
        operations.append({
            "operation": "delete_task",
            "task_reference": task_ref
        })

    return operations


async def process_with_openai_and_mcp(user_id: str, message: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
    """
    Process the natural language message using OpenAI or Gemini with MCP tool integration.
    Includes conversation history for context.
    """
    try:
        # Get AI configuration
        cfg = resolve_llm()
        ai_provider, api_key, model = cfg.provider, cfg.api_key, cfg.model

        if not api_key or api_key == "sk-dummy-key-for-development":
            # Return a mock response if using dummy API key
            return {
                "response": f"Chatbot is working! However, {ai_provider.upper()} API key is not configured. Please set a valid API key in environment variables.",
                "tool_calls": [],
                "results": []
            }

        # Initialize OpenAI-compatible client
        client = openai.OpenAI(api_key=api_key, base_url=cfg.base_url, default_headers=cfg.default_headers or None)

        # Prepare the tools for function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": "Create a new task with title and optional description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "title": {"type": "string", "description": "Task title"},
                            "description": {"type": "string", "description": "Task description (optional)"}
                        },
                        "required": ["user_id", "title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "Retrieve tasks from the list with optional status filter",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "status": {"type": "string", "description": "Filter by status: 'all', 'pending', 'completed' (optional)"}
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": "Mark a task as complete by task_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "task_id": {"type": "integer", "description": "Task ID to mark as complete"}
                        },
                        "required": ["user_id", "task_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": "Remove a task from the list by task_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "task_id": {"type": "integer", "description": "Task ID to delete"}
                        },
                        "required": ["user_id", "task_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_task",
                    "description": "Modify task title or description by task_id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "task_id": {"type": "integer", "description": "Task ID to update"},
                            "title": {"type": "string", "description": "New task title (optional)"},
                            "description": {"type": "string", "description": "New task description (optional)"}
                        },
                        "required": ["user_id", "task_id"]
                    }
                }
            }
        ]

        # Create the messages array with system prompt
        messages = [
            {
                "role": "system",
                "content": "You are a friendly and proactive Task Management Assistant for TodoFlow. "
                          "Your goal is to help users stay organized without overwhelming them with technical details. "
                          "\n\nCRITICAL BEHAVIOR:\n"
                          "1. If a user refers to a task by name/title (e.g., 'I finished the fish task'), DO NOT ask for an ID. "
                          "Instead, call `list_tasks` first to find the ID yourself, then proceed with the action.\n"
                          "2. You can call multiple tools in a single turn if the user has multiple requests.\n"
                          "3. When listing tasks:\n"
                          "   - Group them by status (e.g., 'Active', 'Completed').\n"
                          "   - Don't show raw technical data like IDs unless specifically asked.\n"
                          "   - Use a natural, conversational tone.\n"
                          "4. Always confirm what you've done clearly."
            }
        ]
        
        # Add history
        messages.extend(history)
        
        # Add the new user message with User ID context
        messages.append({
            "role": "user",
            "content": f"[User Context: user_id={user_id}] {message}"
        })

        # Call the API with function calling
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        # Process the response
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        results = []
        formatted_tool_calls = []

        if tool_calls:
            # Execute the tool calls
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Add user_id if not present in the arguments
                if "user_id" not in function_args:
                    function_args["user_id"] = user_id

                # Call the appropriate MCP tool
                result = call_mcp_tool(function_name, function_args)
                results.append(result)

                formatted_tool_calls.append({
                    "tool_name": function_name,
                    "tool_input": function_args,
                    "result": result
                })

        # Generate the final response
        if results:
            # If there were tool calls, generate a response based on the results
            final_response = client.chat.completions.create(
                model=model,
                messages=messages + [
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls
                    }
                ] + [
                    {
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.id
                    }
                    for tool_call, result in zip(tool_calls, results)
                ]
            )

            response_text = final_response.choices[0].message.content or "I have processed your request and updated your tasks accordingly."
        else:
            # If no tool calls were made, use the initial response
            response_text = response_message.content or "I processed your request but didn't need to make any changes to your tasks."

        return {
            "response": response_text,
            "tool_calls": formatted_tool_calls,
            "results": results
        }

    except Exception as e:
        return {
            "error": str(e),
            "response": f"I encountered an error processing your request: {str(e)}"
        }


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stateless chat endpoint that processes natural language commands
    and uses MCP tools to manage tasks.

    Follows the Phase 3 specification:
    - Stateless server (no in-memory state)
    - Conversation state stored in database
    - Uses MCP tools for task operations
    """
    try:
        # Create or retrieve conversation ID
        conversation_id = str(request.conversation_id) if request.conversation_id else str(uuid.uuid4())
        history_to_pass = []

        # Store and fetch context in database
        with database_engine.get_session() as db:
            # Create or get conversation session
            session = db.exec(
                select(ChatSession).where(ChatSession.id == conversation_id)
            ).first()

            if not session:
                session = ChatSession(
                    id=conversation_id,
                    user_id=current_user.id,
                    title=request.message[:50] + "..." if len(request.message) > 50 else request.message
                )
                db.add(session)
                db.commit()
            else:
                # Fetch recent history (last 10 messages)
                messages = db.exec(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == conversation_id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(10)
                ).all()
                
                # Format history for LLM (need to reverse because we fetched descending)
                for msg in reversed(messages):
                    history_to_pass.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Store the NEW user message in database
            user_message = ChatMessage(
                session_id=conversation_id,
                user_id=current_user.id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            db.commit()

        # Process the natural language command using OpenAI/Gemini with history
        result = await process_with_openai_and_mcp(
            user_id=str(current_user.id),
            message=request.message,
            history=history_to_pass
        )

        # Extract response
        if "error" in result:
            response_text = f"Error: {result['error']}"
            formatted_tool_calls = []
        else:
            response_text = result.get("response", "Operation completed successfully.")
            formatted_tool_calls = result.get("tool_calls", [])

        # Store assistant response in database
        with database_engine.get_session() as db:
            assistant_message = ChatMessage(
                session_id=conversation_id,
                user_id=current_user.id,
                role="assistant",
                content=response_text
            )
            db.add(assistant_message)
            db.commit()

        return ChatResponse(
            conversation_id=conversation_id,
            response=response_text,
            tool_calls=formatted_tool_calls
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@router.get("/conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    """
    List all chat conversations for the current user.
    """
    try:
        with database_engine.get_session() as db:
            conversations = db.exec(
                select(ChatSession)
                .where(ChatSession.user_id == current_user.id)
                .order_by(ChatSession.created_at.desc())
            ).all()

        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, current_user: User = Depends(get_current_user)):
    """
    Get all messages for a specific conversation.
    """
    try:
        with database_engine.get_session() as db:
            # Verify user owns the conversation
            session = db.exec(
                select(ChatSession)
                .where(ChatSession.id == conversation_id)
                .where(ChatSession.user_id == current_user.id)
            ).first()

            if not session:
                raise HTTPException(status_code=404, detail="Conversation not found")

            messages = db.exec(
                select(ChatMessage)
                .where(ChatMessage.session_id == conversation_id)
                .order_by(ChatMessage.created_at.asc())
            ).all()

        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))