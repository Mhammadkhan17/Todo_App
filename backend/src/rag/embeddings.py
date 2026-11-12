"""Embedding providers: local ONNX MiniLM-L6-v2 and hosted OpenRouter Nemotron.

`EMBEDDING_PROVIDER` selects which one `store.get_embedder()` returns:
`onnx` (local, 384-dim) or `openrouter` (hosted, 2048-dim).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from langchain_core.embeddings import Embeddings

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "all-MiniLM-L6-v2"
ONNX_EMBEDDING_DIM = 384
MAX_TOKENS = 256

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-embed-1b:free"
OPENROUTER_EMBEDDING_DIM = 2048


def mean_pool(token_embeddings, attention_mask):
    """Attention-masked mean of token embeddings. numpy arrays: (B, L, D), (B, L)."""
    import numpy as np

    mask = attention_mask.astype(np.float32)[:, :, None]
    summed = (token_embeddings.astype(np.float32) * mask).sum(axis=1)
    counts = mask.sum(axis=1).clip(min=1e-9)
    return summed / counts


def l2_normalize(embeddings):
    import numpy as np

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
    return embeddings / norms


class OnnxMiniLMEmbeddings(Embeddings):
    def __init__(self, model_dir: Path = MODEL_DIR, max_tokens: int = MAX_TOKENS):
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise ImportError(
                "RAG embedding deps missing — install backend/requirements.txt "
                "(onnxruntime, tokenizers)"
            ) from exc

        onnx_path = model_dir / "onnx" / "model.onnx"
        if not onnx_path.exists():
            raise FileNotFoundError(
                f"{onnx_path} not found — run scripts/fetch_embeddings_model.py first"
            )

        config = json.loads((model_dir / "config.json").read_text())
        pad_id = config.get("pad_token_id", 0)

        self._tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self._tokenizer.enable_truncation(max_length=max_tokens)
        self._tokenizer.enable_padding(pad_id=pad_id)
        self._session = onnxruntime.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        self._input_names = {i.name for i in self._session.get_inputs()}

    def _encode(self, texts: list[str]):
        import numpy as np

        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feed: dict = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.zeros_like(input_ids)
        token_embeddings = self._session.run(None, feed)[0]
        return l2_normalize(mean_pool(token_embeddings, attention_mask))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0].tolist()


class OpenRouterEmbeddings(Embeddings):
    """Hosted embeddings via OpenRouter's OpenAI-compatible `/api/v1/embeddings`."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "OpenRouter embedding deps missing — install backend/requirements.txt "
                "(langchain-openai)"
            ) from exc

        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not set — required when EMBEDDING_PROVIDER=openrouter"
            )
        self.model = model or os.getenv(
            "OPENROUTER_EMBED_MODEL", DEFAULT_OPENROUTER_MODEL
        )
        # check_embedding_ctx_length=True (default) tokenizes with tiktoken and
        # sends token-ID arrays; NVIDIA rejects those ("support strings and
        # multimodal inputs") — send raw strings instead. See langchain_openai
        # OpenAIEmbeddings note for OpenAI-compatible APIs.
        self._inner = OpenAIEmbeddings(
            model=self.model,
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            check_embedding_ctx_length=False,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(text)
