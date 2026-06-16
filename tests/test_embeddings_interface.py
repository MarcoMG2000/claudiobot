"""Tests for the EmbeddingProvider Protocol contract.

The contract is exercised through ``FakeEmbeddingProvider`` (zero ML deps),
which is the canonical test-time implementation of ``EmbeddingProvider``.

Traceability
------------
R1  — EmbeddingProvider Protocol: FakeEmbeddingProvider satisfies embed().
R2  — EmbeddingProvider Protocol: read-only dimension property.
R3  — embed([]) returns [] without raising.
R4  — embed(N texts) returns exactly N vectors in input order.
R6  — every returned vector has exactly `dimension` float elements.
R7  — embedding the same text twice yields identical vectors (intra-instance).
R16 — empty / whitespace-only text raises EmbeddingError naming the position.
"""

from __future__ import annotations

import pytest

from wowrag.embeddings import (
    EmbeddingError,
    EmbeddingProvider,
    FakeEmbeddingProvider,
)


def test_embed_empty_list():  # R3
    """embed([]) must return [] without raising."""
    fake = FakeEmbeddingProvider()
    assert fake.embed([]) == []


def test_embed_returns_same_count():  # R4
    """embed(['a', 'b', 'c']) must return exactly 3 vectors in order."""
    fake = FakeEmbeddingProvider(dimension=16)
    vectors = fake.embed(["a", "b", "c"])
    assert len(vectors) == 3
    # Order preserved: distinct texts -> distinct vectors at their positions.
    assert vectors[0] == fake.embed(["a"])[0]
    assert vectors[1] == fake.embed(["b"])[0]
    assert vectors[2] == fake.embed(["c"])[0]


def test_embed_vector_dimension():  # R6
    """Each returned vector must have exactly `dimension` float elements."""
    fake = FakeEmbeddingProvider(dimension=32)
    vectors = fake.embed(["alpha", "beta"])
    for vec in vectors:
        assert len(vec) == fake.dimension == 32
        assert all(isinstance(x, float) for x in vec)


def test_embed_same_text_reproducible():  # R7
    """Embedding the same text twice in one instance yields identical vectors."""
    fake = FakeEmbeddingProvider(dimension=16)
    first = fake.embed(["the same text"])
    second = fake.embed(["the same text"])
    assert first == second


def test_provider_protocol_compatible():  # R1, R2
    """FakeEmbeddingProvider must be assignable to EmbeddingProvider.

    Structural check: the Protocol exposes a read-only `dimension` property and
    an `embed` method, both satisfied by the fake.
    """
    provider: EmbeddingProvider = FakeEmbeddingProvider(dimension=8)
    assert provider.dimension == 8  # R2: read-only dimension property
    assert provider.embed(["x"])  # R1: embed() callable via the Protocol


def test_embed_invalid_text_raises():  # R16
    """embed(['ok', '']) must raise EmbeddingError naming position 1."""
    fake = FakeEmbeddingProvider()
    with pytest.raises(EmbeddingError) as exc_info:
        fake.embed(["ok", ""])
    assert "1" in str(exc_info.value)


def test_embed_whitespace_text_raises():  # R16
    """embed(['  ']) must raise EmbeddingError for whitespace-only text."""
    fake = FakeEmbeddingProvider()
    with pytest.raises(EmbeddingError):
        fake.embed(["  "])
