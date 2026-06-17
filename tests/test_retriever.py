"""Tests for DefaultRetriever using FakeEmbeddingProvider + FakeVectorStore (f5).

Trazabilidad: R6, R7, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R20, R22, R23.
All tests are DB-free / GPU-free / network-free.
"""

from __future__ import annotations

import pytest

from wowrag.config import Settings
from wowrag.embeddings.base import EmbeddingError
from wowrag.embeddings.fake import FakeEmbeddingProvider
from wowrag.models import Chunk
from wowrag.retrieval import DefaultRetriever, Retriever, RetrieverError
from wowrag.store.base import VectorStoreError
from wowrag.store.fake import FakeVectorStore


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str,
    text: str = "Some spell description.",
    source_url: str = "https://www.wowhead.com/classic/spell=1/test",
    title: str = "Test Spell",
    section: str = "Overview",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=source_url,
        title=title,
        section=section,
    )


def _settings(top_k: int = 5, score_threshold: float = 0.30) -> Settings:
    """Return a Settings with no .env file and explicit values."""
    return Settings(
        _env_file=None,
        top_k=top_k,
        score_threshold=score_threshold,
    )


def _populated_retriever(
    *,
    top_k: int = 5,
    score_threshold: float = 0.30,
    num_chunks: int = 3,
) -> tuple[DefaultRetriever, FakeEmbeddingProvider, FakeVectorStore]:
    """Build a DefaultRetriever with pre-populated fake store."""
    dim = 16
    embedder = FakeEmbeddingProvider(dimension=dim)
    store = FakeVectorStore(dimension=dim)
    settings = _settings(top_k=top_k, score_threshold=score_threshold)

    chunks = [
        _make_chunk(
            chunk_id=f"c{i}",
            text=f"Chunk text number {i} about spells.",
            source_url=f"https://wowhead.com/{i}",
            title=f"Spell {i}",
            section=f"Section {i}",
        )
        for i in range(num_chunks)
    ]
    embeddings = embedder.embed([c.text for c in chunks])
    store.upsert(chunks, embeddings)

    retriever = DefaultRetriever(embedder=embedder, store=store, settings=settings)
    return retriever, embedder, store


# ---------------------------------------------------------------------------
# R10 — empty / whitespace query raises RetrieverError
# ---------------------------------------------------------------------------

class _SpyEmbedder:
    """Minimal embedder that records whether embed() was called."""

    def __init__(self) -> None:
        self.embed_called = False
        self._dim = 16

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_called = True
        return [[0.0] * self._dim for _ in texts]


class _SpyStore:
    """Minimal store that records whether similarity_search() was called."""

    def __init__(self) -> None:
        self.search_called = False
        self._dim = 16

    @property
    def dimension(self) -> int:
        return self._dim

    def ensure_schema(self) -> None:
        pass

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        return 0

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        self.search_called = True
        return []


@pytest.mark.parametrize("bad_query", ["", "   ", "\t", "\n"])
def test_empty_query_raises(bad_query: str):
    """R10: empty or whitespace-only query raises RetrieverError without calling embed/store."""
    spy_embedder = _SpyEmbedder()
    spy_store = _SpyStore()
    retriever = DefaultRetriever(
        embedder=spy_embedder,
        store=spy_store,
        settings=_settings(),
    )

    with pytest.raises(RetrieverError):
        retriever.retrieve(bad_query)

    assert not spy_embedder.embed_called, "embed must NOT be called for empty query"
    assert not spy_store.search_called, "store must NOT be called for empty query"


# ---------------------------------------------------------------------------
# R11 — embed is called with a list of exactly one element
# ---------------------------------------------------------------------------

class _RecordingEmbedder:
    """Embedder that records the call arguments for inspection."""

    def __init__(self, inner: FakeEmbeddingProvider) -> None:
        self._inner = inner
        self.last_texts: list[str] = []

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.last_texts = list(texts)
        return self._inner.embed(texts)


def test_embeds_query_as_single_vector():
    """R11: embed is called with a list of exactly 1 element."""
    dim = 16
    inner = FakeEmbeddingProvider(dimension=dim)
    recording_embedder = _RecordingEmbedder(inner)
    store = FakeVectorStore(dimension=dim)
    retriever = DefaultRetriever(
        embedder=recording_embedder,
        store=store,
        settings=_settings(),
    )

    retriever.retrieve("What is Fireball?")

    assert len(recording_embedder.last_texts) == 1
    assert recording_embedder.last_texts[0] == "What is Fireball?"


# ---------------------------------------------------------------------------
# R12, R13 — results are RetrievedChunk wrappers, order preserved (score desc)
# ---------------------------------------------------------------------------

