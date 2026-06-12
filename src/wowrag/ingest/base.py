"""Corpus-loader interface and exception hierarchy for the ingest layer.

``CorpusLoader`` is the swap point (Protocol) that all corpus-loading
implementations must satisfy.  The exception hierarchy lets callers catch
the whole family via ``CorpusError`` or handle specific cases with the
subclasses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from wowrag.models import Document


class CorpusError(Exception):
    """Base error for corpus loading problems."""


class CorpusNotFoundError(CorpusError):
    """Raised when the corpus path is missing or not a directory.

    The exception message includes the offending path so callers can surface
    it clearly without inspecting the original exception attributes.
    """


class MalformedCorpusError(CorpusError):
    """Raised when a line cannot be parsed into a ``Document``.

    The exception message includes both the file path and the 1-based line
    number of the offending line.
    """


class CorpusLoader(Protocol):
    """Swap point: reads a local corpus directory into a list of Documents.

    Implementations must not perform any network I/O; they read only from the
    local filesystem (see R11).
    """

    def load(self, corpus_dir: str | Path) -> list[Document]:
        """Load all documents from *corpus_dir*.

        Parameters
        ----------
        corpus_dir:
            Path to a directory that contains the corpus files.

        Returns
        -------
        list[Document]
            All documents found in the directory, in a deterministic order.

        Raises
        ------
        CorpusNotFoundError
            If *corpus_dir* does not exist or is not a directory.
        MalformedCorpusError
            If a corpus entry cannot be parsed into a valid ``Document``.
        """
        ...
