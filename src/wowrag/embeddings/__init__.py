"""Embeddings layer: provider interface, fake (tests) and bge-m3 (real).

Consumers depend on this package, not on the internal modules.
"""

from wowrag.embeddings.base import EmbeddingError, EmbeddingProvider
from wowrag.embeddings.bge_m3 import BgeM3Embeddings
from wowrag.embeddings.fake import FakeEmbeddingProvider

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "BgeM3Embeddings",
]
