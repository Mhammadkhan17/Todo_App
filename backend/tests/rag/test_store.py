from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from src.rag import store
from tests.rag.in_memory import FakeEmbedder


def test_defaults():
    assert store.qdrant_url() == "http://localhost:6333"
    assert store.collection_name() == "todo_documents"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("RAG_COLLECTION", "custom_col")
    assert store.qdrant_url() == "http://qdrant:6333"
    assert store.collection_name() == "custom_col"


def test_ensure_collection_creates_and_is_idempotent(qdrant_client):
    store.ensure_collection(client=qdrant_client)
    store.ensure_collection(client=qdrant_client)  # no error on second call
    info = qdrant_client.get_collection(store.collection_name())
    assert info.config.params.vectors.size == store.EMBEDDING_DIM


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
