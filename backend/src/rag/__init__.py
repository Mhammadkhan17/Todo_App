"""
RAG (Retrieval Augmented Generation) module for TodoFlow application

This module provides:
- Document ingestion and indexing capabilities
- AI-powered chatbot with retrieval augmentation
- Vector database integration with Qdrant
- Semantic search functionality
"""

from .chatbot import RAGChatbot
from .ingest import DocumentIngestor

__all__ = ["DocumentIngestor", "RAGChatbot"]