def test_wraps_pairs_into_retrieved_chunks():
    """R12/R13: each (Chunk, float) pair is wrapped into RetrievedChunk; score-desc order."""
    retriever, _, _ = _populated_retriever(num_chunks=3)
    result = retriever.retrieve("spells")

    assert len(result.chunks) > 0
    for rc in result.chunks:
        assert hasattr(rc, "chunk")
        assert hasattr(rc, "score")

    # Verify score-descending order (R13).
    scores = [rc.score for rc in result.chunks]
    assert scores == sorted(scores, reverse=True), "chunks must be score-desc"


# ---------------------------------------------------------------------------
# R14 — at most k results returned
# ---------------------------------------------------------------------------

def test_respects_k_limit():
    """R14: with M > k rows in the store, retrieve(q, k) returns <= k chunks."""
    retriever, _, _ = _populated_retriever(num_chunks=5, top_k=5)
    result = retriever.retrieve("spells", k=2)

    assert len(result.chunks) <= 2


# ---------------------------------------------------------------------------
# R15 — metadata is preserved in results
# ---------------------------------------------------------------------------

def test_results_carry_metadata():
    """R15: each RetrievedChunk carries source_url, title, section from the Chunk."""
    retriever, _, _ = _populated_retriever(num_chunks=3)
    result = retriever.retrieve("spells")

    for rc in result.chunks:
        assert rc.source_url == rc.chunk.source_url
        assert rc.title == rc.chunk.title
        assert rc.section == rc.chunk.section
        # Verify non-empty (our helper uses real values).
        assert rc.source_url.startswith("https://")
        assert rc.title
        assert rc.section


# ---------------------------------------------------------------------------
# R16 — k=None uses Settings.top_k
# ---------------------------------------------------------------------------

def test_k_none_uses_top_k():
    """R16: retrieve(q) with no k argument uses Settings.top_k."""
    dim = 16
    embedder = FakeEmbeddingProvider(dimension=dim)
    store = FakeVectorStore(dimension=dim)
    # Insert 6 chunks.
    chunks = [_make_chunk(chunk_id=f"d{i}", text=f"Desc {i}") for i in range(6)]
    embeddings = embedder.embed([c.text for c in chunks])
    store.upsert(chunks, embeddings)

    settings = _settings(top_k=3)
    retriever = DefaultRetriever(embedder=embedder, store=store, settings=settings)

    result = retriever.retrieve("Desc")

    assert len(result.chunks) <= 3


# ---------------------------------------------------------------------------
# R17 — explicit k overrides Settings.top_k
# ---------------------------------------------------------------------------

def test_explicit_k_overrides_top_k():
    """R17: retrieve(q, k=2) uses 2, ignoring Settings.top_k."""
    dim = 16
    embedder = FakeEmbeddingProvider(dimension=dim)
    store = FakeVectorStore(dimension=dim)
    chunks = [_make_chunk(chunk_id=f"e{i}", text=f"Entry {i}") for i in range(5)]
    embeddings = embedder.embed([c.text for c in chunks])
    store.upsert(chunks, embeddings)

    settings = _settings(top_k=10)  # top_k is large
    retriever = DefaultRetriever(embedder=embedder, store=store, settings=settings)

    result = retriever.retrieve("Entry", k=2)

    assert len(result.chunks) <= 2


# ---------------------------------------------------------------------------
# R18 — k <= 0 raises RetrieverError without touching the store
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_k", [0, -1, -100])
def test_non_positive_k_raises(bad_k: int):
    """R18: retrieve(q, k<=0) raises RetrieverError without calling the store."""
    spy_store = _SpyStore()
    embedder = FakeEmbeddingProvider(dimension=16)
    retriever = DefaultRetriever(
        embedder=embedder,
        store=spy_store,
        settings=_settings(),
    )

    with pytest.raises(RetrieverError):
        retriever.retrieve("valid query", k=bad_k)

    assert not spy_store.search_called, "store must NOT be called for k<=0"


# ---------------------------------------------------------------------------
# R6, R19 — below_threshold=True when max_score < score_threshold
# ---------------------------------------------------------------------------

def test_below_threshold_true_when_max_score_low():
    """R6/R19: below_threshold is True when max_score < score_threshold."""
    # Use a very high threshold so any real score is below it.
    retriever, _, _ = _populated_retriever(score_threshold=0.9999)
    result = retriever.retrieve("spells")

    assert result.below_threshold is True


# ---------------------------------------------------------------------------
# R7 — below_threshold=False when max_score >= score_threshold (strict <)
# ---------------------------------------------------------------------------

