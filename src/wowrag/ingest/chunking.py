"""Chunking interface and overlap-based implementation.

This module defines:
- ``ChunkingError`` — domain exception for invalid chunker parameters.
- ``Chunker``       — Protocol (swap point) for any chunking strategy.
- ``OverlapChunker``— Concrete implementation: sliding window by characters.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from wowrag.models import Chunk, Document


class ChunkingError(Exception):
    """Raised when chunking parameters are invalid (e.g. overlap >= size)."""


class Chunker(Protocol):
    """Swap point: divide un Document en una lista ordenada de Chunk.

    Any object that implements ``chunk(document: Document) -> list[Chunk]``
    satisfies this protocol.  Consumers depend on this interface, not on
    ``OverlapChunker`` directly.
    """

    def chunk(self, document: Document) -> list[Chunk]:  # pragma: no cover
        ...


class OverlapChunker:
    """Split por caracteres con ventana deslizante y solapamiento fijo.

    Parameters
    ----------
    chunk_size : int
        Máximo de caracteres por chunk (must be > 0).
    chunk_overlap : int
        Caracteres de solapamiento entre chunks consecutivos
        (must satisfy 0 <= chunk_overlap < chunk_size).

    Raises
    ------
    ChunkingError
        Si ``chunk_overlap >= chunk_size``.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ChunkingError(
                f"chunk_overlap ({chunk_overlap}) must be < chunk_size ({chunk_size})"
            )
        self._size = chunk_size
        self._overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        """Divide *document* into an ordered list of overlapping ``Chunk`` objects.

        A document whose text is shorter than ``chunk_size`` produces exactly
        one chunk containing the full text (R12).  The union of all fragments
        covers the full original text with no gaps (R13).
        """
        text = document.text
        step = self._size - self._overlap
        chunks: list[Chunk] = []
        idx = 0
        start = 0
        # Ensure at least one iteration even for very short text.
        while True:
            fragment = text[start : start + self._size]
            if not fragment:
                break
            chunk_id = self._make_id(document, idx)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=fragment,
                    source_url=document.source_url,
                    title=document.title,
                    section=document.section,
                )
            )
            # Stop once this chunk covered the end of the text (no more content
            # beyond what we just emitted, so no new sliding-window position
            # would add new material).  This ensures text of length <= chunk_size
            # produces exactly 1 chunk (R12).
            if start + self._size >= len(text):
                break
            start += step
            idx += 1
        return chunks

    @staticmethod
    def _make_id(document: Document, index: int) -> str:
        """Compute a deterministic 16-hex-char chunk id.

        Formula: ``sha256(source_url + "|" + section + "|" + str(index))[:16]``

        Using only positional identity (not text content) keeps ids stable even
        if the text is lightly normalised between re-indexing runs.
        """
        key = f"{document.source_url}|{document.section}|{index}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
