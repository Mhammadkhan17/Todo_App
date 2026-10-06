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
