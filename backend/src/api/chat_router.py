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
from ..agents.todo_agent import process_natural_language_command
from ..rag.guards import (
    INJECTION_BLOCK_MESSAGE,
    detect_injection,
    sanitize_output,
)
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/chat")


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


async def process_with_openai_and_mcp(
    user_id: str,
    message: str,
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """
    Async wrapper around todo_agent.process_natural_language_command,
    the shared LLM + MCP tool-calling implementation (kept under this
    name for the /api/chat endpoint and its tests).
    """
    return process_natural_language_command(user_id, command=message, history=history)


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
        # Deterministic input guard: refuse known injection payloads (OWASP
        # LLM01) without ever calling the LLM.
        if detect_injection(request.message):
            return ChatResponse(
                conversation_id=str(request.conversation_id)
                if request.conversation_id
                else str(uuid.uuid4()),
                response=INJECTION_BLOCK_MESSAGE,
                tool_calls=[],
            )

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

        # Deterministic output guard against prompt leakage (OWASP LLM07)
        response_text = sanitize_output(response_text)

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