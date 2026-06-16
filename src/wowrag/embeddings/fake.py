"""Deterministic, ML-free embedding provider for unit tests.

``FakeEmbeddingProvider`` derives each vector from the SHA-256 digest of the
text, so the same text always maps to the same vector across instances,
sessions and processes. It depends only on the standard library
(``hashlib`` + ``math``); no torch, FlagEmbedding or sentence-transformers.
"""

from __future__ import annotations

import hashlib
import math

from wowrag.embeddings.base import EmbeddingError


class FakeEmbeddingProvider:
    """Deterministic embedding provider for unit tests. Zero ML dependencies.

    Each text maps to a fixed unit-norm vector derived from SHA-256 of its
    UTF-8 encoding. Same text -> same vector across instances and sessions.
    """

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result: list[list[float]] = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise EmbeddingError(
                    f"Text at position {i} is empty or whitespace-only."
                )
            result.append(self._text_to_vector(text))
        return result

    def _text_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()  # 32 bytes
        # Tile the digest bytes to fill `dimension` floats, then normalize to
        # the unit sphere so vectors are cosine-similarity friendly (f4).
        raw = [(digest[j % 32] / 255.0) - 0.5 for j in range(self._dimension)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
