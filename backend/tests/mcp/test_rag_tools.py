"""
Phase 2.3: RAG tools over the signed-in user's documents.

Both tools mirror /api/rag scoping: the retrieval allow-list is computed from
SQL (active Document rows for the MCP identity) and passed to RAGChatbot, which
additionally filters by metadata.user_id. Neither tool accepts a user id.
"""

import json

import pytest
from langchain_core.documents import Document as LCDocument
from sqlmodel import Session

from mcp import Client
from src.models.rag import Document
from src.rag.chain import create_rag_chain
from src.rag.chatbot import RAGChatbot
from tests.helpers import create_user
from tests.mcp.conftest import mcp_user
from tests.rag.in_memory import EchoLLM, InMemoryStore

RAG_TOOLS = ("todo_search_documents", "todo_ask_documents")


@pytest.fixture
def rag_store():
    return InMemoryStore()


@pytest.fixture
def mcp_rag(rag_store):
    def factory(user_id, **kwargs):
        return create_rag_chain(
            user_id, store=kwargs["store"], llm=EchoLLM(reply="Grounded answer.")
        )

    return RAGChatbot(store=rag_store, chain_factory=factory)


def _vector_doc(text: str, user_id: str, document_id: str, file_name: str):
    return LCDocument(
        page_content=text,
        metadata={
            "user_id": str(user_id),
            "document_id": document_id,
            "file_name": file_name,
        },
    )


def _sql_document(doc_id: str, user_id: str, file_name: str, *, active: bool = True):
    return Document(
        id=doc_id,
        user_id=str(user_id),
        filename=file_name,
        original_filename=file_name,
        file_path=f"/tmp/{file_name}",
        file_size=1,
        mime_type="text/plain",
        hash="0" * 64,
        status="indexed",
        is_active=active,
    )


@pytest.mark.asyncio
async def test_rag_tools_are_registered_and_read_only(mcp_server):
    async with Client(mcp_server) as client:
        tools = (await client.list_tools()).tools

    assert len(tools) == 10
    by_name = {t.name: t for t in tools}
    for name in RAG_TOOLS:
        tool = by_name[name]
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert "user_id" not in json.dumps(tool.input_schema, default=str)


@pytest.mark.asyncio
async def test_search_documents_is_scoped_to_identity(mcp_server, test_db, rag_store):
    with Session(test_db) as session:
        uid = str(mcp_user(session).id)
        other_uid = str(create_user(session).id)

    rag_store.add(_vector_doc("alpha notes for owner", uid, "doc-one", "one.txt"))
    rag_store.add(
        _vector_doc("alpha notes for stranger", other_uid, "doc-two", "two.txt")
    )
    rag_store.add(_vector_doc("alpha notes draft off", uid, "doc-off", "off.txt"))

    with Session(test_db) as session:
        session.add(_sql_document("doc-one", uid, "one.txt"))
        session.add(_sql_document("doc-two", other_uid, "two.txt"))
        session.add(_sql_document("doc-off", uid, "off.txt", active=False))
        session.commit()

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "todo_search_documents", {"query": "alpha notes"}
        )

    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    files = [r["metadata"]["file_name"] for r in payload["results"]]
    # stranger's doc filtered by user_id; inactive doc filtered by allow-list
    assert files == ["one.txt"]


@pytest.mark.asyncio
async def test_ask_documents_answers_from_own_documents_only(
    mcp_server, test_db, rag_store
):
    with Session(test_db) as session:
        uid = str(mcp_user(session).id)
        other_uid = str(create_user(session).id)

    rag_store.add(
        _vector_doc("budget says forty two dollars", uid, "doc-b", "budget.txt")
    )
    rag_store.add(
        _vector_doc("secret merger forecast numbers", other_uid, "doc-s", "secret.txt")
    )

    with Session(test_db) as session:
        session.add(_sql_document("doc-b", uid, "budget.txt"))
        session.add(_sql_document("doc-s", other_uid, "secret.txt"))
        session.commit()

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            # the fake store scores plain-token overlap, so keep "budget"
            # as a standalone token (no trailing punctuation)
            "todo_ask_documents",
            {"question": "What is the budget number"},
        )

    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["response"] == "Grounded answer."
    files = [s["metadata"]["file_name"] for s in payload["sources"]]
    assert files == ["budget.txt"]
