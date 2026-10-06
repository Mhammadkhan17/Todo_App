import pytest

from src.rag.embeddings import (
    EMBEDDING_DIM,
    MODEL_DIR,
    OnnxMiniLMEmbeddings,
    l2_normalize,
    mean_pool,
)


def _model_ready() -> bool:
    """Weights fetched AND embedding deps installed (both are user-run steps)."""
    if not (MODEL_DIR / "onnx" / "model.onnx").exists():
        return False
    try:
        import onnxruntime  # noqa: F401
        from tokenizers import Tokenizer  # noqa: F401
    except ImportError:
        return False
    return True


MODEL_READY = _model_ready()


def test_mean_pool_masks_padding():
    import numpy as np

    token = np.array([[[1.0, 0.0], [3.0, 2.0], [100.0, 100.0]]])
    mask = np.array([[1, 1, 0]])
    pooled = mean_pool(token, mask)
    assert pooled.shape == (1, 2)
    np.testing.assert_allclose(pooled, [[2.0, 1.0]])


def test_l2_normalize_unit_length():
    import numpy as np

    out = l2_normalize(np.array([[3.0, 4.0]]))
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), [1.0], rtol=1e-6)


@pytest.mark.skipif(
    not (MODEL_DIR / "tokenizer.json").exists(), reason="model files not fetched yet"
)
def test_model_dir_layout():
    assert (MODEL_DIR / "tokenizer.json").exists()
    assert (MODEL_DIR / "config.json").exists()


@pytest.mark.skipif(
    not MODEL_READY,
    reason="run pip install -r requirements + fetch_embeddings_model.py first",
)
def test_real_embedding_shape_and_determinism():
    emb = OnnxMiniLMEmbeddings()
    v1 = emb.embed_query("buy groceries tomorrow")
    v2 = emb.embed_query("buy groceries tomorrow")
    assert len(v1) == EMBEDDING_DIM
    assert v1 == v2
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-4
