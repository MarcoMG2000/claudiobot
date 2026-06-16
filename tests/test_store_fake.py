"""FakeVectorStore property tests (cosine, top-k, upsert, metadata, dimension).

Covers Slice A fake-specific behaviour: R4, R5, R8, R9, R10, R18, R27, R28.

R14 (``test_pgvector_instantiation_raises_without_driver``) is the
instantiation-isolation unit test deferred from Slice A (A6 note); it landed with
Slice B once the ``PgVectorStore`` class existed. It runs in ``init.sh`` (NOT an
integration test) because it verifies that instantiating ``PgVectorStore``
WITHOUT the driver raises ``VectorStoreError`` (a domain error), not
``ImportError``.
"""

from __future__ import annotations

import importlib.util

import pytest

from wowrag.models import Chunk
from wowrag.store import FakeVectorStore, PgVectorStore, VectorStoreError

_DRIVER_INSTALLED = (
    importlib.util.find_spec("psycopg") is not None
    and importlib.util.find_spec("pgvector") is not None
)


def _chunk(chunk_id: str, text: str = "hello") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=f"https://wowhead.example/{chunk_id}",
        title=f"Title {chunk_id}",
        section=f"Section {chunk_id}",
    )


def test_search_orders_by_cosine_desc():  # R9, R10, R27
    store = FakeVectorStore(dimension=2)
    # Query points along +x. "near" is aligned with +x (cosine ~1),
    # "far" is orthogonal (cosine ~0), "opp" is anti-aligned (cosine ~-1).
    store.upsert(
        [_chunk("near"), _chunk("far"), _chunk("opp")],
        [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]],
    )
    results = store.similarity_search([1.0, 0.0], k=3)
    ids = [chunk.chunk_id for chunk, _ in results]
    assert ids == ["near", "far", "opp"]
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_returns_chunk_score_pairs():  # R4, R9
    store = FakeVectorStore(dimension=2)
    store.upsert([_chunk("a")], [[1.0, 0.0]])
    results = store.similarity_search([1.0, 0.0], k=1)
    assert len(results) == 1
    pair = results[0]
    assert isinstance(pair, tuple) and len(pair) == 2
    chunk, score = pair
    assert isinstance(chunk, Chunk)
    assert isinstance(score, float)


def test_search_respects_k():  # R9
    store = FakeVectorStore(dimension=2)
    store.upsert(
        [_chunk("a"), _chunk("b"), _chunk("c"), _chunk("d")],
        [[1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.7, 0.3]],
    )
    results = store.similarity_search([1.0, 0.0], k=2)
    assert len(results) == 2


def test_upsert_replaces_by_chunk_id():  # R8, R28
    store = FakeVectorStore(dimension=2)
    store.upsert([_chunk("dup", text="first")], [[1.0, 0.0]])
    store.upsert([_chunk("dup", text="second")], [[0.0, 1.0]])
    results = store.similarity_search([0.0, 1.0], k=10)
    assert len(results) == 1
    chunk, _ = results[0]
    assert chunk.chunk_id == "dup"
    assert chunk.text == "second"  # last write wins


def test_result_carries_metadata():  # R18
    store = FakeVectorStore(dimension=2)
    store.upsert([_chunk("m")], [[1.0, 0.0]])
    chunk, _ = store.similarity_search([1.0, 0.0], k=1)[0]
    assert chunk.source_url == "https://wowhead.example/m"
    assert chunk.title == "Title m"
    assert chunk.section == "Section m"


def test_dimension_default_and_custom():  # R5
    assert FakeVectorStore().dimension == 1024
    assert FakeVectorStore(dimension=64).dimension == 64


@pytest.mark.skipif(
    _DRIVER_INSTALLED,
    reason="Postgres driver is installed; the missing-driver path is not exercised",
)
def test_pgvector_instantiation_raises_without_driver():  # R14
    """Constructing PgVectorStore without the driver raises VectorStoreError.

    It must surface a domain error (VectorStoreError), never a raw ImportError,
    so callers get a uniform store-layer failure with an install hint.
    """
    with pytest.raises(VectorStoreError):
        PgVectorStore(dsn="postgresql://x", dimension=8)
