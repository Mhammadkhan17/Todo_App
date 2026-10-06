"""Local ONNX MiniLM-L6-v2 embeddings (Approach A: port of rag-example)."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.embeddings import Embeddings

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
MAX_TOKENS = 256


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
