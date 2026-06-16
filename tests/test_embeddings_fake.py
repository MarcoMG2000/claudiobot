"""Tests for FakeEmbeddingProvider-specific properties and the bge-m3 module's
lazy-import safety. All stdlib + fake; no torch, no FlagEmbedding, no GPU.

Traceability
------------
R9  — bge_m3 module imports without FlagEmbedding; instantiation raises
      EmbeddingError (not ImportError) when FlagEmbedding is missing.
R12 — FakeEmbeddingProvider imports no ML libraries (stdlib only).
R13 — determinism across independent instances for the same text.
R14 — dimension is configurable in the constructor (default 1024); every
      vector has exactly that dimension.
R17 — Settings.embedding_dim is the single source of truth feeding the fake.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

from wowrag.config import Settings
from wowrag.embeddings import EmbeddingError, FakeEmbeddingProvider


def test_custom_dimension():  # R14
    """FakeEmbeddingProvider(dimension=64) must yield vectors of 64 floats."""
    fake = FakeEmbeddingProvider(dimension=64)
    assert fake.dimension == 64
    (vector,) = fake.embed(["hello"])
    assert len(vector) == 64


def test_default_dimension():  # R14, R17
    """FakeEmbeddingProvider() must default to dimension == 1024."""
    fake = FakeEmbeddingProvider()
    assert fake.dimension == 1024
    (vector,) = fake.embed(["hello"])
    assert len(vector) == 1024


def test_determinism_cross_instance():  # R13
    """Two independent instances with the same dimension produce identical
    vectors for the same text (determinism by SHA-256 of the text)."""
    a = FakeEmbeddingProvider(dimension=128)
    b = FakeEmbeddingProvider(dimension=128)
    assert a.embed(["WoW Classic"]) == b.embed(["WoW Classic"])


def test_settings_embedding_dim_feeds_fake():  # R17
    """Settings.embedding_dim must be usable as the fake's dimension."""
    dim = Settings().embedding_dim
    fake = FakeEmbeddingProvider(dimension=dim)
    assert fake.dimension == dim
    (vector,) = fake.embed(["grounded answer"])
    assert len(vector) == dim


def test_fake_provider_uses_no_ml_libraries():  # R12
    """Importing FakeEmbeddingProvider must not pull in torch / FlagEmbedding /
    sentence-transformers."""
    import wowrag.embeddings.fake  # noqa: F401  (import for side-effect check)

    for ml_module in ("torch", "FlagEmbedding", "sentence_transformers"):
        assert ml_module not in sys.modules, (
            f"{ml_module} must not be imported by the fake provider"
        )


def test_bge_m3_module_importable_without_flagembedding():  # R9
    """import wowrag.embeddings.bge_m3 must not raise even when FlagEmbedding
    is absent (the import is lazy, inside __init__)."""
    module = importlib.import_module("wowrag.embeddings.bge_m3")
    assert hasattr(module, "BgeM3Embeddings")
    # Importing the module must not have pulled FlagEmbedding into sys.modules.
    assert "FlagEmbedding" not in sys.modules


def test_bge_m3_instantiation_raises_embedding_error():  # R9
    """When FlagEmbedding is not installed, BgeM3Embeddings() must raise
    EmbeddingError (a domain error), not a raw ImportError."""
    if importlib.util.find_spec("FlagEmbedding") is not None:
        pytest.skip("FlagEmbedding is installed; lazy-import error path not exercised")

    from wowrag.embeddings import BgeM3Embeddings

    with pytest.raises(EmbeddingError) as exc_info:
        BgeM3Embeddings()
    assert "FlagEmbedding" in str(exc_info.value)
