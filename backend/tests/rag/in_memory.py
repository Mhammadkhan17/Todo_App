"""Deterministic fakes for RAG tests: no ONNX, no Qdrant server, no LLM."""

import zlib

from langchain_core.embeddings import Embeddings

DIM = 384


class FakeEmbedder(Embeddings):
    """Bag-of-words 384-d embedder: overlapping words -> non-zero cosine."""

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for token in text.lower().split():
            vec[zlib.crc32(token.encode()) % DIM] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm else vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


from types import SimpleNamespace

from langchain_core.documents import Document


class InMemoryStore:
    """Duck-typed QdrantVectorStore stand-in with the same search API."""

    def __init__(self, docs: list[Document] | None = None):
        self._docs: list[tuple[Document, str]] = []
        for doc in docs or []:
            self.add(doc)

    def add(self, doc: Document) -> None:
        self._docs.append((doc, str(len(self._docs))))

    def similarity_search_with_score(self, query: str, k: int = 5, filter=None):
        from qdrant_client import models

        query_lower = query.lower()
        scored = []
        for doc, _point_id in self._docs:
            if filter is not None:
                wanted = {
                    c.match.value
                    for c in filter.must
                    if c.key == "metadata.user_id"
                    and isinstance(c.match, models.MatchValue)
                }
                if wanted and str(doc.metadata.get("user_id")) not in wanted:
                    continue
            overlap = len(
                set(query_lower.split()) & set(doc.page_content.lower().split())
            )
            score = 1.0 if overlap else 0.0
            if overlap:
                scored.append((doc, score))
        return scored[:k]


class EchoLLM:
    """Records prompts; returns a fixed reply (never touches the network)."""

    def __init__(self, reply: str = "OK"):
        self.reply = reply
        self.prompts: list = []

    def invoke(self, messages) -> SimpleNamespace:
        self.prompts.append(messages)
        return SimpleNamespace(content=self.reply)
