"""Ingest layer — corpus loading and (future) chunking.

Public API for the ingest layer.  Consumers should depend on the
``CorpusLoader`` interface, not on ``JsonlCorpusLoader`` directly.
The concrete implementation is selected at the single composition point
(factory / config).
"""

from wowrag.ingest.base import (
    CorpusError,
    CorpusLoader,
    CorpusNotFoundError,
    MalformedCorpusError,
)
from wowrag.ingest.chunking import Chunker, ChunkingError, OverlapChunker
from wowrag.ingest.loader import JsonlCorpusLoader

__all__ = [
    "CorpusLoader",
    "JsonlCorpusLoader",
    "CorpusError",
    "CorpusNotFoundError",
    "MalformedCorpusError",
    "Chunker",
    "ChunkingError",
    "OverlapChunker",
]
