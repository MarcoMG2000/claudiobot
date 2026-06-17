"""Tests for DefaultRagOrchestrator (f8-rag-orchestrator).

Two dependency styles, both DB-free / GPU-free / network-free:
- stubs/spies of Retriever/PromptBuilder + FakeLLMProvider (f7) to isolate the
  orchestrator and verify the short-circuit by spying on the deps;
- the real f5/f6 impls fed by FakeEmbeddingProvider/FakeVectorStore + a real
  persona YAML, for the empty-store composition case.

Trazabilidad: R2, R4, R5, R6, R7, R9, R10, R11, R12, R13, R14, R15, R16, R17,
R18, R19, R20, R21, R22, R23, R25, R26, R27.
"""

from __future__ import annotations

import pytest

from wowrag.config import Settings
from wowrag.embeddings.fake import FakeEmbeddingProvider
from wowrag.llm.base import LLMError
from wowrag.llm.fake import FakeLLMProvider
from wowrag.models import (
    Answer,
    BuiltPrompt,
    Chunk,
    RetrievalResult,
    RetrievedChunk,
    Source,
)
from wowrag.personas import Persona, load_persona
from wowrag.rag import DefaultRagOrchestrator, OrchestratorError, RagOrchestrator
from wowrag.retrieval.base import RetrieverError
from wowrag.store.fake import FakeVectorStore


# ---------------------------------------------------------------------------
# Helpers / stubs / spies
# ---------------------------------------------------------------------------

def _settings(score_threshold: float = 0.30, default_persona: str = "simple") -> Settings:
    """Settings with no .env file and explicit values."""
    return Settings(
        _env_file=None,
        score_threshold=score_threshold,
        default_persona=default_persona,
    )


def _make_chunk(chunk_id: str = "c1", text: str = "Fireball deals fire damage.") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url="https://wowhead.com/fireball",
        title="Fireball - Spell",
        section="Description",
    )


def _result(*, below_threshold: bool, scores: list[float]) -> RetrievalResult:
    chunks = [
        RetrievedChunk(chunk=_make_chunk(chunk_id=f"c{i}"), score=s)
        for i, s in enumerate(scores)
    ]
    max_score = chunks[0].score if chunks else 0.0
    return RetrievalResult(chunks=chunks, max_score=max_score, below_threshold=below_threshold)


class _StubRetriever:
    """Retriever stub: returns a fixed RetrievalResult; records calls."""

    def __init__(self, result: RetrievalResult) -> None:
        self._result = result
        self.retrieve_called = False
        self.last_query: str | None = None

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        self.retrieve_called = True
        self.last_query = query
        return self._result


class _SpyPromptBuilder:
    """PromptBuilder spy: returns a fixed BuiltPrompt; records call + persona received."""

    def __init__(self, built: BuiltPrompt | None = None) -> None:
        self._built = built or BuiltPrompt(
            system="SYSTEM-PROMPT-TEXT",
            user="USER-PROMPT-TEXT",
            sources=[Source(n=1, title="Fireball - Spell", url="https://wowhead.com/fireball")],
        )
        self.build_called = False
        self.received_persona: Persona | None = None

    def build(
        self,
        query: str,
        result: RetrievalResult,
        persona: Persona | None = None,
    ) -> BuiltPrompt:
        self.build_called = True
        self.received_persona = persona
        return self._built


class _SpyLLM:
    """LLMProvider spy: records prompts; returns a fixed text."""

    def __init__(self, model: str = "spy-llm", text: str = "GENERATED ANSWER") -> None:
        self._model = model
        self._text = text
        self.prompts: list[str] = []

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._text


class _ErrorRetriever:
    """Retriever stub that always raises RetrieverError."""

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        raise RetrieverError("simulated retriever failure")


class _ErrorLLM:
    """LLMProvider stub that always raises LLMError on generate."""

    @property
    def model(self) -> str:
        return "error-llm"

    def generate(self, prompt: str) -> str:
        raise LLMError("simulated LLM failure")


# ---------------------------------------------------------------------------
# R25 — empty / whitespace query raises OrchestratorError before touching deps
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_query", ["", "   ", "\t", "\n"])
def test_empty_query_raises(bad_query: str):
    """R25: empty/whitespace query -> OrchestratorError; retrieve/build/generate NOT called."""
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    with pytest.raises(OrchestratorError):
        orch.answer(bad_query)

    assert not retriever.retrieve_called, "retrieve must NOT be called for empty query"
    assert not builder.build_called, "build must NOT be called for empty query"
    assert llm.prompts == [], "generate must NOT be called for empty query"


