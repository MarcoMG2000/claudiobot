"""Real ``VectorStore`` backed by PostgreSQL + pgvector (lazy driver import).

The ``psycopg`` / ``pgvector`` import happens **inside ``__init__``**, not at
module level, so this module is importable without the driver installed (R13).
The dependency is only enforced at construction time; a missing driver raises
``VectorStoreError`` with an install hint, never ``ImportError`` (R14). Mirrors
the lazy-import strategy of ``BgeM3Embeddings`` (f3).

Distance metric: pgvector's ``<=>`` is the cosine-distance operator. The returned
``score`` is ``1 - distance`` so that "higher == more similar" (R10); ordering by
distance ascending equals score descending (R9). The HNSW index uses
``vector_cosine_ops`` to match (see ``migrations.sql``).
"""

from __future__ import annotations

from pathlib import Path

from wowrag.models import Chunk
from wowrag.store.base import VectorStoreError

_MIGRATIONS = Path(__file__).with_name("migrations.sql")

# distance_metric (Settings) -> pgvector operator. cosine is the project default
# and the only metric consistent with f3's unit-norm vectors (design §13).
_METRIC_OPERATORS = {
    "cosine": "<=>",
    "l2": "<->",
    "inner_product": "<#>",
}


class PgVectorStore:
    """Real ``VectorStore`` backed by PostgreSQL + pgvector (R12).

    The ``psycopg``/``pgvector`` import is lazy (in ``__init__``) so the module
    is importable without the driver (R13); a missing driver raises
    ``VectorStoreError`` (R14). Callers depend on the ``VectorStore`` Protocol,
    not on this class.
    """

    def __init__(
        self,
        dsn: str,
        dimension: int,
        table: str = "chunks",
        metric: str = "cosine",
    ) -> None:
        try:
            import psycopg  # lazy import (R13)
            from pgvector.psycopg import register_vector
        except ImportError as exc:
            # R14: missing driver -> domain error with install hint, not ImportError.
            raise VectorStoreError(
                "Postgres driver not installed. "
                "Install store dependencies: pip install -r requirements-pg.txt"
            ) from exc

        if metric not in _METRIC_OPERATORS:
            raise VectorStoreError(
                f"unsupported distance_metric {metric!r}; "
                f"expected one of {sorted(_METRIC_OPERATORS)}"
            )

        self._dsn = dsn
        self._dimension = dimension
        self._table = table
        self._metric = metric
        self._operator = _METRIC_OPERATORS[metric]
        self._psycopg = psycopg
        self._register_vector = register_vector

    @property
    def dimension(self) -> int:
        # R16: embedding_dim (passed in) is the single source of truth.
        return self._dimension

    def _connect(self):
        try:
            conn = self._psycopg.connect(self._dsn)
        except Exception as exc:  # R25: connection failure -> domain error.
            raise VectorStoreError(f"Postgres connection failed: {exc}") from exc
        self._register_vector(conn)
        return conn

    def ensure_schema(self) -> None:
        # R17: DDL lives in migrations.sql, parametrized by {table}/{dim}.
        # R15/R16: idempotent (CREATE ... IF NOT EXISTS), column is vector({dim}).
        ddl = _MIGRATIONS.read_text(encoding="utf-8").format(
            table=self._table, dim=self._dimension
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            # R7: mismatched lengths -> domain error, no partial storage.
            raise VectorStoreError(
                f"len(chunks)={len(chunks)} != len(embeddings)={len(embeddings)}"
            )
        if not chunks:
            return 0
        # R8: upsert by chunk_id (PRIMARY KEY) -> ON CONFLICT DO UPDATE.
        # R18: persist chunk_id, text, source_url, title, section + embedding.
        # Values always travel as psycopg parameters, never interpolated.
        sql = (
            f"INSERT INTO {self._table} "
            "(chunk_id, text, source_url, title, section, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (chunk_id) DO UPDATE SET "
            "text = EXCLUDED.text, "
            "source_url = EXCLUDED.source_url, "
            "title = EXCLUDED.title, "
            "section = EXCLUDED.section, "
            "embedding = EXCLUDED.embedding"
        )
        params = [
            (
                chunk.chunk_id,
                chunk.text,
                chunk.source_url,
                chunk.title,
                chunk.section,
                list(vec),
            )
            for chunk, vec in zip(chunks, embeddings)
        ]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, params)
            conn.commit()
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
        # R10: 1 - cosine_distance -> higher == more similar.
        # R9: ORDER BY distance ascending == score descending.
        # R18: select metadata so each returned Chunk carries it.
        sql = (
            "SELECT chunk_id, text, source_url, title, section, "
            f"1 - (embedding {self._operator} %s) AS score "
            f"FROM {self._table} "
            f"ORDER BY embedding {self._operator} %s "
            "LIMIT %s"
        )
        vec = list(query_vector)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (vec, vec, k))
                rows = cur.fetchall()
        results: list[tuple[Chunk, float]] = []
        for chunk_id, text, source_url, title, section, score in rows:
            chunk = Chunk(
                chunk_id=chunk_id,
                text=text,
                source_url=source_url,
                title=title,
                section=section,
            )
            results.append((chunk, float(score)))
        return results  # R11: empty store -> [] (no rows fetched)
