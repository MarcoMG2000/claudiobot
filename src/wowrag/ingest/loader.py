"""JSONL corpus loader — concrete implementation of ``CorpusLoader``.

Reads every ``*.jsonl`` file found in a directory (sorted for determinism),
parses each non-blank line as a JSON object and constructs a ``Document``
from it.

No network I/O is performed; only ``pathlib`` and the stdlib ``json`` module
are used (satisfies R11).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from wowrag.ingest.base import CorpusNotFoundError, MalformedCorpusError
from wowrag.models import Document

logger = logging.getLogger(__name__)


class JsonlCorpusLoader:
    """Reads every ``*.jsonl`` file in a directory; one Document per line.

    This is the concrete implementation of the ``CorpusLoader`` Protocol.
    It should be selected at the single composition point (factory / config)
    and the rest of the code should depend only on the ``CorpusLoader``
    interface.
    """

    def load(self, corpus_dir: str | Path) -> list[Document]:
        """Load all documents from JSONL files inside *corpus_dir*.

        Parameters
        ----------
        corpus_dir:
            Path to a directory containing ``*.jsonl`` corpus files.

        Returns
        -------
        list[Document]
            All documents parsed from all ``*.jsonl`` files, in sorted-file
            then line order.

        Raises
        ------
        CorpusNotFoundError
            If *corpus_dir* does not exist or is not a directory (R7).
        MalformedCorpusError
            If a non-blank line is not valid JSON or does not satisfy
            ``Document`` validation (R8).
        """
        root = Path(corpus_dir)
        if not root.is_dir():
            raise CorpusNotFoundError(
                f"corpus directory not found or not a directory: {root}"
            )

        docs: list[Document] = []
        for path in sorted(root.glob("*.jsonl")):
            logger.debug("loading corpus file %s", path)
            with path.open("r", encoding="utf-8") as fh:
                for lineno, raw in enumerate(fh, start=1):
                    if not raw.strip():
                        # R10: blank lines are silently ignored.
                        continue
                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise MalformedCorpusError(
                            f"{path}:{lineno}: invalid JSON — {exc}"
                        ) from exc
                    try:
                        docs.append(Document(**obj))
                    except (ValidationError, TypeError) as exc:
                        raise MalformedCorpusError(
                            f"{path}:{lineno}: document validation failed — {exc}"
                        ) from exc

        return docs
