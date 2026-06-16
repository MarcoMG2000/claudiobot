"""Vector-store interface and domain exception for the store layer.

``VectorStore`` is the swap point (Protocol) that all vector-store
implementations must satisfy. The concrete implementations are
``PgVectorStore`` (real, PostgreSQL + pgvector) and ``FakeVectorStore``
(in-memory, stdlib-only, for tests).

Search results are returned as ``list[tuple[Chunk, float]]`` — each element is a
``(chunk, score)`` pair using the existing ``Chunk`` model. The ``RetrievedChunk``
wrapper is deferred to f5; f4 exposes the minimal raw contract.
"""

from __future__ import annotations

from typing import Protocol

from wowrag.models import Chunk


class VectorStoreError(Exception):
    """Domain exception for vector-store failures.

    Raised for a missing DB driver, dimension mismatches, mismatched
    chunks/embeddings lengths, or connection failures.
    """


class VectorStore(Protocol):
    """Swap point: persists chunks+vectors+metadata and searches by similarity.

    Concrete implementations: ``PgVectorStore`` (real) and ``FakeVectorStore``
    (tests). Callers depend on this Protocol, never on a concrete
    implementation.
    """

    @property
    def dimension(self) -> int:
        """Expected dimensionality of the vectors this store accepts/returns.

        Read-only: implementations expose a property with no setter.
        """
        ...

    def ensure_schema(self) -> None:
        """Prepare the schema (table/column/index) idempotently.

        Must not fail if the schema already exists; a second invocation is a
        safe no-op.
        """
        ...

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        """Store chunks together with their vectors and metadata.

        Pairs the i-th chunk with the i-th vector (same order). Persists each
        chunk's ``chunk_id``, ``text``, ``source_url``, ``title`` and
        ``section`` so downstream citations survive. Upserts by ``chunk_id``:
        re-storing an existing ``chunk_id`` replaces it instead of duplicating.

        Returns
        -------
        int
            The number of rows inserted or updated.

        Raises
        ------
        VectorStoreError
            If ``len(chunks) != len(embeddings)``.
        """
        ...

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        """Return up to ``k`` most-similar ``(chunk, score)`` pairs.

        Uses cosine similarity; ``score`` is the cosine value where a higher
        value means more similar. The list is ordered by score descending (best
        first). An empty store returns ``[]`` without raising. A
        ``query_vector`` whose length does not match ``dimension`` raises
        ``VectorStoreError``.

        Returns
        -------
        list[tuple[Chunk, float]]
            One ``(Chunk, float)`` pair per result, best first.

        Raises
        ------
        VectorStoreError
            If ``len(query_vector) != dimension``.
        """
        ...
