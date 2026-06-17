"""Retrieval layer: Retriever interface, domain exception, and DefaultRetriever.

Re-exports for R23: consumers import from this package, not from internal modules.
"""

from __future__ import annotations

from wowrag.retrieval.base import Retriever, RetrieverError
from wowrag.retrieval.retriever import DefaultRetriever

__all__ = ["Retriever", "RetrieverError", "DefaultRetriever"]
