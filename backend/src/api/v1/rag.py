"""
RAG Chatbot API endpoints
"""
import os
import uuid
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from pydantic import BaseModel
from sqlmodel import Session, select

from ...agents.todo_agent import process_natural_language_command
from ...database.session import get_session
from ...dependencies.auth import get_current_user
from ...models.rag import ChatMessage, ChatSession, Document
from ...models.user import User
from ...rag.chatbot import RAGChatbot
from ...rag.ingest import DocumentIngestor

router = APIRouter(prefix="/rag")

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # If provided, continue existing session
    user_id: str | None = None
    # Chat-scoped docs uploaded before this session existed: bind them now
    document_ids: list[str] | None = None

class ChatResponse(BaseModel):
    response: str
    sources: list[dict]
    query: str
    session_id: str

class DocumentIndexResponse(BaseModel):
    success: bool
    message: str
    indexed_count: int | None = None

class DocumentActiveRequest(BaseModel):
    is_active: bool

class CreateSessionRequest(BaseModel):
    title: str

class CreateSessionResponse(BaseModel):
    session_id: str
    title: str

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}


def get_chatbot() -> RAGChatbot:
    return RAGChatbot()


def get_ingestor() -> DocumentIngestor:
    return DocumentIngestor()


CurrentUserDep = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_session)]
ChatbotDep = Annotated[RAGChatbot, Depends(get_chatbot)]
IngestorDep = Annotated[DocumentIngestor, Depends(get_ingestor)]


def _bind_pending_documents(
    db: Session, user_id: str, session_id: str, document_ids: list[str]
) -> None:
    """Attach chat-scoped docs uploaded before this session existed."""
    rows = db.exec(
        select(Document)
        .where(Document.user_id == user_id)
        .where(Document.id.in_(document_ids))
    ).all()
    changed = False
    for row in rows:
        if row.scope == "chat" and row.session_id is None:
            row.session_id = session_id
            db.add(row)
            changed = True
    if changed:
        db.commit()


def _allowed_document_ids(db: Session, user_id: str, session_id: str) -> list[str]:
    """Docs retrievable in this chat: active AND (universal OR bound here)."""
    rows = db.exec(
        select(Document.id)
        .where(Document.user_id == user_id)
        .where(Document.is_active.is_(True))
        .where(
            (Document.scope == "universal") | (Document.session_id == session_id)
        )
    ).all()
    return [str(row_id) for row_id in rows]


