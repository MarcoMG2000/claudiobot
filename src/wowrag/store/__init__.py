"""Store layer: vector-store interface, domain exception and in-memory fake.

Consumers depend on this package, not on the internal modules (R33).

Slice A ships the interface (``VectorStore``), the domain exception
(``VectorStoreError``) and the in-memory ``FakeVectorStore``. The real
``PgVectorStore`` re-export lands with Slice B (its module is added there); since
the driver import is lazy in ``PgVectorStore.__init__``, that re-export stays
importable without the Postgres driver installed.
"""

from wowrag.store.base import VectorStore, VectorStoreError
from wowrag.store.fake import FakeVectorStore

__all__ = [
    "VectorStore",
    "VectorStoreError",
    "FakeVectorStore",
]
