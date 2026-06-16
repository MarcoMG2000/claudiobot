"""Integration tests for PgVectorStore (real PostgreSQL + pgvector).

Every test is marked ``@pytest.mark.integration`` and is therefore excluded by
``init.sh`` (``pytest -m "not integration"``). They require:
  - the driver installed: ``pip install -r requirements-pg.txt`` (module-level
    ``importorskip`` skips the whole file when ``psycopg`` is absent), and
  - a live Postgres with the pgvector extension, reachable at ``WOWRAG_TEST_DSN``
    (the per-test fixtures skip when no DSN is configured).

Traceability
------------
R12 — PgVectorStore is a concrete VectorStore backed by Postgres + pgvector.
R15 — ensure_schema() creates the schema and is idempotent (2nd call no error).
R16 — the vector column dimension equals embedding_dim.
R17 — the migration DDL comes from migrations.sql.
R18 — each returned Chunk carries source_url/title/section metadata.
R10 — score is cosine (higher == more similar); results ordered score desc.
R8  — re-upserting an existing chunk_id replaces it, never duplicates.
R25 — a bad DSN / unreachable Postgres raises VectorStoreError.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("psycopg")
pytest.importorskip("pgvector")

from wowrag.models import Chunk  # noqa: E402
from wowrag.store import PgVectorStore, VectorStoreError  # noqa: E402

_DSN = os.environ.get("WOWRAG_TEST_DSN")
_DIM = 4


def _chunk(chunk_id: str, text: str = "hello") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=f"https://wowhead.example/{chunk_id}",
        title=f"Title {chunk_id}",
        section=f"Section {chunk_id}",
    )


@pytest.fixture
def store():
    """A PgVectorStore on a throwaway table; drops the table afterwards."""
    if not _DSN:
        pytest.skip("WOWRAG_TEST_DSN not set; no live Postgres+pgvector available")
    table = "test_chunks_" + uuid.uuid4().hex[:8]
    s = PgVectorStore(dsn=_DSN, dimension=_DIM, table=table, metric="cosine")
    s.ensure_schema()
    yield s
    import psycopg

    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()


@pytest.mark.integration
def test_ensure_schema_creates_and_idempotent(store):  # R15, R17
    """ensure_schema() created the table (via fixture); a 2nd call must not raise."""
    store.ensure_schema()  # second invocation -> idempotent (R15), uses migrations.sql (R17)


@pytest.mark.integration
def test_upsert_and_search_roundtrip(store):  # R12, R10, R18
    """upsert chunks+vectors, then similarity_search returns (Chunk, score) pairs."""
    chunks = [_chunk("near"), _chunk("far"), _chunk("opp")]
    vecs = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-1.0, 0.0, 0.0, 0.0],
    ]
    assert store.upsert(chunks, vecs) == 3
    results = store.similarity_search([1.0, 0.0, 0.0, 0.0], k=3)
    ids = [chunk.chunk_id for chunk, _ in results]
    assert ids == ["near", "far", "opp"]  # R10 cosine order, best first
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)  # R10 score descending
    top_chunk, _ = results[0]
    # R18: metadata survives the round-trip.
    assert top_chunk.source_url == "https://wowhead.example/near"
    assert top_chunk.title == "Title near"
    assert top_chunk.section == "Section near"


@pytest.mark.integration
def test_upsert_replaces_existing_chunk_id(store):  # R8
    """Re-upserting the same chunk_id replaces the row, never duplicates it."""
    store.upsert([_chunk("dup", text="first")], [[1.0, 0.0, 0.0, 0.0]])
    store.upsert([_chunk("dup", text="second")], [[0.0, 1.0, 0.0, 0.0]])
    results = store.similarity_search([0.0, 1.0, 0.0, 0.0], k=10)
    assert len(results) == 1
    chunk, _ = results[0]
    assert chunk.chunk_id == "dup"
    assert chunk.text == "second"  # last write wins


@pytest.mark.integration
def test_vector_column_uses_embedding_dim(store):  # R16
    """The migrated vector column dimension equals the configured embedding_dim."""
    import psycopg

    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = %s::regclass AND attname = 'embedding'",
                (store._table,),
            )
            (typmod,) = cur.fetchone()
    # pgvector stores the declared dimension directly in atttypmod.
    assert typmod == _DIM


@pytest.mark.integration
def test_bad_dsn_raises_vector_store_error():  # R25
    """An unreachable Postgres / invalid DSN surfaces as VectorStoreError."""
    bad = PgVectorStore(
        dsn="postgresql://nouser:nopass@127.0.0.1:1/nodb",
        dimension=_DIM,
    )
    with pytest.raises(VectorStoreError):
        bad.ensure_schema()
