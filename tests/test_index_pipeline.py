"""End-to-end unit tests for ``IndexingPipeline`` (Slice C).

Pure unit tests: no real DB, no torch, no ``@pytest.mark.integration``. The
pipeline is exercised with the project fakes / stubs only:
``JsonlCorpusLoader`` + ``OverlapChunker`` + ``FakeEmbeddingProvider`` +
``FakeVectorStore`` (and minimal Protocol stubs for R23).

Covers Slice C requirements:
- R20 — pipeline runs corpus -> load -> chunk -> embed -> upsert.
- R21 — ``ensure_schema`` is called before ``upsert``; ``index`` returns the
  total chunk count.
- R22 — M documents -> C chunks -> exactly C upserted entries (incl. empty edge).
- R23 — pipeline depends only on the interfaces, not concrete implementations.
"""

from __future__ import annotations

import json
from pathlib import Path

from wowrag.embeddings.fake import FakeEmbeddingProvider
from wowrag.index import IndexingPipeline
from wowrag.ingest.chunking import OverlapChunker
from wowrag.ingest.loader import JsonlCorpusLoader
from wowrag.models import Chunk, Document
from wowrag.store.fake import FakeVectorStore

_DIM = 16


def _write_corpus(corpus_dir: Path, docs: list[dict]) -> None:
    """Write *docs* as a single ``*.jsonl`` file inside *corpus_dir*."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(doc) for doc in docs)
    (corpus_dir / "corpus.jsonl").write_text(lines, encoding="utf-8")


def test_index_ingests_corpus_end_to_end(tmp_path):  # R20, R22
    """A real corpus is loaded, chunked, embedded and upserted; store ends up
    populated and searchable, and ``index`` returns the chunk count C."""
    corpus_dir = tmp_path / "corpus"
    # Two docs; chunk_size > each text length -> 1 chunk per doc (see f2 R12).
    docs = [
        {
            "text": "Fireball is a fire mage spell.",
            "source_url": "https://wowhead.example/fireball",
            "title": "Fireball",
            "section": "Spells",
        },
        {
            "text": "Frostbolt slows the target.",
            "source_url": "https://wowhead.example/frostbolt",
            "title": "Frostbolt",
            "section": "Spells",
        },
    ]
    _write_corpus(corpus_dir, docs)

    loader = JsonlCorpusLoader()
    chunker = OverlapChunker(chunk_size=512, chunk_overlap=64)
    embedder = FakeEmbeddingProvider(dimension=_DIM)
    store = FakeVectorStore(dimension=_DIM)
    pipeline = IndexingPipeline(loader, chunker, embedder, store)

    # Independently compute the expected chunk count from the same collaborators
    # so the assertion does not hard-code chunker behaviour.
    expected_chunks: list[Chunk] = []
    for doc in loader.load(corpus_dir):
        expected_chunks.extend(chunker.chunk(doc))
    expected_count = len(expected_chunks)
    assert expected_count >= len(docs)  # at least one chunk per document

    indexed = pipeline.index(corpus_dir)
    assert indexed == expected_count  # R22: returns total chunks indexed

    # R20: the store ends up populated and searchable with exactly C entries.
    query = embedder.embed(["Fireball is a fire mage spell."])[0]
    results = store.similarity_search(query, k=expected_count)
    assert len(results) == expected_count
    returned_ids = {chunk.chunk_id for chunk, _ in results}
    assert returned_ids == {chunk.chunk_id for chunk in expected_chunks}


class _OrderSpyStore:
    """Minimal ``VectorStore`` stub recording the order of method calls (R21)."""

    def __init__(self, dimension: int = _DIM) -> None:
        self._dimension = dimension
        self.calls: list[str] = []

    @property
    def dimension(self) -> int:
        return self._dimension

    def ensure_schema(self) -> None:
        self.calls.append("ensure_schema")

    def upsert(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> int:
        self.calls.append("upsert")
        return len(chunks)

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        self.calls.append("similarity_search")
        return []


def test_index_calls_ensure_schema_before_upsert(tmp_path):  # R21
    """``ensure_schema`` must run before the first ``upsert``."""
    corpus_dir = tmp_path / "corpus"
    _write_corpus(
        corpus_dir,
        [
            {
                "text": "Some indexable content.",
                "source_url": "https://wowhead.example/x",
                "title": "X",
                "section": "S",
            }
        ],
    )

    spy = _OrderSpyStore()
    pipeline = IndexingPipeline(
        JsonlCorpusLoader(),
        OverlapChunker(chunk_size=512, chunk_overlap=64),
        FakeEmbeddingProvider(dimension=_DIM),
        spy,
    )
    pipeline.index(corpus_dir)

    assert "ensure_schema" in spy.calls
    assert "upsert" in spy.calls
    assert spy.calls.index("ensure_schema") < spy.calls.index("upsert")


def test_index_empty_corpus_returns_zero(tmp_path):  # R22 (edge)
    """A corpus with no documents/chunks indexes nothing and returns 0."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)  # empty dir: no *.jsonl files

    store = FakeVectorStore(dimension=_DIM)
    pipeline = IndexingPipeline(
        JsonlCorpusLoader(),
        OverlapChunker(chunk_size=512, chunk_overlap=64),
        FakeEmbeddingProvider(dimension=_DIM),
        store,
    )

    assert pipeline.index(corpus_dir) == 0
    # Nothing was stored, and the empty store still searches without error.
    assert store.similarity_search([0.0] * _DIM, k=5) == []


# --- Pure Protocol stubs: prove the pipeline depends only on interfaces (R23) ---


class _StubLoader:
    """``CorpusLoader`` stub: returns a fixed document list, ignores the path."""

    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents

    def load(self, corpus_dir: str | Path) -> list[Document]:
        return list(self._documents)


class _StubChunker:
    """``Chunker`` stub: one chunk per document, no real splitting logic."""

    def chunk(self, document: Document) -> list[Chunk]:
        return [
            Chunk(
                chunk_id=f"stub-{document.source_url}",
                text=document.text,
                source_url=document.source_url,
                title=document.title,
                section=document.section,
            )
        ]


class _StubEmbedder:
    """``EmbeddingProvider`` stub: deterministic constant vectors."""

    def __init__(self, dimension: int = _DIM) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (self._dimension - 1) for _ in texts]


def test_pipeline_depends_only_on_interfaces():  # R23
    """The pipeline works with collaborators that ONLY satisfy the Protocols.

    No JsonlCorpusLoader/OverlapChunker/Fake* concrete classes here — just
    minimal stubs implementing the interfaces, plus FakeVectorStore as the store
    target. If the pipeline reached for any concrete behaviour, this would fail.
    """
    documents = [
        Document(
            text="Interface-only doc.",
            source_url="https://wowhead.example/iface",
            title="Iface",
            section="S",
        )
    ]
    store = FakeVectorStore(dimension=_DIM)
    pipeline = IndexingPipeline(
        _StubLoader(documents),
        _StubChunker(),
        _StubEmbedder(dimension=_DIM),
        store,
    )

    indexed = pipeline.index("ignored/path")
    assert indexed == 1
    results = store.similarity_search([1.0] + [0.0] * (_DIM - 1), k=5)
    assert len(results) == 1
    chunk, _ = results[0]
    assert chunk.chunk_id == "stub-https://wowhead.example/iface"
