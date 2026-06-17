"""Tests for the Answer and AnswerMetadata models (f8-rag-orchestrator).

Trazabilidad: R1, R3, R4, R5, R6, R7, R27 (parcial).
All tests are DB-free / GPU-free / network-free.
"""

from __future__ import annotations

from wowrag.models import Answer, AnswerMetadata, Source


# ---------------------------------------------------------------------------
# R1 — Answer exposes answer / sources / abstained / metadata
# ---------------------------------------------------------------------------

def test_answer_fields():
    """R1: Answer(answer, sources, abstained, metadata) builds and exposes all four."""
    meta = AnswerMetadata(model="fake-llm", persona="simple", max_score=0.9, scores=[0.9])
    source = Source(n=1, title="Fireball - Spell", url="https://wowhead.com/fireball")
    answer = Answer(
        answer="Fireball deals fire damage. [1]",
        sources=[source],
        abstained=False,
        metadata=meta,
    )

    assert answer.answer == "Fireball deals fire damage. [1]"
    assert answer.sources == [source]
    assert answer.abstained is False
    assert answer.metadata == meta


# ---------------------------------------------------------------------------
# R3 — Answer.sources accepts and preserves a list[Source] from f6
# ---------------------------------------------------------------------------

def test_answer_sources_are_source_type():
    """R3: Answer.sources accepts a list[Source] ({n, title, url}) and preserves it."""
    sources = [
        Source(n=1, title="Spell A", url="https://wowhead.com/a"),
        Source(n=2, title="Spell B", url="https://wowhead.com/b"),
    ]
    answer = Answer(
        answer="Grounded answer [1][2]",
        sources=sources,
        abstained=False,
        metadata=AnswerMetadata(model="m", persona="simple", max_score=0.8, scores=[0.8, 0.7]),
    )

    assert all(isinstance(s, Source) for s in answer.sources)
    assert answer.sources[0].n == 1
    assert answer.sources[0].title == "Spell A"
    assert answer.sources[0].url == "https://wowhead.com/a"
    assert answer.sources[1].n == 2


# ---------------------------------------------------------------------------
# R4, R5, R6, R7 — AnswerMetadata exposes model / persona / max_score / scores
# ---------------------------------------------------------------------------

def test_answer_metadata_fields():
    """R4/R5/R6/R7: AnswerMetadata builds and exposes model, persona, max_score, scores."""
    meta = AnswerMetadata(
        model="qwen2.5:7b-instruct",
        persona="orc",
        max_score=0.95,
        scores=[0.95, 0.72, 0.55],
    )

    assert meta.model == "qwen2.5:7b-instruct"   # R4
    assert meta.persona == "orc"                 # R5
    assert meta.max_score == 0.95                # R6
    assert meta.scores == [0.95, 0.72, 0.55]     # R7


def test_abstained_answer_empty_sources():
    """R16: an abstained Answer is valid with sources=[]."""
    answer = Answer(
        answer="No hay evidencia suficiente en los documentos para responder con seguridad.",
        sources=[],
        abstained=True,
        metadata=AnswerMetadata(model="m", persona="simple", max_score=0.0, scores=[]),
    )

    assert answer.abstained is True
    assert answer.sources == []


# ---------------------------------------------------------------------------
# R27 (partial) — Answer / AnswerMetadata importable from wowrag.models
# ---------------------------------------------------------------------------

def test_exports_models():
    """R27 (partial): from wowrag.models import Answer, AnswerMetadata works."""
    import wowrag.models as models

    assert Answer is not None
    assert AnswerMetadata is not None
    assert "Answer" in models.__all__
    assert "AnswerMetadata" in models.__all__
