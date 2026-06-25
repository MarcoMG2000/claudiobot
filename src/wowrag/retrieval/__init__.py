"""Retrieval layer: Retriever interface, domain exception, DefaultRetriever, and Reranker.

Re-exports for R23 (f5) and R28 (f12): consumers import from this package,
not from internal modules.
"""

from __future__ import annotations

from wowrag.retrieval.base import Retriever, RetrieverError
from wowrag.retrieval.reranker import (
    CrossEncoderReranker,
    FakeCrossEncoderReranker,
    PassthroughReranker,
    Reranker,
)
from wowrag.retrieval.retriever import DefaultRetriever

__all__ = [
    "Retriever",
    "RetrieverError",
    "DefaultRetriever",
    "Reranker",              # f12 (R28)
    "PassthroughReranker",   # f12 (R28)
    "CrossEncoderReranker",  # f12 (R28)
    "FakeCrossEncoderReranker",  # f12 (R28)
]
