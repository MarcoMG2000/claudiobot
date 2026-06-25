"""Tests for the f12 reranking layer.

Covers:
- PassthroughReranker (R5, R6, R7, R8, R26)
- FakeCrossEncoderReranker (R4, R13, R14, R15, R26)
- Integration of Reranker in DefaultRagOrchestrator (R19, R20, R21, R22, R23)
- RerankResult model (R3)
- Package exports (R28)
- CrossEncoderReranker with a real model (@integration, R9-R12, R25)

All unit tests are DB-free / GPU-free / network-free.
"""

from __future__ import annotations

import sys

import pytest

from wowrag.config import Settings
from wowrag.models import (
    BuiltPrompt,
    Chunk,
    RerankResult,
    RetrievalResult,
    RetrievedChunk,
    Source,
)
from wowrag.rag import DefaultRagOrchestrator
from wowrag.retrieval.reranker import (
    CrossEncoderReranker,
    FakeCrossEncoderReranker,
    PassthroughReranker,
    Reranker,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str = "c1", text: str = "Fireball deals fire damage.") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url="https://wowhead.com/fireball",
        title="Fireball - Spell",
        section="Description",
    )


def _make_retrieved_chunk(chunk_id: str, score: float = 0.9, text: str = "text") -> RetrievedChunk:
    return RetrievedChunk(chunk=_make_chunk(chunk_id=chunk_id, text=text), score=score)


def _three_chunks() -> list[RetrievedChunk]:
    """Three chunks in arbitrary order — used by most reranker tests."""
    return [
        _make_retrieved_chunk("c1", score=0.9, text="text-c1"),
        _make_retrieved_chunk("c2", score=0.7, text="text-c2"),
        _make_retrieved_chunk("c3", score=0.5, text="text-c3"),
    ]


def _settings(**kwargs) -> Settings:  # type: ignore[return]
    return Settings(_env_file=None, default_persona="simple", **kwargs)


# ---------------------------------------------------------------------------
# Stubs for orchestrator integration tests
# ---------------------------------------------------------------------------

class _StubRetriever:
    """Returns a fixed RetrievalResult."""

    def __init__(self, result: RetrievalResult) -> None:
        self._result = result

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        return self._result


class _SpyPromptBuilder:
    """PromptBuilder spy: records the RetrievalResult it received."""

    def __init__(self) -> None:
        self.received_result: RetrievalResult | None = None
        self._built = BuiltPrompt(
            system="SYS",
            user="USR",
            sources=[Source(n=1, title="T", url="https://wowhead.com/t")],
        )

    def build(self, query: str, result: RetrievalResult, persona=None) -> BuiltPrompt:
        self.received_result = result
        return self._built


class _StubLLM:
    model: str = "stub-llm"

    def generate(self, prompt: str) -> str:
        return "stub answer"


class _SpyReranker:
    """Reranker spy: records whether rerank was called."""

    def __init__(self) -> None:
        self.called = False
        self.call_args: tuple | None = None

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        self.called = True
        self.call_args = (query, chunks, top_n)
        return RerankResult(chunks=chunks, top_n=len(chunks), reranker_model="spy")


# ---------------------------------------------------------------------------
# PassthroughReranker tests
# ---------------------------------------------------------------------------

def test_passthrough_preserves_order():
    """R6: PassthroughReranker returns chunks in the same order as received."""
    chunks = _three_chunks()
    reranker = PassthroughReranker()
    result = reranker.rerank("fireball", chunks)
    assert [c.chunk.chunk_id for c in result.chunks] == ["c1", "c2", "c3"]


def test_passthrough_reranker_model_is_none():
    """R7: PassthroughReranker.rerank returns reranker_model=None."""
    chunks = _three_chunks()
    reranker = PassthroughReranker()
    result = reranker.rerank("fireball", chunks)
    assert result.reranker_model is None


def test_passthrough_truncates_to_top_n():
    """R8: with top_n=2 and 3 chunks, returns the 2 first in original order."""
    chunks = _three_chunks()
    reranker = PassthroughReranker()
    result = reranker.rerank("fireball", chunks, top_n=2)
    assert len(result.chunks) == 2
    assert result.top_n == 2
    assert [c.chunk.chunk_id for c in result.chunks] == ["c1", "c2"]


def test_passthrough_top_n_exceeds_chunks():
    """R5: with top_n=10 and 3 chunks, returns all 3 chunks (no padding)."""
    chunks = _three_chunks()
    reranker = PassthroughReranker()
    result = reranker.rerank("fireball", chunks, top_n=10)
    assert len(result.chunks) == 3
    assert result.top_n == 3


