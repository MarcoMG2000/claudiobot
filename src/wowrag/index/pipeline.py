"""End-to-end offline indexing pipeline.

``IndexingPipeline`` orchestrates the offline indexing flow
``corpus -> load -> chunk -> embed -> upsert``. It is composed exclusively from
the layer interfaces (``CorpusLoader``, ``Chunker``, ``EmbeddingProvider`` and
``VectorStore``), so it runs end-to-end in tests with fakes — no Postgres, no
GPU. This module lives in its own ``index/`` package (not ``ingest/`` or
``rag/``) because it composes several layers in an offline flow; see
``design.md`` §8.
"""

from __future__ import annotations

from pathlib import Path

from wowrag.embeddings.base import EmbeddingProvider
from wowrag.ingest.base import CorpusLoader
from wowrag.ingest.chunking import Chunker
from wowrag.models import Chunk
from wowrag.store.base import VectorStore


class IndexingPipeline:
    """Offline indexing flow: ``corpus -> load -> chunk -> embed -> upsert``.

    Depends only on interfaces (R23), so it is testable end-to-end with fakes
    without Postgres or a GPU. The collaborators are injected via their Protocol
    types at construction time (dependency injection).
    """

    def __init__(
        self,
        loader: CorpusLoader,
        chunker: Chunker,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ) -> None:
        # R20/R23: collaborators are injected as Protocol interfaces, never
        # concrete implementations.
        self._loader = loader
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    def index(self, corpus_dir: str | Path) -> int:
        """Index *corpus_dir* end-to-end and return the chunk count.

        Runs the full flow: ensure the store schema, load the corpus into
        documents, chunk every document, embed the chunk texts, and upsert the
        chunks with their vectors. Returns the total number of chunks indexed
        (``0`` when the corpus yields no chunks).

        Parameters
        ----------
        corpus_dir:
            Path to the corpus directory handed to the ``CorpusLoader``.

        Returns
        -------
        int
            Total number of chunks indexed (R21, R22).
        """
        # R21: ensure the schema is in place BEFORE any upsert.
        self._store.ensure_schema()

        documents = self._loader.load(corpus_dir)
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self._chunker.chunk(document))

        # R22 (edge): an empty corpus produces zero chunks; skip the embed/upsert
        # round-trip entirely and report 0.
        if not chunks:
            return 0

        embeddings = self._embedder.embed([chunk.text for chunk in chunks])
        # R22: exactly C chunks embedded -> exactly C entries upserted.
        self._store.upsert(chunks, embeddings)
        return len(chunks)
