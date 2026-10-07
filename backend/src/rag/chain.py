"""Retrieval-augmented answer chain: filtered search -> grounded prompt -> sources."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import HumanMessage

from ..llm.provider import make_llm
from .store import (
    get_vectorstore,  # cheap: embedder/vectorstore stay lazy behind lru_cache
)

DEFAULT_K = 5
PROMPT_TEMPLATE = """You are TodoFlow's study assistant. Answer the user's question using ONLY the context below, and cite the source file names you used. If the answer is not in the context, say you don't know based on their documents.

Context:
{context}

Question: {question}"""


def _search_kwargs(
    user_id: str, k: int = DEFAULT_K, document_ids: list[str] | None = None
) -> dict:
    from qdrant_client import models

    must: list = [
        models.FieldCondition(
            key="metadata.user_id",
            match=models.MatchValue(value=str(user_id)),
        )
    ]
    if document_ids is not None:
        must.append(
            models.FieldCondition(
                key="metadata.document_id",
                match=models.MatchAny(any=[str(i) for i in document_ids]),
            )
        )
    return {"k": k, "filter": models.Filter(must=must)}


def _source_metadata(doc, score: float) -> dict:
    metadata = doc.metadata or {}
    file_name = metadata.get("file_name") or metadata.get("filename") or "unknown"
    return {"file_name": file_name, "score": round(float(score), 4)}


def hits_to_sources(hits) -> list[dict]:
    return [
        {"content": doc.page_content, "metadata": _source_metadata(doc, score)}
        for doc, score in hits
    ]


def create_rag_chain(user_id: str, *, store=None, llm=None) -> Callable[..., dict]:
    """Build `(question, document_ids=None) -> {"response", "sources"}` for one user.

    `document_ids` is the SQL-computed allow-list (None = no allow-list, legacy);
    it is passed per call so toggles/session scoping take effect immediately even
    though the chain is cached per user.

    Fails fast on a missing LLM key BEFORE touching the vector store.
    """
    if llm is None:
        llm = make_llm()
    store = store or get_vectorstore()

    def _run(question: str, document_ids: list[str] | None = None) -> dict:
        if document_ids is not None and not document_ids:
            hits = []  # every document disabled or none allowed for this chat
        else:
            hits = store.similarity_search_with_score(
                question, **_search_kwargs(str(user_id), document_ids=document_ids)
            )
        context = (
            "\n\n".join(doc.page_content for doc, _ in hits) or "(no documents found)"
        )
        messages = [
            HumanMessage(
                content=PROMPT_TEMPLATE.format(context=context, question=question)
            )
        ]
        answer = llm.invoke(messages)
        return {"response": answer.content, "sources": hits_to_sources(hits)}

    return _run
