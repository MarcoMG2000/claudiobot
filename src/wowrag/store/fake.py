"""In-memory, stdlib-only vector store for unit tests.

``FakeVectorStore`` keeps chunks and vectors in a plain ``dict`` and computes
cosine similarity with ``math`` only — no ``psycopg``, ``pgvector`` or any
network/DB library. It mirrors the cosine/top-k semantics of ``PgVectorStore``
so it can power every unit test of f4 (and later f5) without Postgres.
"""

from __future__ import annotations

import math

from wowrag.models import Chunk
from wowrag.store.base import VectorStoreError


class FakeVectorStore:
    """In-memory ``VectorStore`` for unit tests. Zero DB dependencies.

    Cosine similarity over stored vectors, same semantics as ``PgVectorStore``.
    Upsert is keyed by ``chunk_id`` so re-storing an id replaces the entry.
    """

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension
        # chunk_id -> (Chunk, vector)
        self._rows: dict[str, tuple[Chunk, list[float]]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    def ensure_schema(self) -> None:
        # R29: in-memory store has no schema to migrate; safe idempotent no-op.
        return None

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            # R7: mismatched lengths -> domain error, no partial storage.
            raise VectorStoreError(
                f"len(chunks)={len(chunks)} != len(embeddings)={len(embeddings)}"
            )
        for chunk, vec in zip(chunks, embeddings):
            # R8/R28: keyed by chunk_id -> re-store replaces, never duplicates.
            # R18: the whole Chunk (with metadata) is retained.
            self._rows[chunk.chunk_id] = (chunk, list(vec))
        return len(chunks)  # R6

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        if len(query_vector) != self._dimension:
            # R19: wrong query dimension -> domain error naming expected/received.
            raise VectorStoreError(
                f"query_vector dimension {len(query_vector)} "
                f"!= expected {self._dimension}"
            )
        if not self._rows:
            return []  # R11: empty store -> empty list, no exception.
        scored = [
            (self._cosine(query_vector, vec), chunk)
            for chunk, vec in self._rows.values()
        ]
        # R9/R10/R27: cosine, ordered by score descending (best first).
        scored.sort(key=lambda t: t[0], reverse=True)
        return [(chunk, score) for score, chunk in scored[:k]]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)