def _active_document_ids(db: Session, user_id: str) -> list[str]:
    """All of the user's kept documents (search ignores chat scoping)."""
    rows = db.exec(
        select(Document.id)
        .where(Document.user_id == user_id)
        .where(Document.is_active.is_(True))
    ).all()
    return [str(row_id) for row_id in rows]


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
def chat_with_rag(
    request: ChatRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
    bot: ChatbotDep,
) -> ChatResponse:
    """
    Chat with the RAG-enabled bot that can handle both document queries and task management
    """
    try:
        # Create or retrieve chat session
        session_id = request.session_id or str(uuid.uuid4())

        # Resume only into a session the caller owns (matches upload/GET guards)
        if request.session_id:
            owner = db.exec(
                select(ChatSession)
                .where(ChatSession.id == request.session_id)
                .where(ChatSession.user_id == str(current_user.id))
            ).first()
            if owner is None:
                raise HTTPException(status_code=404, detail="Session not found")

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
            if request.document_ids:
                _bind_pending_documents(
                    db, str(current_user.id), session_id, request.document_ids
                )
            allowed_ids = _allowed_document_ids(
                db, str(current_user.id), session_id
            )
            response = bot.generate_response(
                request.message,
                str(current_user.id),
                document_ids=allowed_ids,
            )

        # Store the conversation in the database
        # Create chat message entry
        chat_message = ChatMessage(
            session_id=session_id,
            user_id=str(current_user.id),
            role="user",
            content=request.message
        )
        db.add(chat_message)

        # Create assistant response entry
        assistant_message = ChatMessage(
            session_id=session_id,
            user_id=str(current_user.id),
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
                user_id=str(current_user.id),
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", response_model=CreateSessionResponse)
def create_chat_session(
    request: CreateSessionRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> CreateSessionResponse:
    """
    Create a new chat session
    """
    try:
        session_id = str(uuid.uuid4())

        chat_session = ChatSession(
            id=session_id,
            user_id=str(current_user.id),
            title=request.title
        )
        db.add(chat_session)
        db.commit()

        return CreateSessionResponse(session_id=session_id, title=request.title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
def list_chat_sessions(
    current_user: CurrentUserDep,
    db: SessionDep,
) -> dict[str, Any]:
    """
    List all chat sessions for the user
    """
    try:
        sessions = db.exec(
            select(ChatSession)
            .where(ChatSession.user_id == str(current_user.id))
            .order_by(ChatSession.created_at.desc())
        ).all()

        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: Annotated[str, Path()],
    current_user: CurrentUserDep,
    db: SessionDep,
) -> dict[str, Any]:
    """
    Get all messages for a specific session
    """
    try:
        # Verify user owns the session
        session = db.exec(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == str(current_user.id))
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
def upload_and_index_documents(
    files: Annotated[list[UploadFile], File()],
    current_user: CurrentUserDep,
    db: SessionDep,
    ingestor: IngestorDep,
    scope: Annotated[str, Form()] = "universal",
    session_id: Annotated[str | None, Form()] = None,
) -> DocumentIndexResponse:
    """
    Upload documents and index them into the user's Qdrant collection.

    `scope` is "universal" (retrieved in every chat) or "chat" (only the chat
    identified by `session_id`; omit `session_id` to bind on first message).
    """
    try:
        if scope not in {"universal", "chat"}:
            raise HTTPException(status_code=400, detail="scope must be universal or chat")
        if scope == "universal":
            session_id = None
        elif session_id:
            owner = db.exec(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .where(ChatSession.user_id == str(current_user.id))
            ).first()
            if owner is None:
                raise HTTPException(status_code=404, detail="Session not found")

        payloads: list[tuple[str, bytes]] = []
        rejected = 0
        for upload in files:
            ext = os.path.splitext(upload.filename or "")[1].lower()
            if ext not in ALLOWED_UPLOAD_EXTENSIONS:
                rejected += 1
                continue
            content = upload.file.read()
            if len(content) > MAX_FILE_SIZE:
                rejected += 1
                continue
            payloads.append((upload.filename or "unnamed", content))

        if not payloads:
            raise HTTPException(
                status_code=400,
                detail="No valid files. Supported: PDF, TXT, MD, DOCX (max 10MB each).",
            )

        result = ingestor.ingest_upload(
            db, str(current_user.id), payloads, scope=scope, session_id=session_id
        )
        return DocumentIndexResponse(
            success=result.failed == 0,
            message=(
                f"Indexed {result.indexed}, skipped {result.skipped}, "
                f"failed {result.failed}"
                + (f" ({'; '.join(result.errors[:3])})" if result.errors else "")
            ),
            indexed_count=result.indexed + result.skipped,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-local-files")
def index_local_files(
    file_paths: list[str],
    current_user: CurrentUserDep,
    db: SessionDep,
    ingestor: IngestorDep,
) -> DocumentIndexResponse:
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

        result = ingestor.ingest_paths(db, str(current_user.id), safe_paths)
        return DocumentIndexResponse(
            success=result.failed == 0,
            message=f"Indexed {result.indexed}, failed {result.failed}",
            indexed_count=result.indexed + result.skipped,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_documents(
    current_user: CurrentUserDep,
    db: SessionDep,
    bot: ChatbotDep,
    query: Annotated[str, Query()],
    k: Annotated[int, Query()] = 5,
) -> dict[str, Any]:
    """
    Search for documents similar to the query (current user's kept docs only).
    """
    try:
        allowed_ids = _active_document_ids(db, str(current_user.id))
        results = bot.search_similar(
            query, str(current_user.id), k=k, document_ids=allowed_ids
        )
        return {"results": results, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
def list_user_documents(
    current_user: CurrentUserDep,
    db: SessionDep,
) -> dict[str, Any]:
    """
    List all documents uploaded by the user
    """
    try:
        documents = db.exec(
            select(Document)
            .where(Document.user_id == str(current_user.id))
            .order_by(Document.created_at.desc())
        ).all()

        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
def delete_user_document(
    document_id: Annotated[str, Path()],
    current_user: CurrentUserDep,
    db: SessionDep,
    ingestor: IngestorDep,
) -> dict[str, Any]:
    """
    Delete one of the caller's indexed documents (chunks, stored file, DB row).
    """
    try:
        removed = ingestor.delete_document(db, str(current_user.id), document_id)
        if removed is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "removed_chunks": removed}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - match sibling routes
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/documents/{document_id}")
def set_document_active(
    document_id: Annotated[str, Path()],
    request: DocumentActiveRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> dict[str, Any]:
    """
    Keep-toggle: set is_active (false = kept in library, excluded from retrieval).
    """
    try:
        row = db.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.user_id == str(current_user.id))
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found")
        row.is_active = request.is_active
        db.add(row)
        db.commit()
        return {
            "success": True,
            "document_id": document_id,
            "is_active": row.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - match sibling routes
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset-index")
def reset_rag_index(
    current_user: CurrentUserDep,
    db: SessionDep,
    ingestor: IngestorDep,
) -> dict[str, Any]:
    """
    Reset the current user's RAG index and document rows.
    """
    try:
        user_id = str(current_user.id)
        deleted = ingestor.reset_user(db, user_id)
        return {
            "success": True,
            "message": f"Removed {deleted} indexed chunks and document records for user {user_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))