def test_passthrough_empty_chunks():
    """R26: empty chunks -> RerankResult(chunks=[], top_n=0, reranker_model=None)."""
    reranker = PassthroughReranker()
    result = reranker.rerank("fireball", [])
    assert result.chunks == []
    assert result.top_n == 0
    assert result.reranker_model is None


# ---------------------------------------------------------------------------
# FakeCrossEncoderReranker tests
# ---------------------------------------------------------------------------

def test_fake_reverses_order():
    """R13: FakeCrossEncoderReranker returns chunks in reversed order."""
    chunks = _three_chunks()
    reranker = FakeCrossEncoderReranker()
    result = reranker.rerank("fireball", chunks)
    assert [c.chunk.chunk_id for c in result.chunks] == ["c3", "c2", "c1"]


def test_fake_reranker_model_is_fake():
    """R15: FakeCrossEncoderReranker.rerank returns reranker_model='fake'."""
    chunks = _three_chunks()
    reranker = FakeCrossEncoderReranker()
    result = reranker.rerank("fireball", chunks)
    assert result.reranker_model == "fake"


def test_fake_truncates_to_top_n():
    """R4, R13: with top_n=2 and 3 chunks, returns 2 chunks from the reversed order."""
    chunks = _three_chunks()
    reranker = FakeCrossEncoderReranker()
    result = reranker.rerank("fireball", chunks, top_n=2)
    assert len(result.chunks) == 2
    assert result.top_n == 2
    # reversed order is [c3, c2, c1]; top 2 = [c3, c2]
    assert [c.chunk.chunk_id for c in result.chunks] == ["c3", "c2"]


def test_fake_no_ml_imports():
    """R14: importing FakeCrossEncoderReranker must not import sentence_transformers."""
    # sentence_transformers must not be in sys.modules after importing the reranker module
    # (the module was already imported above, so we check that the import path did NOT load it)
    assert "sentence_transformers" not in sys.modules, (
        "sentence_transformers was imported by FakeCrossEncoderReranker or its module, "
        "violating the zero-ML-dependency requirement (R14)"
    )


def test_fake_empty_chunks():
    """R26: empty chunks -> RerankResult(chunks=[], top_n=0, reranker_model='fake')."""
    reranker = FakeCrossEncoderReranker()
    result = reranker.rerank("fireball", [])
    assert result.chunks == []
    assert result.top_n == 0
    assert result.reranker_model == "fake"


# ---------------------------------------------------------------------------
# DefaultRagOrchestrator integration tests (reranker param)
# ---------------------------------------------------------------------------

def _make_retrieval_result(below_threshold: bool = False) -> RetrievalResult:
    chunks = _three_chunks()
    return RetrievalResult(
        chunks=chunks,
        max_score=chunks[0].score,
        below_threshold=below_threshold,
    )


def test_orchestrator_without_reranker_unchanged():
    """R22: no reranker -> PromptBuilder receives result.chunks in retriever order."""
    ret_result = _make_retrieval_result(below_threshold=False)
    retriever = _StubRetriever(ret_result)
    builder = _SpyPromptBuilder()
    llm = _StubLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    orch.answer("What is fireball?")

    assert builder.received_result is not None
    received_ids = [c.chunk.chunk_id for c in builder.received_result.chunks]
    assert received_ids == ["c1", "c2", "c3"]


def test_orchestrator_with_fake_reranker_uses_reranked_order():
    """R20: FakeCrossEncoderReranker + 3 chunks -> PromptBuilder receives reversed order."""
    ret_result = _make_retrieval_result(below_threshold=False)
    retriever = _StubRetriever(ret_result)
    builder = _SpyPromptBuilder()
    llm = _StubLLM()
    reranker = FakeCrossEncoderReranker()
    # reranker_top_n=3 so all chunks are passed (no truncation)
    orch = DefaultRagOrchestrator(
        retriever, builder, llm,
        settings=_settings(reranker_top_n=3),
        reranker=reranker,
    )

    orch.answer("What is fireball?")

    assert builder.received_result is not None
    received_ids = [c.chunk.chunk_id for c in builder.received_result.chunks]
    assert received_ids == ["c3", "c2", "c1"]


