"""Integration tests for BgeM3Embeddings (real bge-m3 via FlagEmbedding).

Every test is marked ``@pytest.mark.integration`` and is therefore excluded by
``init.sh`` (``pytest -m "not integration"``). They require the ML stack
installed (``pip install -r requirements-ml.txt``) and, ideally, a GPU; the
module-level ``importorskip`` skips the whole file when FlagEmbedding is absent.

Traceability
------------
R4  — a batch of N texts returns N vectors.
R5  — batches larger than batch_size are processed and return one vector each.
R7  — same text, two calls in one instance -> identical vectors.
R8  — BgeM3Embeddings().embed(['...']) returns a dense bge-m3 vector.
R11 — dimension is 1024 without loading/encoding through the model.
R15 — device='cuda' without CUDA raises EmbeddingError.
R16 — empty / whitespace-only text raises EmbeddingError.
"""

from __future__ import annotations

import pytest

pytest.importorskip("FlagEmbedding")

from wowrag.embeddings import BgeM3Embeddings, EmbeddingError  # noqa: E402


@pytest.mark.integration
def test_embed_single_text():  # R8, R11
    """embed(['Hello WoW']) returns exactly 1 vector of 1024 floats."""
    provider = BgeM3Embeddings()
    vectors = provider.embed(["Hello WoW"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
    assert all(isinstance(x, float) for x in vectors[0])


@pytest.mark.integration
def test_embed_batch():  # R4, R5
    """A list of 5 texts returns 5 vectors, each of 1024 floats.

    batch_size=2 forces multiple internal batches to exercise R5.
    """
    provider = BgeM3Embeddings(batch_size=2)
    texts = ["one", "two", "three", "four", "five"]
    vectors = provider.embed(texts)
    assert len(vectors) == len(texts)
    for vec in vectors:
        assert len(vec) == 1024


@pytest.mark.integration
def test_embed_reproducible_intra_session():  # R7
    """Same text, two calls on the same instance -> identical vectors."""
    provider = BgeM3Embeddings()
    first = provider.embed(["Onyxia's Lair"])
    second = provider.embed(["Onyxia's Lair"])
    assert first == second


@pytest.mark.integration
def test_cuda_unavailable_raises():  # R15
    """device='cuda' on a machine without CUDA must raise EmbeddingError."""
    import torch

    if torch.cuda.is_available():
        pytest.skip("CUDA is available; the unavailable-device path is not exercised")
    with pytest.raises(EmbeddingError):
        BgeM3Embeddings(device="cuda")


@pytest.mark.integration
def test_embed_empty_text_raises_integration():  # R16
    """embed(['']) must raise EmbeddingError."""
    provider = BgeM3Embeddings()
    with pytest.raises(EmbeddingError):
        provider.embed([""])


@pytest.mark.integration
def test_dimension_without_model_load():  # R11
    """The dimension property returns 1024 without calling encode()."""
    provider = BgeM3Embeddings()
    assert provider.dimension == 1024
