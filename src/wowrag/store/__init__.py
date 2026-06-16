"""Store layer: vector-store interface, domain exception, fake and pgvector impl.

Consumers depend on this package, not on the internal modules (R33).

Re-exports the interface (``VectorStore``), the domain exception
(``VectorStoreError``), the in-memory ``FakeVectorStore`` and the real
``PgVectorStore``. The ``PgVectorStore`` driver import is lazy (in its
``__init__``), so this re-export stays importable without the Postgres driver
installed.
"""

from wowrag.store.base import VectorStore, VectorStoreError
from wowrag.store.fake import FakeVectorStore
from wowrag.store.pgvector_store import PgVectorStore

__all__ = [
    "VectorStore",
    "VectorStoreError",
    "FakeVectorStore",
    "PgVectorStore",
]
