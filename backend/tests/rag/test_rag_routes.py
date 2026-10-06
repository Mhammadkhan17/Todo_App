import pytest
from langchain_core.documents import Document as LCDocument
from langchain_qdrant import QdrantVectorStore

from main import app
from src.api.v1 import rag as rag_router
from src.rag.chain import _search_kwargs
from src.rag.ingest import DocumentIngestor
from src.rag.store import collection_name, ensure_collection
from tests.rag.in_memory import FakeEmbedder


class FakeChatbot:
    def __init__(self):
        self.responses = []

    def generate_response(self, query, user_id):
        self.responses.append((query, str(user_id)))
        return {
            "response": f"answer to {query}",
            "sources": [
                {"content": "c", "metadata": {"file_name": "f.txt", "score": 0.9}}
            ],
        }

    def search_similar(self, query, user_id, k=5):
        return [{"content": "hit", "metadata": {"file_name": "f.txt", "score": 0.5}}]


@pytest.fixture
def fake_chatbot():
    bot = FakeChatbot()
    app.dependency_overrides[rag_router.get_chatbot] = lambda: bot
    yield bot
    app.dependency_overrides.pop(rag_router.get_chatbot, None)


def test_chat_requires_auth(client):
    response = client.post("/api/rag/chat", json={"message": "hello"})
    assert response.status_code == 401


def test_chat_task_intent_keeps_existing_branch(
    client, auth_headers, fake_chatbot, monkeypatch
):
    monkeypatch.setattr(
        rag_router,
        "process_natural_language_command",
        lambda user_id, command: {"response": f"tasks for {user_id}"},
    )
    response = client.post(
        "/api/rag/chat",
        json={"message": "list my tasks"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "tasks for 1" in response.json()["response"]
    assert fake_chatbot.responses == []  # RAG branch not consulted


def test_chat_document_intent_uses_chatbot(client, auth_headers, fake_chatbot):
    response = client.post(
        "/api/rag/chat",
        json={"message": "what does the report say about budgets?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response"].startswith("answer to")
    assert data["sources"][0]["metadata"]["file_name"] == "f.txt"
    assert fake_chatbot.responses[0][1].isdigit()  # str(user_id)


def test_upload_rejects_bad_extension(client, auth_headers):
    response = client.post(
        "/api/rag/upload-and-index",
        files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))],
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_upload_indexes_for_current_user(
    client, auth_headers, qdrant_client, tmp_path, db_session
):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        response = client.post(
            "/api/rag/upload-and-index",
            files=[
                ("files", ("notes.txt", b"important shared knowledge", "text/plain"))
            ],
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["indexed_count"] == 1

        points, _ = qdrant_client.scroll(collection_name(), limit=10, with_payload=True)
        assert points
        assert points[0].payload["metadata"]["user_id"] == "1"
        assert points[0].payload["metadata"]["file_name"] == "notes.txt"
    finally:
        app.dependency_overrides.pop(rag_router.get_ingestor, None)


class ScopedSearchBot:
    """Delegates to a real QdrantVectorStore the way RAGChatbot does."""

    def __init__(self, qdrant_client):
        self._store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=collection_name(),
            embedding=FakeEmbedder(),
        )

    def generate_response(self, query, user_id):
        return {"response": "n/a", "sources": []}

    def search_similar(self, query, user_id, k=5):
        hits = self._store.similarity_search_with_score(
            query, **_search_kwargs(user_id, k)
        )
        return [
            {
                "content": doc.page_content,
                "metadata": {
                    "file_name": doc.metadata.get("file_name"),
                    "score": float(score),
                },
            }
            for doc, score in hits
        ]


def test_search_is_scoped_to_requesting_user(client, auth_headers, qdrant_client):
    ensure_collection(client=qdrant_client)
    store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name(),
        embedding=FakeEmbedder(),
    )
    store.add_documents(
        [
            LCDocument(
                page_content="alpha notes for user one",
                metadata={"user_id": "1", "file_name": "one.txt"},
            ),
            LCDocument(
                page_content="alpha notes for user two",
                metadata={"user_id": "2", "file_name": "two.txt"},
            ),
        ],
        ids=[
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ],
    )
    app.dependency_overrides[rag_router.get_chatbot] = lambda: ScopedSearchBot(
        qdrant_client
    )
    try:
        response = client.get(
            "/api/rag/search", params={"query": "alpha notes"}, headers=auth_headers
        )
        assert response.status_code == 200
        files = [r["metadata"]["file_name"] for r in response.json()["results"]]
        assert files == ["one.txt"]
    finally:
        app.dependency_overrides.pop(rag_router.get_chatbot, None)


def test_documents_list_and_reset(client, auth_headers, qdrant_client, tmp_path):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        client.post(
            "/api/rag/upload-and-index",
            files=[("files", ("mine.txt", b"my own document text", "text/plain"))],
            headers=auth_headers,
        )
        listing = client.get("/api/rag/documents", headers=auth_headers)
        assert listing.status_code == 200
        assert len(listing.json()["documents"]) == 1

        reset = client.delete("/api/rag/reset-index", headers=auth_headers)
        assert reset.status_code == 200
        assert reset.json()["success"] is True

        assert (
            client.get("/api/rag/documents", headers=auth_headers).json()["documents"]
            == []
        )
        assert qdrant_client.count(collection_name()).count == 0
    finally:
        app.dependency_overrides.pop(rag_router.get_ingestor, None)


def test_session_crud_smoke(client, auth_headers):
    created = client.post(
        "/api/rag/sessions", json={"title": "notes"}, headers=auth_headers
    )
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    listed = client.get("/api/rag/sessions", headers=auth_headers)
    assert listed.status_code == 200
    assert any(s["id"] == session_id for s in listed.json()["sessions"])

    messages = client.get(
        f"/api/rag/sessions/{session_id}/messages", headers=auth_headers
    )
    assert messages.status_code == 200
