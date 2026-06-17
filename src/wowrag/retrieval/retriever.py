"""DefaultRetriever: composes EmbeddingProvider + VectorStore by dependency injection.

Depends only on interfaces (EmbeddingProvider, VectorStore). Testable with
FakeEmbeddingProvider (f3) + FakeVectorStore (f4). Zero DB/ML/network imports.
"""

from __future__ import annotations

from wowrag.config import Settings
from wowrag.embeddings.base import EmbeddingProvider
from wowrag.models import RetrievalResult, RetrievedChunk
from wowrag.retrieval.base import RetrieverError
from wowrag.store.base import VectorStore


class DefaultRetriever:
    """Retriever que compone un EmbeddingProvider y un VectorStore.

    Depende solo de las interfaces (R9): testeable con FakeEmbeddingProvider +
    FakeVectorStore, sin Postgres ni GPU.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._settings = settings or Settings()

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        """Recupera los top-k chunks para una query y computa la señal de abstención.

        Parameters
        ----------
        query:
            Texto de la consulta. Vacío o solo-espacios -> RetrieverError (R10).
        k:
            Número de resultados a devolver. None -> Settings.top_k (R16).
            Entero positivo -> usa ese k (R17). k <= 0 -> RetrieverError (R18).

        Returns
        -------
        RetrievalResult
            chunks (score desc), max_score, below_threshold.
            Store vacío -> chunks=[], max_score=0.0, below_threshold=True (R20).

        Raises
        ------
        RetrieverError
            Query vacía/solo-espacios (R10) o k no positivo (R18).
        EmbeddingError
            Propagada tal cual desde el EmbeddingProvider (R22).
        VectorStoreError
            Propagada tal cual desde el VectorStore (R22).
        """
        # R10: validar query ANTES de tocar embed/store.
        if not query or not query.strip():
            raise RetrieverError("query must be a non-empty string")

        # R16/R17: resolver k. Si None, usar Settings.top_k.
        resolved_k = self._settings.top_k if k is None else k

        # R18: k <= 0 -> error ANTES de tocar el store.
        if resolved_k <= 0:
            raise RetrieverError(f"k must be positive, got {resolved_k}")

        # R11: embed la query en exactamente un vector (lista de 1 elemento).
        # EmbeddingError propaga tal cual (R22).
        query_vector = self._embedder.embed([query])[0]

        # R12: búsqueda cruda -> pares (Chunk, float). VectorStoreError propaga (R22).
        hits = self._store.similarity_search(query_vector, resolved_k)

        # R12/R13/R15: envuelve cada par preservando orden score-desc y metadata.
        chunks = [RetrievedChunk(chunk=c, score=s) for c, s in hits]

        # R19: umbral desde Settings.
        threshold = self._settings.score_threshold

        # R5/R20: max_score = score del mejor chunk; 0.0 si store vacío.
        max_score = chunks[0].score if chunks else 0.0

        # R6/R7/R20: below_threshold usa < estricto (== no abstiene, R7).
        below_threshold = max_score < threshold

        return RetrievalResult(
            chunks=chunks,
            max_score=max_score,
            below_threshold=below_threshold,
        )
