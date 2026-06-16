"""VectorStore contract tests, exercised through FakeVectorStore.

Covers the DB-free interface contract for Slice A:
R1, R2, R6, R7, R11, R19, R26, R29.

R13 (``test_pgvector_module_importable_without_driver``) is the import-isolation
unit test deferred from Slice A (A5 note); it landed with Slice B once the
``pgvector_store`` module existed. It runs in ``init.sh`` (NOT an integration
test) because it verifies the module imports WITHOUT the driver installed.
"""

from __future__ import annotations

import pytest

from wowrag.models import Chunk
from wowrag.store import FakeVectorStore, VectorStore, VectorStoreError


def _chunk(chunk_id: str, text: str = "hello") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url="https://wowhead.example/x",
        title="Title",
        section="Section",
    )


def test_empty_store_search_returns_empty():  # R11
    store = FakeVectorStore(dimension=3)
    assert store.similarity_search([1.0, 0.0, 0.0], k=5) == []


def test_upsert_returns_count():  # R6
    store = FakeVectorStore(dimension=2)
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    vecs = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    assert store.upsert(chunks, vecs) == 3


def test_upsert_length_mismatch_raises():  # R7
    store = FakeVectorStore(dimension=2)
    with pytest.raises(VectorStoreError):
        store.upsert([_chunk("a"), _chunk("b")], [[1.0, 0.0]])


def test_search_wrong_dimension_raises():  # R19
    store = FakeVectorStore(dimension=4)
    with pytest.raises(VectorStoreError):
        store.similarity_search([1.0, 0.0], k=3)


def test_fake_satisfies_protocol():  # R1, R26
    store: VectorStore = FakeVectorStore(dimension=8)
    assert store.dimension == 8


def test_ensure_schema_idempotent_noop():  # R2, R29
    store = FakeVectorStore(dimension=2)
    assert store.ensure_schema() is None
    assert store.ensure_schema() is None  # second call must not raise


def test_pgvector_module_importable_without_driver():  # R13
    """Importing the pgvector_store module must not require psycopg/pgvector.

    The driver import is lazy (inside PgVectorStore.__init__), so importing the
    module raises no ImportError even when the driver is not installed.
    """
    import importlib

    module = importlib.import_module("wowrag.store.pgvector_store")
    assert hasattr(module, "PgVectorStore")
