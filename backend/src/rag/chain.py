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


def _search_kwargs(user_id: str, k: int = DEFAULT_K) -> dict:
    from qdrant_client import models

    return {
        "k": k,
        "filter": models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.user_id",
                    match=models.MatchValue(value=str(user_id)),
                )
            ]
        ),
    }


def _source_metadata(doc, score: float) -> dict:
    metadata = doc.metadata or {}
    file_name = metadata.get("file_name") or metadata.get("filename") or "unknown"
    return {"file_name": file_name, "score": round(float(score), 4)}


def hits_to_sources(hits) -> list[dict]:
    return [
        {"content": doc.page_content, "metadata": _source_metadata(doc, score)}
        for doc, score in hits
    ]


def create_rag_chain(user_id: str, *, store=None, llm=None) -> Callable[[str], dict]:
    """Build `question -> {"response", "sources"}` for one user.

    Fails fast on a missing LLM key BEFORE touching the vector store.
    """
    if llm is None:
        llm = make_llm()
    store = store or get_vectorstore()

    kwargs = _search_kwargs(str(user_id))

    def _run(question: str) -> dict:
        hits = store.similarity_search_with_score(question, **kwargs)
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
