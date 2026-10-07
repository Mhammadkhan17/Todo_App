import pytest
from langchain_core.documents import Document as LCDocument
from langchain_qdrant import QdrantVectorStore

from main import app
from src.api.v1 import rag as rag_router
from src.models.rag import Document
from src.rag.chain import _search_kwargs
from src.rag.ingest import DocumentIngestor
from src.rag.store import collection_name, ensure_collection
from tests.rag.in_memory import FakeEmbedder


class FakeChatbot:
    def __init__(self):
        self.responses = []

    def generate_response(self, query, user_id, document_ids=None):
        self.responses.append((query, str(user_id), document_ids))
        return {
            "response": f"answer to {query}",
            "sources": [
                {"content": "c", "metadata": {"file_name": "f.txt", "score": 0.9}}
            ],
        }

    def search_similar(self, query, user_id, k=5, document_ids=None):
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

    def generate_response(self, query, user_id, document_ids=None):
        return {"response": "n/a", "sources": []}

    def search_similar(self, query, user_id, k=5, document_ids=None):
        hits = self._store.similarity_search_with_score(
            query, **_search_kwargs(user_id, k, document_ids=document_ids)
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


def test_search_is_scoped_to_requesting_user(
    client, auth_headers, qdrant_client, db_session
):
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
                metadata={
                    "user_id": "1",
                    "file_name": "one.txt",
                    "document_id": "doc-one",
                },
            ),
            LCDocument(
                page_content="alpha notes for user two",
                metadata={
                    "user_id": "2",
                    "file_name": "two.txt",
                    "document_id": "doc-two",
                },
            ),
        ],
        ids=[
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ],
    )
    # Retrieval allow-lists come from SQL: give both points document rows
    for doc_id, user_id, name in (
        ("doc-one", "1", "one.txt"),
        ("doc-two", "2", "two.txt"),
    ):
        db_session.add(
            Document(
                id=doc_id,
                user_id=user_id,
                filename=name,
                original_filename=name,
                file_path=f"/tmp/{name}",
                file_size=1,
                mime_type="text/plain",
                hash="0" * 64,
                status="indexed",
            )
        )
    db_session.commit()

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


def test_delete_single_document(client, auth_headers, qdrant_client, tmp_path):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        client.post(
            "/api/rag/upload-and-index",
            files=[("files", ("keep.txt", b"content to index and drop", "text/plain"))],
            headers=auth_headers,
        )
        docs = client.get("/api/rag/documents", headers=auth_headers).json()[
            "documents"
        ]
        assert len(docs) == 1
        doc_id = docs[0]["id"]
        assert qdrant_client.count(collection_name()).count >= 1

        resp = client.delete(f"/api/rag/documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {
            "success": True,
            "removed_chunks": resp.json()["removed_chunks"],
        }

        assert (
            client.get("/api/rag/documents", headers=auth_headers).json()["documents"]
            == []
        )
        assert qdrant_client.count(collection_name()).count == 0
    finally:
        app.dependency_overrides.pop(rag_router.get_ingestor, None)


