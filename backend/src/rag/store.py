"""Qdrant client, embedder, and vectorstore singletons."""

from __future__ import annotations

import os
from functools import lru_cache

from qdrant_client import QdrantClient

from .embeddings import ONNX_EMBEDDING_DIM, OPENROUTER_EMBEDDING_DIM

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "todo_documents"
DEFAULT_EMBEDDING_PROVIDER = "onnx"
PROVIDER_DIMS = {"onnx": ONNX_EMBEDDING_DIM, "openrouter": OPENROUTER_EMBEDDING_DIM}
PAYLOAD_INDEX_FIELDS = ("metadata.user_id", "metadata.document_id")


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL") or DEFAULT_QDRANT_URL


def collection_name() -> str:
    return os.getenv("RAG_COLLECTION") or DEFAULT_COLLECTION


def embedding_provider() -> str:
    raw = os.getenv("EMBEDDING_PROVIDER") or DEFAULT_EMBEDDING_PROVIDER
    return raw.strip().lower() or DEFAULT_EMBEDDING_PROVIDER


def _unknown_provider(provider: str) -> ValueError:
    return ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}' "
        f"(expected one of: {', '.join(sorted(PROVIDER_DIMS))})"
    )


def embedding_dim() -> int:
    provider = embedding_provider()
    if provider not in PROVIDER_DIMS:
        raise _unknown_provider(provider)
    return PROVIDER_DIMS[provider]


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    api_key = os.getenv("QDRANT_API_KEY") or None
    if api_key:
        return QdrantClient(url=qdrant_url(), api_key=api_key, timeout=30)
    return QdrantClient(url=qdrant_url(), timeout=30)


@lru_cache(maxsize=1)
def get_embedder():
    provider = embedding_provider()
    if provider == "onnx":
        from .embeddings import OnnxMiniLMEmbeddings

        return OnnxMiniLMEmbeddings()
    if provider == "openrouter":
        from .embeddings import OpenRouterEmbeddings

        return OpenRouterEmbeddings()
    raise _unknown_provider(provider)


def ensure_collection(client: QdrantClient | None = None) -> None:
    from qdrant_client import models

    client = client or get_client()
    name = collection_name()
    if client.collection_exists(name):
        return
    client.create_collection(
        name,
        vectors_config=models.VectorParams(
            size=embedding_dim(), distance=models.Distance.COSINE
        ),
    )
    for field in PAYLOAD_INDEX_FIELDS:
        client.create_payload_index(
            name, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
        )


@lru_cache(maxsize=1)
def get_vectorstore():
    from langchain_qdrant import QdrantVectorStore

    ensure_collection()
    return QdrantVectorStore(
        client=get_client(),
        collection_name=collection_name(),
        embedding=get_embedder(),
    )


def reset_singletons() -> None:
    get_client.cache_clear()
    get_embedder.cache_clear()
    get_vectorstore.cache_clear()
