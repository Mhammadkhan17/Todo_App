"""RAG chatbot facade: per-user cached chains + direct similarity search."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .chain import _search_kwargs, create_rag_chain, hits_to_sources


class RAGChatbot:
    def __init__(self, *, store=None, chain_factory=None):
        self._store = store
        self._chain_factory = chain_factory
        self._chains: dict[str, Callable[[str], dict]] = {}

    def _chain(self, user_id: str) -> Callable[[str], dict]:
        user_id = str(user_id)
        if user_id not in self._chains:
            factory = self._chain_factory or create_rag_chain
            kwargs = {"store": self._store} if self._store is not None else {}
            self._chains[user_id] = factory(user_id, **kwargs)
        return self._chains[user_id]

    def generate_response(self, query: str, user_id: str) -> dict[str, Any]:
        return self._chain(user_id)(query)

    def search_similar(
        self, query: str, user_id: str, k: int = 5
    ) -> list[dict[str, Any]]:
        if self._store is None:
            from .store import get_vectorstore

            self._store = get_vectorstore()
        hits = self._store.similarity_search_with_score(
            query, **_search_kwargs(user_id, k)
        )
        return hits_to_sources(hits)