def test_orchestrator_reranker_not_called_on_abstention():
    """R21: below_threshold=True -> reranker.rerank must NOT be called."""
    ret_result = _make_retrieval_result(below_threshold=True)
    retriever = _StubRetriever(ret_result)
    builder = _SpyPromptBuilder()
    llm = _StubLLM()
    spy = _SpyReranker()
    orch = DefaultRagOrchestrator(
        retriever, builder, llm,
        settings=_settings(),
        reranker=spy,
    )

    orch.answer("obscure query")

    assert spy.called is False, "reranker.rerank must NOT be called when below_threshold=True (R21)"


def test_orchestrator_answer_contract_unchanged():
    """R23: with reranker active, Answer has exactly {answer, sources, abstained, metadata}."""
    ret_result = _make_retrieval_result(below_threshold=False)
    retriever = _StubRetriever(ret_result)
    builder = _SpyPromptBuilder()
    llm = _StubLLM()
    reranker = FakeCrossEncoderReranker()
    orch = DefaultRagOrchestrator(
        retriever, builder, llm,
        settings=_settings(reranker_top_n=3),
        reranker=reranker,
    )

    answer = orch.answer("query")

    # Exactly these four fields, no extras (R23)
    answer_fields = set(answer.model_fields_set | set(type(answer).model_fields.keys()))
    assert answer_fields == {"answer", "sources", "abstained", "metadata"}
    assert isinstance(answer.answer, str)
    assert isinstance(answer.sources, list)
    assert isinstance(answer.abstained, bool)
    assert answer.abstained is False


def test_orchestrator_reranker_top_n_passed():
    """R20: reranker.rerank is called with top_n=settings.reranker_top_n."""
    ret_result = _make_retrieval_result(below_threshold=False)
    retriever = _StubRetriever(ret_result)
    builder = _SpyPromptBuilder()
    llm = _StubLLM()
    spy = _SpyReranker()
    settings = _settings(reranker_top_n=2)
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=settings, reranker=spy)

    orch.answer("query")

    assert spy.called is True
    # call_args is (query, chunks, top_n)
    assert spy.call_args is not None
    _, _, top_n = spy.call_args
    assert top_n == 2, f"Expected top_n=2 (settings.reranker_top_n), got {top_n}"


# ---------------------------------------------------------------------------
# Model and export tests
# ---------------------------------------------------------------------------

def test_rerank_result_fields():
    """R3: RerankResult exposes chunks, top_n, reranker_model."""
    chunks = _three_chunks()[:2]
    result = RerankResult(chunks=chunks, top_n=2, reranker_model="test-model")
    assert result.chunks == chunks
    assert result.top_n == 2
    assert result.reranker_model == "test-model"


def test_exports_reranker_from_retrieval_package():
    """R28: from wowrag.retrieval import Reranker, PassthroughReranker, etc. works."""
    from wowrag.retrieval import (  # noqa: F401
        CrossEncoderReranker as CE,
        FakeCrossEncoderReranker as FCE,
        PassthroughReranker as PT,
        Reranker as R,
    )
    assert R is not None
    assert PT is not None
    assert CE is not None
    assert FCE is not None


def test_exports_rerank_result_from_models():
    """R28: from wowrag.models import RerankResult works."""
    from wowrag.models import RerankResult as RR  # noqa: F401

    assert RR is not None


# ---------------------------------------------------------------------------
# Integration test — CrossEncoderReranker with a real model
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_cross_encoder_reranks_correctly():
    """R9, R10, R11, R12, R25: CrossEncoderReranker with a real model reorders chunks.

    Requires sentence-transformers and the model to be downloaded.
    Skipped in CI via '-m not integration'.
    """
    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker = CrossEncoderReranker(model_name)  # R10

    query = "What does Fireball do?"
    chunks = [
        _make_retrieved_chunk("irrelevant", score=0.9, text="The weather in Stormwind is sunny."),
        _make_retrieved_chunk("relevant", score=0.7, text="Fireball is a fire spell that deals damage."),
        _make_retrieved_chunk("slightly-relevant", score=0.5, text="Mages can cast fire magic."),
    ]

    result = reranker.rerank(query, chunks, top_n=2)  # R9

    # top_n=2 -> exactly 2 chunks returned (R4)
    assert len(result.chunks) == 2

    # The most relevant chunk about Fireball should be first (R9)
    assert result.chunks[0].chunk.chunk_id == "relevant"

    # reranker_model matches model_name (R12)
    assert result.reranker_model == model_name

    # top_n field == len(chunks) returned (R3, R4)
    assert result.top_n == 2