# ---------------------------------------------------------------------------
# R2, R13, R19, R20 — happy path: grounded answer with citations
# ---------------------------------------------------------------------------

def test_happy_path_returns_answer_with_citations():
    """R2/R13/R19/R20: below_threshold=False -> abstained False, answer=LLM text, sources=BuiltPrompt.sources."""
    built = BuiltPrompt(
        system="SYS",
        user="USR",
        sources=[
            Source(n=1, title="Spell A", url="https://wowhead.com/a"),
            Source(n=2, title="Spell B", url="https://wowhead.com/b"),
        ],
    )
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9, 0.8]))
    builder = _SpyPromptBuilder(built=built)
    llm = _SpyLLM(text="The grounded answer [1][2]")
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("What is Fireball?")

    assert isinstance(answer, Answer)
    assert answer.abstained is False                       # R13
    assert answer.answer == "The grounded answer [1][2]"   # R2, R13
    assert answer.sources == built.sources                 # R19, R20
    assert len(answer.sources) >= 1                         # R19


# ---------------------------------------------------------------------------
# R12 — generate is called exactly once with combined system+user prompt
# ---------------------------------------------------------------------------

def test_generate_called_once_with_combined_prompt():
    """R12: generate gets one string containing built.system AND built.user, called once."""
    built = BuiltPrompt(
        system="SYSTEM-MARKER-XYZ",
        user="USER-MARKER-ABC",
        sources=[Source(n=1, title="T", url="https://wowhead.com/t")],
    )
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9]))
    builder = _SpyPromptBuilder(built=built)
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    orch.answer("query")

    assert len(llm.prompts) == 1, "generate must be called exactly once"
    prompt = llm.prompts[0]
    assert "SYSTEM-MARKER-XYZ" in prompt
    assert "USER-MARKER-ABC" in prompt
    # system precedes user, separated by a blank line (R12, design §6).
    assert prompt == "SYSTEM-MARKER-XYZ\n\nUSER-MARKER-ABC"


# ---------------------------------------------------------------------------
# R4, R5, R6, R7, R21 — metadata: model, persona, max_score, scores
# ---------------------------------------------------------------------------

def test_metadata_model_persona_scores():
    """R4/R5/R6/R7/R21: metadata carries llm.model, effective persona, max_score, per-chunk scores."""
    result = _result(below_threshold=False, scores=[0.95, 0.72, 0.55])
    retriever = _StubRetriever(result)
    builder = _SpyPromptBuilder()
    llm = _SpyLLM(model="qwen2.5:7b-instruct")
    persona = Persona(name="orc", system_style="Lok'tar")
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("query", persona=persona)

    assert answer.metadata.model == "qwen2.5:7b-instruct"            # R4
    assert answer.metadata.persona == "orc"                          # R5
    assert answer.metadata.max_score == result.max_score == 0.95     # R6
    assert answer.metadata.scores == [0.95, 0.72, 0.55]              # R7, R21
    assert answer.metadata.scores == [rc.score for rc in result.chunks]  # R21


# ---------------------------------------------------------------------------
# R14, R15, R16, R18 — abstention short-circuits build + generate
# ---------------------------------------------------------------------------