def test_delete_document_is_scoped_to_owner(
    client, auth_headers, qdrant_client, tmp_path, make_user
):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    try:
        client.post(
            "/api/rag/upload-and-index",
            files=[("files", ("mine.txt", b"my private document text", "text/plain"))],
            headers=auth_headers,
        )
        docs = client.get("/api/rag/documents", headers=auth_headers).json()[
            "documents"
        ]
        doc_id = docs[0]["id"]

        other = make_user("ragother_del", "rag-other-del@example.com")
        stolen = client.delete(f"/api/rag/documents/{doc_id}", headers=other)
        assert stolen.status_code == 404

        missing = client.delete(
            "/api/rag/documents/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert missing.status_code == 404

        # Owner's document survives both failed attempts
        assert (
            len(
                client.get("/api/rag/documents", headers=auth_headers).json()[
                    "documents"
                ]
            )
            == 1
        )
        assert qdrant_client.count(collection_name()).count >= 1
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


@pytest.fixture
def ingest_override(qdrant_client, tmp_path):
    app.dependency_overrides[rag_router.get_ingestor] = lambda: DocumentIngestor(
        client=qdrant_client, embedder=FakeEmbedder(), uploads_dir=tmp_path / "uploads"
    )
    yield
    app.dependency_overrides.pop(rag_router.get_ingestor, None)


def _upload(
    client, headers, filename="scope.txt", content=b"scoped content", data=None
):
    return client.post(
        "/api/rag/upload-and-index",
        files=[("files", (filename, content, "text/plain"))],
        data=data or {},
        headers=headers,
    )


def test_upload_scope_validation_and_defaults(client, auth_headers, ingest_override):
    bad = _upload(client, auth_headers, data={"scope": "team"})
    assert bad.status_code == 400

    ok = _upload(client, auth_headers, data={"scope": "chat"})
    assert ok.status_code == 200, ok.text

    default = _upload(client, auth_headers, filename="plain.txt")
    assert default.status_code == 200

    docs = {
        d["original_filename"]: d
        for d in client.get("/api/rag/documents", headers=auth_headers).json()[
            "documents"
        ]
    }
    assert docs["scope.txt"]["scope"] == "chat"
    assert docs["scope.txt"]["session_id"] is None  # pending: binds on first message
    assert docs["scope.txt"]["is_active"] is True
    assert docs["plain.txt"]["scope"] == "universal"


def test_upload_scope_chat_requires_owned_session(
    client, auth_headers, other_user_headers, ingest_override
):
    foreign = client.post(
        "/api/rag/sessions", json={"title": "their chat"}, headers=other_user_headers
    ).json()["session_id"]

    stolen = _upload(
        client, auth_headers, data={"scope": "chat", "session_id": foreign}
    )
    assert stolen.status_code == 404


def test_chat_binds_pending_documents_and_passes_allowlist(
    client, auth_headers, fake_chatbot, ingest_override
):
    upload = _upload(client, auth_headers, data={"scope": "chat"})
    assert upload.status_code == 200
    doc_id = client.get("/api/rag/documents", headers=auth_headers).json()["documents"][
        0
    ]["id"]

    response = client.post(
        "/api/rag/chat",
        json={
            "message": "what does the report say about budgets?",
            "document_ids": [doc_id],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]

    # Pending chat-scoped doc is now bound to the session that was just created
    docs = client.get("/api/rag/documents", headers=auth_headers).json()["documents"]
    assert docs[0]["session_id"] == session_id
    assert docs[0]["scope"] == "chat"

    # Retrieval allow-list handed to the chatbot contains the bound doc
    _query, user_id, allowed = fake_chatbot.responses[0]
    assert user_id == "1"
    assert allowed == [doc_id]


def test_chat_passes_empty_allowlist_without_documents(
    client, auth_headers, fake_chatbot
):
    response = client.post(
        "/api/rag/chat",
        json={"message": "what does the report say about budgets?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    # No rows -> allow-list is empty; retrieval must not widen to all user chunks
    assert fake_chatbot.responses[0][2] == []


def test_chat_resume_requires_owned_session(
    client, auth_headers, other_user_headers, fake_chatbot
):
    foreign = client.post(
        "/api/rag/sessions", json={"title": "their chat"}, headers=other_user_headers
    ).json()["session_id"]

    stolen = client.post(
        "/api/rag/chat",
        json={"message": "list my tasks", "session_id": foreign},
        headers=auth_headers,
    )
    assert stolen.status_code == 404

    # Unknown ids are rejected too — no silent adoption of a client-chosen id
    missing = client.post(
        "/api/rag/chat",
        json={"message": "list my tasks", "session_id": "no-such-session"},
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_patch_document_keep_toggle(client, auth_headers, ingest_override):
    assert _upload(client, auth_headers).status_code == 200
    doc_id = client.get("/api/rag/documents", headers=auth_headers).json()["documents"][
        0
    ]["id"]

    off = client.patch(
        f"/api/rag/documents/{doc_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert off.status_code == 200
    assert off.json()["is_active"] is False

    docs = client.get("/api/rag/documents", headers=auth_headers).json()["documents"]
    assert docs[0]["is_active"] is False  # kept in the library, just not retrieved

    on = client.patch(
        f"/api/rag/documents/{doc_id}",
        json={"is_active": True},
        headers=auth_headers,
    )
    assert on.status_code == 200
    assert on.json()["is_active"] is True


def test_patch_document_is_scoped_to_owner(
    client, auth_headers, other_user_headers, ingest_override
):
    assert _upload(client, auth_headers).status_code == 200
    doc_id = client.get("/api/rag/documents", headers=auth_headers).json()["documents"][
        0
    ]["id"]

    stolen = client.patch(
        f"/api/rag/documents/{doc_id}",
        json={"is_active": False},
        headers=other_user_headers,
    )
    assert stolen.status_code == 404

    missing = client.patch(
        "/api/rag/documents/00000000-0000-0000-0000-000000000000",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert missing.status_code == 404

    docs = client.get("/api/rag/documents", headers=auth_headers).json()["documents"]
    assert docs[0]["is_active"] is True  # untouched
