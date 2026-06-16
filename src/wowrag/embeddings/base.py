"""Embedding-provider interface and domain exception for the embeddings layer.

``EmbeddingProvider`` is the swap point (Protocol) that all embedding
implementations must satisfy. The concrete implementations are
``BgeM3Embeddings`` (real, bge-m3 via FlagEmbedding) and
``FakeEmbeddingProvider`` (deterministic, ML-free, for tests).
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingError(Exception):
    """Domain exception for embedding failures.

    Raised for missing ML dependencies, invalid input (empty/whitespace text),
    or unavailable devices (e.g. ``cuda`` requested but no GPU present).
    """


class EmbeddingProvider(Protocol):
    """Swap point: converts texts into fixed-dimension vectors.

    Concrete implementations: ``BgeM3Embeddings`` (real) and
    ``FakeEmbeddingProvider`` (tests). Callers depend on this Protocol, never
    on a concrete implementation.
    """

    @property
    def dimension(self) -> int:
        """Fixed dimensionality of this provider's embedding space.

        Read-only: implementations expose a property with no setter.
        """
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Parameters
        ----------
        texts:
            Non-empty strings to embed. An empty list returns ``[]``.
            Empty or whitespace-only strings raise ``EmbeddingError``.

        Returns
        -------
        list[list[float]]
            One vector per input text, each with exactly ``dimension``
            elements of type ``float``, in the same order as the input.

        Raises
        ------
        EmbeddingError
            If any text is empty/whitespace-only, or if the backend fails.
        """
        ...
