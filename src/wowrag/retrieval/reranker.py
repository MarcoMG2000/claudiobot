"""Reranker interface and implementations for the wow-classic-rag pipeline (f12).

Provides a swap point between the Retriever and PromptBuilder layers:

    Reranker.rerank(query, chunks, top_n) -> RerankResult

Implementations
---------------
PassthroughReranker
    No-op: returns chunks in original order at zero cost (R6-R8).
    Default when reranker_enabled=False.
CrossEncoderReranker
    Uses a sentence-transformers CrossEncoder model for scoring (R9-R12, R26, R27).
    Requires ``requirements-ml.txt``. Lazy-loaded on first call (R11).
FakeCrossEncoderReranker
    Deterministic test double: reverses the chunk order (R13-R15).
    Zero ML dependencies — safe for unit tests without sentence-transformers.

Protocol contract (R1, R2):
- empty chunks -> RerankResult(chunks=[], top_n=0, reranker_model=...)
- top_n=None   -> return all chunks
- top_n > len  -> return all chunks (no padding)
- ML errors propagate as-is (R27)
"""

from __future__ import annotations

from typing import Protocol

from wowrag.models import RerankResult, RetrievedChunk


class Reranker(Protocol):
    """Swap point: (query, chunks, top_n) -> RerankResult.  (R1)

    All implementations must be constructible and invocable without ML
    dependencies, network, or Postgres (R2).

    Contract:
    - Empty chunks -> RerankResult(chunks=[], top_n=0, reranker_model=...).
    - top_n=None -> return all chunks.
    - top_n > len(chunks) -> return all chunks (no padding).
    - Infrastructure errors from the ML model propagate as-is (R27).
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        ...


class PassthroughReranker:
    """No-op reranker: returns chunks in their original order at zero cost.

    Used as the default when reranker_enabled=False (R6). Satisfies the
    Reranker Protocol (duck-typing). reranker_model=None signals that no
    scoring was performed (R7). Truncates to min(top_n, len(chunks)) (R8).
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        effective = chunks[:top_n] if top_n is not None else chunks  # R8, R5
        return RerankResult(
            chunks=effective,
            top_n=len(effective),
            reranker_model=None,  # R7
        )


class CrossEncoderReranker:
    """Reranker using a sentence-transformers CrossEncoder.

    Lazy-loads the model on first call (R11) so the module can be imported
    without triggering ML weight loading. Requires sentence-transformers
    (requirements-ml.txt). Infrastructure errors from the model propagate (R27).

    Parameters
    ----------
    model_name:
        Name of the cross-encoder model to load (R10).
        Default: "cross-encoder/ms-marco-MiniLM-L-6-v2".
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # lazy load (R11)

    def _get_model(self):  # type: ignore[return]
        if self._model is None:
            from sentence_transformers import CrossEncoder  # lazy import (R11)

            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        if not chunks:  # R26
            return RerankResult(
                chunks=[],
                top_n=0,
                reranker_model=self._model_name,
            )
        model = self._get_model()
        pairs = [(query, c.chunk.text) for c in chunks]
        scores = model.predict(pairs)  # may raise — propagates (R27)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        effective_n = min(top_n, len(chunks)) if top_n is not None else len(chunks)  # R5
        top_chunks = [c for _, c in ranked[:effective_n]]
        return RerankResult(
            chunks=top_chunks,
            top_n=len(top_chunks),
            reranker_model=self._model_name,  # R12
        )


class FakeCrossEncoderReranker:
    """Deterministic test double: reverses the chunk order.

    Inverts the retriever's score-desc order so tests can assert that the
    orchestrator respects the reranker's output, not the retriever's (R13).
    Zero ML dependencies (R14). reranker_model="fake" (R15).
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        reversed_chunks = list(reversed(chunks))  # R13
        effective_n = min(top_n, len(chunks)) if top_n is not None else len(chunks)  # R5
        result_chunks = reversed_chunks[:effective_n]
        return RerankResult(
            chunks=result_chunks,
            top_n=len(result_chunks),
            reranker_model="fake",  # R15
        )