def test_abstains_when_below_threshold():
    """R14/R15/R16/R18: below_threshold=True -> abstained, clear message, sources=[]; build/generate NOT called."""
    retriever = _StubRetriever(_result(below_threshold=True, scores=[0.1]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("obscure query")

    assert answer.abstained is True                          # R14
    assert answer.answer == (
        "No hay evidencia suficiente en los documentos para responder con seguridad."
    )                                                        # R15, R18
    assert answer.sources == []                              # R16
    assert not builder.build_called, "build must NOT be called when abstaining"   # R14
    assert llm.prompts == [], "generate must NOT be called when abstaining"       # R14


# ---------------------------------------------------------------------------
# R17 — abstention metadata still populated (max_score, persona, model)
# ---------------------------------------------------------------------------

def test_abstention_metadata_present():
    """R17: when abstaining, metadata still carries max_score, persona (and model)."""
    retriever = _StubRetriever(_result(below_threshold=True, scores=[0.12]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM(model="qwen2.5:7b-instruct")
    persona = Persona(name="troll", system_style="Mon...")
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("query", persona=persona)

    assert answer.metadata.max_score == 0.12       # R17
    assert answer.metadata.persona == "troll"      # R17
    assert answer.metadata.model == "qwen2.5:7b-instruct"
    assert answer.metadata.scores == [0.12]


# ---------------------------------------------------------------------------
# R14, R16, R17 — empty store abstains (real f5 + f6, fakes underneath)
# ---------------------------------------------------------------------------

def test_empty_store_abstains():
    """R14/R16/R17: real f5 over an empty store (below_threshold, max_score=0.0) -> f8 abstains."""
    from wowrag.generation.prompt_builder import DefaultPromptBuilder
    from wowrag.retrieval.retriever import DefaultRetriever

    dim = 16
    embedder = FakeEmbeddingProvider(dimension=dim)
    store = FakeVectorStore(dimension=dim)  # empty: no upsert
    settings = _settings(score_threshold=0.30, default_persona="simple")
    retriever = DefaultRetriever(embedder=embedder, store=store, settings=settings)
    builder = DefaultPromptBuilder(settings=settings)
    llm = FakeLLMProvider(model="fake-llm")
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=settings)

    answer = orch.answer("What is Fireball?")

    assert answer.abstained is True                          # R14
    assert answer.sources == []                              # R16
    assert answer.metadata.max_score == 0.0                  # R17
    assert answer.metadata.persona == "simple"               # R17


# ---------------------------------------------------------------------------
# R23 — persona=None resolves Settings.default_persona, passed to the builder
# ---------------------------------------------------------------------------

def test_persona_none_resolves_default():
    """R23: answer(q) with no persona -> metadata reports Settings.default_persona; builder receives it."""
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings(default_persona="orc"))

    answer = orch.answer("query")  # no persona

    expected = load_persona("orc")
    assert answer.metadata.persona == "orc"                   # R23
    # The builder received the SAME resolved persona used for the metadata (R23).
    assert builder.received_persona is not None
    assert builder.received_persona.name == expected.name


# ---------------------------------------------------------------------------
# R5 — explicit persona reported in metadata
# ---------------------------------------------------------------------------

def test_persona_explicit_reported():
    """R5: answer(q, persona=<orc>) -> metadata.persona == 'orc' and builder gets it."""
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    persona = load_persona("orc")
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("query", persona=persona)

    assert answer.metadata.persona == "orc"                  # R5
    assert builder.received_persona is persona


# ---------------------------------------------------------------------------
# R26 — infra errors propagate, not masked as an empty Answer
# ---------------------------------------------------------------------------

def test_infra_errors_propagate_retriever():
    """R26: RetrieverError from the retriever propagates; not masked as an empty Answer."""
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(_ErrorRetriever(), builder, llm, settings=_settings())

    with pytest.raises(RetrieverError):
        orch.answer("valid query")

    assert not builder.build_called
    assert llm.prompts == []


def test_infra_errors_propagate_llm():
    """R26: LLMError from the LLM provider propagates; not masked as an empty Answer."""
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.9]))
    builder = _SpyPromptBuilder()
    orch = DefaultRagOrchestrator(retriever, builder, _ErrorLLM(), settings=_settings())

    with pytest.raises(LLMError):
        orch.answer("valid query")


# ---------------------------------------------------------------------------
# R9, R22 — depends only on the Protocol interfaces (duck-typed stubs)
# ---------------------------------------------------------------------------

def test_depends_only_on_interfaces():
    """R9/R22: constructible/runnable with stubs that implement only the Protocols."""
    # _StubRetriever, _SpyPromptBuilder, _SpyLLM implement only the Protocol surfaces.
    retriever = _StubRetriever(_result(below_threshold=False, scores=[0.7]))
    builder = _SpyPromptBuilder()
    llm = _SpyLLM()
    orch = DefaultRagOrchestrator(retriever, builder, llm, settings=_settings())

    answer = orch.answer("spell query")

    assert isinstance(answer, Answer)
    assert answer.abstained is False


# ---------------------------------------------------------------------------
# R27 — exports from the wowrag.rag package
# ---------------------------------------------------------------------------

def test_exports_from_package():
    """R27: from wowrag.rag import RagOrchestrator, OrchestratorError, DefaultRagOrchestrator works."""
    assert RagOrchestrator is not None
    assert OrchestratorError is not None
    assert DefaultRagOrchestrator is not None
    assert issubclass(OrchestratorError, Exception)
    assert hasattr(DefaultRagOrchestrator, "answer")
