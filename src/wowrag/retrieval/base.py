"""Retriever interface and domain exception for the retrieval layer.

``Retriever`` is the swap point (Protocol) that all retriever implementations
must satisfy. The concrete implementation is ``DefaultRetriever``
(composes EmbeddingProvider + VectorStore). Domain exception ``RetrieverError``
covers input validation failures; infrastructure errors from the embedding/store
layers propagate as-is (R22).
"""

from __future__ import annotations

from typing import Protocol

from wowrag.models import RetrievalResult


class RetrieverError(Exception):
    """Domain exception for retriever input failures.

    Raised for an empty/whitespace query or a non-positive explicit k.
    Infrastructure errors from the embedding/store layers are NOT wrapped:
    they propagate as EmbeddingError / VectorStoreError (R22).
    """


class Retriever(Protocol):
    """Swap point: query -> embedding -> top-k -> RetrievalResult con señal.

    Implementación concreta: DefaultRetriever (compone EmbeddingProvider +
    VectorStore). Callers depend on this Protocol, never on a concrete impl.

    Contract
    --------
    - k=None -> uses Settings.top_k as default.
    - Empty/whitespace query -> raises RetrieverError (without calling embed/store).
    - k <= 0 -> raises RetrieverError (without calling the store).
    - Infrastructure errors (EmbeddingError, VectorStoreError) propagate as-is (R22).
    - Empty store -> RetrievalResult(chunks=[], max_score=0.0, below_threshold=True).
    """

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        """Recupera los top-k chunks para una query y computa la señal de abstención.

        k=None -> usa Settings.top_k. Query vacía o k<=0 -> RetrieverError.
        """
        ...
