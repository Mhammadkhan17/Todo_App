"""
RAG-related data models
"""
from sqlmodel import SQLModel, Field, Column, DateTime, create_engine
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON


class Document(SQLModel, table=True):
    """
    Model representing an uploaded document
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(nullable=False)
    filename: str = Field(max_length=255, nullable=False)
    original_filename: str = Field(max_length=255, nullable=False)
    file_path: str = Field(max_length=500, nullable=False)
    file_size: int = Field(nullable=False)
    mime_type: str = Field(max_length=100, nullable=False)
    hash: str = Field(max_length=64, nullable=False)  # SHA256 hash
    status: str = Field(default="uploaded", max_length=20)  # uploaded, processing, indexed, failed
    document_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)))
    indexed_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class ChatSession(SQLModel, table=True):
    """
    Model representing a chat session
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(nullable=False)
    title: str = Field(max_length=255, nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)))
    is_active: bool = Field(default=True)


class ChatMessage(SQLModel, table=True):
    """
    Model representing a chat message
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(nullable=False)
    user_id: str = Field(nullable=False)
    role: str = Field(max_length=20, nullable=False)  # user or assistant
    content: str = Field(nullable=False)
    sources: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))  # Sources for RAG responses
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)))