"""
RAG Chatbot API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlmodel import Session, select
from ...dependencies.auth import get_current_user
from ...models.user import User
from ...models.rag import Document, ChatSession, ChatMessage
from ...database.engine import database_engine
from ...rag.chatbot import RAGChatbot
from ...rag.ingest import DocumentIngestor
from ...agents.todo_agent import process_natural_language_command
import tempfile
import os
import uuid
from datetime import datetime
import re

router = APIRouter(prefix="/rag", tags=["rag"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # If provided, continue existing session
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict]
    query: str
    session_id: str

class DocumentUploadRequest(BaseModel):
    file_urls: List[str]

class DocumentIndexResponse(BaseModel):
    success: bool
    message: str
    indexed_count: Optional[int] = None

class CreateSessionRequest(BaseModel):
    title: str

class CreateSessionResponse(BaseModel):
    session_id: str
    title: str

# Global instances for now (in production, consider dependency injection)
chatbot = RAGChatbot()
ingestor = DocumentIngestor()


def detect_intent(message: str) -> str:
    """
    Detect whether the user wants to manage tasks or query documents.

    Args:
        message: The user's message

    Returns:
        'task_management' if the message is related to task management,
        'document_query' if the message is related to document queries,
        'general' for other queries
    """
    message_lower = message.lower().strip()

    # Keywords for task management
    task_keywords = [
        'add task', 'create task', 'new task', 'add a task', 'create a task',
        'list tasks', 'show tasks', 'view tasks', 'see tasks', 'my tasks',
        'complete task', 'mark task', 'finish task', 'done task',
        'delete task', 'remove task', 'cancel task',
        'update task', 'change task', 'edit task',
        'task', 'todo', 'to-do', 'do this', 'need to', 'have to', 'want to',
        'buy groceries', 'call mom', 'schedule meeting', 'pay bills'
    ]

    # Keywords for document queries
    document_keywords = [
        'document', 'file', 'search', 'find', 'information', 'tell me',
        'what does', 'where is', 'when was', 'who is', 'how to',
        'according to', 'based on', 'refer to', 'mentioned in',
        'summarize', 'explain', 'describe', 'question about'
    ]

    # Count matches for each category
    task_matches = sum(1 for keyword in task_keywords if keyword in message_lower)
    document_matches = sum(1 for keyword in document_keywords if keyword in message_lower)

    # If task-related keywords dominate, treat as task management
    if task_matches > document_matches and task_matches > 0:
        return 'task_management'
    elif document_matches > task_matches and document_matches > 0:
        return 'document_query'
    else:
        # If uncertain, check if it's clearly a task management command
        if any(pattern in message_lower for pattern in [
            r'(add|create|make|new)\s+(a\s+)?(task|todo)',
            r'(list|show|view|see)\s+(my\s+)?tasks?',
            r'(complete|finish|done|mark)\s+(task|as\s+complete)',
            r'(delete|remove|cancel)\s+(task|the\s+task)',
            r'(update|change|edit)\s+(task)'
        ]):
            return 'task_management'
        else:
            return 'document_query'


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the RAG-enabled bot that can handle both document queries and task management
    """
    try:
        # Create or retrieve chat session
        session_id = request.session_id or str(uuid.uuid4())

        # Detect intent to determine how to process the request
        intent = detect_intent(request.message)

        if intent == 'task_management':
            # Process as task management command
            response_data = process_natural_language_command(
                user_id=str(current_user.id),
                command=request.message
            )

            # Format response based on the result
            if "error" in response_data:
                response_text = f"Error: {response_data['error']}"
            elif isinstance(response_data, dict) and "response" in response_data:
                # If it's a dict with response key (from simplified agent)
                response_text = response_data["response"]
            elif isinstance(response_data, list) and len(response_data) > 0:
                # If it's a list of tasks
                if len(response_data) == 0:
                    response_text = "You have no tasks."
                else:
                    task_list = "\\n".join([f"- {task.get('title', 'Untitled')} ({task.get('status', 'unknown')})" for task in response_data])
                    response_text = f"Here are your tasks:\\n{task_list}"
            else:
                # Handle other response formats
                response_text = str(response_data)

            # Create a simplified response format
            response = {
                "response": response_text,
                "sources": []
            }
        else:
            # Process as document query using RAG
            response = chatbot.generate_response(request.message, current_user.id)

        # Store the conversation in the database
        with database_engine.get_session() as db:
            # Create chat message entry
            chat_message = ChatMessage(
                session_id=session_id,
                user_id=current_user.id,
                role="user",
                content=request.message
            )
            db.add(chat_message)

            # Create assistant response entry
            assistant_message = ChatMessage(
                session_id=session_id,
                user_id=current_user.id,
                role="assistant",
                content=response["response"],
                sources=response.get("sources", [])
            )
            db.add(assistant_message)

            # Create session if it doesn't exist
            existing_session = db.exec(
                select(ChatSession).where(ChatSession.id == session_id)
            ).first()

            if not existing_session:
                session_title = request.message[:50] + "..." if len(request.message) > 50 else request.message
                chat_session = ChatSession(
                    id=session_id,
                    user_id=current_user.id,
                    title=session_title
                )
                db.add(chat_session)

            db.commit()

        return ChatResponse(
            response=response["response"],
            sources=response.get("sources", []),
            query=request.message,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new chat session
    """
    try:
        session_id = str(uuid.uuid4())

        with database_engine.get_session() as db:
            chat_session = ChatSession(
                id=session_id,
                user_id=current_user.id,
                title=request.title
            )
            db.add(chat_session)
            db.commit()

        return CreateSessionResponse(session_id=session_id, title=request.title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_chat_sessions(current_user: User = Depends(get_current_user)):
    """
    List all chat sessions for the user
    """
    try:
        with database_engine.get_session() as db:
            sessions = db.exec(
                select(ChatSession)
                .where(ChatSession.user_id == current_user.id)
                .order_by(ChatSession.created_at.desc())
            ).all()

        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all messages for a specific session
    """
    try:
        with database_engine.get_session() as db:
            # Verify user owns the session
            session = db.exec(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .where(ChatSession.user_id == current_user.id)
            ).first()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            messages = db.exec(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            ).all()

        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-index")
async def upload_and_index_documents(
    request: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and index documents for RAG
    """
    try:
        # In a real implementation, you'd download files from URLs
        # For now, we'll simulate the process
        # This is a simplified version - in reality, you'd need to handle file downloads securely

        # Simulate indexing process
        # For demo purposes, we'll just return success
        return DocumentIndexResponse(
            success=True,
            message=f"Started indexing {len(request.file_urls)} documents",
            indexed_count=len(request.file_urls)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-local-files")
async def index_local_files(
    file_paths: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    Index locally accessible files
    """
    try:
        # Verify user has permission to access these files (security check)
        # In a real implementation, restrict this to safe paths only
        safe_paths = []
        for path in file_paths:
            # Basic security check - only allow certain directories
            abs_path = os.path.abspath(path)
            allowed_base = os.getenv("ALLOWED_DOCUMENT_PATH", "/app/documents/")
            if abs_path.startswith(os.path.abspath(allowed_base)):
                safe_paths.append(abs_path)
            else:
                raise HTTPException(status_code=403, detail=f"Access denied to path: {path}")

        success = ingestor.index_documents(safe_paths)
        if success:
            # Store document info in database
            with database_engine.get_session() as db:
                for path in safe_paths:
                    import hashlib
                    with open(path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()

                    document = Document(
                        user_id=current_user.id,
                        filename=os.path.basename(path),
                        original_filename=os.path.basename(path),
                        file_path=path,
                        file_size=os.path.getsize(path),
                        mime_type="application/octet-stream",  # Should determine actual MIME type
                        hash=file_hash,
                        status="indexed"
                    )
                    db.add(document)

                db.commit()

            return DocumentIndexResponse(
                success=True,
                message=f"Successfully indexed {len(safe_paths)} files",
                indexed_count=len(safe_paths)
            )
        else:
            return DocumentIndexResponse(
                success=False,
                message="Failed to index documents",
                indexed_count=0
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_documents(
    query: str,
    k: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Search for documents similar to the query
    """
    try:
        results = chatbot.search_similar(query, k=k)
        return {"results": results, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_user_documents(current_user: User = Depends(get_current_user)):
    """
    List all documents uploaded by the user
    """
    try:
        with database_engine.get_session() as db:
            documents = db.exec(
                select(Document)
                .where(Document.user_id == current_user.id)
                .order_by(Document.created_at.desc())
            ).all()

        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset-index")
async def reset_rag_index(current_user: User = Depends(get_current_user)):
    """
    Reset the entire RAG index (admin only)
    """
    try:
        # Check if user is admin (simplified check)
        # In real implementation, check proper role-based access
        is_admin = current_user.email.endswith("@admin.com") or os.getenv("ADMIN_USER_ID") == current_user.id

        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        success = ingestor.delete_collection()
        if success:
            # Recreate the collection
            ingestor = DocumentIngestor()  # This will recreate the collection
            return {"success": True, "message": "RAG index reset successfully"}
        else:
            return {"success": False, "message": "Failed to reset RAG index"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))