def test_below_threshold_false_when_max_score_high():
    """R7: below_threshold is False when max_score >= score_threshold; == does NOT abstain."""
    # Use a threshold of 0.0 so any cosine score will be >= threshold.
    retriever, _, _ = _populated_retriever(score_threshold=0.0)
    result = retriever.retrieve("spells")

    assert result.below_threshold is False


def test_below_threshold_equal_does_not_abstain():
    """R7: the boundary case max_score == score_threshold => below_threshold is False."""
    dim = 16
    embedder = FakeEmbeddingProvider(dimension=dim)
    store = FakeVectorStore(dimension=dim)

    # Use the same text for query and stored chunk so cosine score == 1.0.
    query_text = "exact match query"
    chunk = _make_chunk(chunk_id="exact", text=query_text)
    store.upsert([chunk], embedder.embed([query_text]))

    # Set threshold exactly at 1.0 — score==1.0 should NOT abstain (< strict).
    settings = _settings(score_threshold=1.0)
    retriever = DefaultRetriever(embedder=embedder, store=store, settings=settings)
    result = retriever.retrieve(query_text)

    # max_score should be 1.0 (or very close to 1.0 due to unit vectors).
    # With threshold == 1.0: 1.0 < 1.0 is False => below_threshold = False.
    assert result.below_threshold is False


# ---------------------------------------------------------------------------
# R20 — empty store signals abstention (no exception)
# ---------------------------------------------------------------------------

def test_empty_store_signals_abstention():
    """R20: empty store returns chunks=[], max_score=0.0, below_threshold=True without exception."""
    embedder = FakeEmbeddingProvider(dimension=16)
    store = FakeVectorStore(dimension=16)  # no upsert
    retriever = DefaultRetriever(
        embedder=embedder,
        store=store,
        settings=_settings(score_threshold=0.30),
    )

    result = retriever.retrieve("What is Fireball?")

    assert result.chunks == []
    assert result.max_score == 0.0
    assert result.below_threshold is True


# ---------------------------------------------------------------------------
# R22 — infrastructure errors propagate, not masked as empty result
# ---------------------------------------------------------------------------

class _ErrorEmbedder:
    """Embedder that always raises EmbeddingError."""

    @property
    def dimension(self) -> int:
        return 16

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("simulated embedding failure")


class _ErrorStore:
    """Store that always raises VectorStoreError on search."""

    @property
    def dimension(self) -> int:
        return 16

    def ensure_schema(self) -> None:
        pass

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        return 0

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        raise VectorStoreError("simulated store failure")


def test_infra_errors_propagate_embedder():
    """R22: EmbeddingError from embedder propagates; not masked as empty result."""
    retriever = DefaultRetriever(
        embedder=_ErrorEmbedder(),
        store=FakeVectorStore(dimension=16),
        settings=_settings(),
    )

    with pytest.raises(EmbeddingError):
        retriever.retrieve("valid query")


def test_infra_errors_propagate_store():
    """R22: VectorStoreError from store propagates; not masked as empty result."""
    embedder = FakeEmbeddingProvider(dimension=16)
    retriever = DefaultRetriever(
        embedder=embedder,
        store=_ErrorStore(),
        settings=_settings(),
    )

    with pytest.raises(VectorStoreError):
        retriever.retrieve("valid query")


# ---------------------------------------------------------------------------
# R9 — DefaultRetriever depends only on Protocol interfaces
# ---------------------------------------------------------------------------

def test_retriever_depends_only_on_interfaces():
    """R9: DefaultRetriever is constructible/runnable with any EmbeddingProvider+VectorStore duck-types."""
    # _SpyEmbedder and _SpyStore implement only the Protocol interface (duck-typing).
    spy_embedder = _SpyEmbedder()
    spy_store = _SpyStore()
    retriever = DefaultRetriever(
        embedder=spy_embedder,
        store=spy_store,
        settings=_settings(),
    )

    # Should not raise — just returns an empty result from the spy store.
    result = retriever.retrieve("spell query")
    assert result.chunks == []
    assert result.below_threshold is True


# ---------------------------------------------------------------------------
# R23 — exports from wowrag.retrieval package
# ---------------------------------------------------------------------------

def test_exports_from_package():
    """R23: from wowrag.retrieval import Retriever, RetrieverError, DefaultRetriever works."""
    # The imports at module top already exercise this.
    # Verify types are accessible and correct.
    assert Retriever is not None
    assert RetrieverError is not None
    assert DefaultRetriever is not None

    # Verify RetrieverError is an Exception subclass (R21).
    assert issubclass(RetrieverError, Exception)

    # Verify DefaultRetriever is a class with retrieve method.
    assert hasattr(DefaultRetriever, "retrieve")
