import pytest
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from src.rag import store
from tests.rag.in_memory import FakeEmbedder


def test_defaults():
    assert store.qdrant_url() == "http://localhost:6333"
    assert store.collection_name() == "todo_documents"
    assert store.embedding_provider() == "onnx"
    assert store.embedding_dim() == 384


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("RAG_COLLECTION", "custom_col")
    assert store.qdrant_url() == "http://qdrant:6333"
    assert store.collection_name() == "custom_col"


def test_ensure_collection_creates_and_is_idempotent(qdrant_client):
    store.ensure_collection(client=qdrant_client)
    store.ensure_collection(client=qdrant_client)  # no error on second call
    info = qdrant_client.get_collection(store.collection_name())
    assert info.config.params.vectors.size == store.embedding_dim()


def test_openrouter_provider_uses_2048_dim(qdrant_client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openrouter")
    assert store.embedding_provider() == "openrouter"
    assert store.embedding_dim() == 2048
    store.ensure_collection(client=qdrant_client)
    info = qdrant_client.get_collection(store.collection_name())
    assert info.config.params.vectors.size == 2048


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "bogus")
    with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
        store.embedding_dim()
    with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
        store.get_embedder()


def test_get_embedder_returns_openrouter(monkeypatch):
    from src.rag.embeddings import DEFAULT_OPENROUTER_MODEL, OpenRouterEmbeddings

    monkeypatch.setenv("EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_EMBED_MODEL", raising=False)
    embedder = store.get_embedder()
    assert isinstance(embedder, OpenRouterEmbeddings)
    assert embedder.model == DEFAULT_OPENROUTER_MODEL
    # raw strings, not tiktoken token-IDs — NVIDIA returns 400 otherwise
    assert embedder._inner.check_embedding_ctx_length is False


def test_vectorstore_roundtrip(qdrant_client):
    store.ensure_collection(client=qdrant_client)
    vs = QdrantVectorStore(
        client=qdrant_client,
        collection_name=store.collection_name(),
        embedding=FakeEmbedder(),
    )
    vs.add_documents(
        [
            Document(
                page_content="alpha text",
                metadata={"user_id": "1", "file_name": "a.txt"},
            )
        ],
        ids=["11111111-1111-1111-1111-111111111111"],
    )
    hits = vs.similarity_search_with_score(
        "alpha text",
        k=5,
        filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.user_id", match=models.MatchValue(value="1")
                )
            ]
        ),
    )
    assert len(hits) == 1
    assert hits[0][0].page_content == "alpha text"
    assert hits[0][1] > 0.0
