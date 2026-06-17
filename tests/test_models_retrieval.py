"""Tests for RetrievedChunk and RetrievalResult models (f5-retriever).

Trazabilidad: R1, R2, R3, R4, R5, R15.
"""

from __future__ import annotations

import pytest

from wowrag.models import Chunk, RetrievedChunk, RetrievalResult


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str = "c1",
    text: str = "Fireball deals fire damage.",
    source_url: str = "https://www.wowhead.com/classic/spell=133/fireball",
    title: str = "Fireball - Spell",
    section: str = "Description",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=source_url,
        title=title,
        section=section,
    )


# ---------------------------------------------------------------------------
# R1 — RetrievedChunk wraps a Chunk + score
# ---------------------------------------------------------------------------

def test_retrievedchunk_wraps_chunk_and_score():
    """R1: RetrievedChunk(chunk=c, score=s) stores chunk and score fields."""
    chunk = _make_chunk()
    rc = RetrievedChunk(chunk=chunk, score=0.85)

    assert rc.chunk is chunk
    assert rc.score == 0.85


# ---------------------------------------------------------------------------
# R2 — Citation metadata properties delegate to chunk
# ---------------------------------------------------------------------------

def test_retrievedchunk_exposes_citation_metadata():
    """R2: source_url, title, section are read-only properties delegating to chunk."""
    chunk = _make_chunk(
        source_url="https://www.wowhead.com/classic/spell=133/fireball",
        title="Fireball - Spell",
        section="Description",
    )
    rc = RetrievedChunk(chunk=chunk, score=0.7)

    assert rc.source_url == chunk.source_url
    assert rc.title == chunk.title
    assert rc.section == chunk.section


def test_retrievedchunk_properties_are_readonly():
    """R2: source_url/title/section are properties (no setter)."""
    rc = RetrievedChunk(chunk=_make_chunk(), score=0.5)

    with pytest.raises((AttributeError, TypeError)):
        rc.source_url = "https://other.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# R3 — score preserved without recalculation
# ---------------------------------------------------------------------------

def test_retrievedchunk_preserves_score():
    """R3: score is stored exactly as passed, no recalculation or normalization."""
    for score_value in (0.0, 0.123456789, 1.0, -0.1):
        rc = RetrievedChunk(chunk=_make_chunk(), score=score_value)
        assert rc.score == score_value, f"Expected {score_value}, got {rc.score}"


# ---------------------------------------------------------------------------
# R4 — RetrievalResult has chunks / max_score / below_threshold
# ---------------------------------------------------------------------------

def test_retrievalresult_fields():
    """R4: RetrievalResult has chunks, max_score, below_threshold fields."""
    rc = RetrievedChunk(chunk=_make_chunk(), score=0.9)
    result = RetrievalResult(chunks=[rc], max_score=0.9, below_threshold=False)

    assert result.chunks == [rc]
    assert result.max_score == 0.9
    assert result.below_threshold is False


def test_retrievalresult_empty_chunks():
    """R4/R20: RetrievalResult with empty chunks is valid."""
    result = RetrievalResult(chunks=[], max_score=0.0, below_threshold=True)

    assert result.chunks == []
    assert result.max_score == 0.0
    assert result.below_threshold is True


# ---------------------------------------------------------------------------
# R5 — max_score equals the score of the first (best) chunk
# ---------------------------------------------------------------------------

def test_max_score_equals_best_chunk_score():
    """R5: with >=1 chunk, max_score should equal the score of chunks[0]."""
    chunks = [
        RetrievedChunk(chunk=_make_chunk(chunk_id="c1"), score=0.95),
        RetrievedChunk(chunk=_make_chunk(chunk_id="c2"), score=0.72),
        RetrievedChunk(chunk=_make_chunk(chunk_id="c3"), score=0.55),
    ]
    result = RetrievalResult(
        chunks=chunks,
        max_score=chunks[0].score,
        below_threshold=False,
    )

    assert result.max_score == chunks[0].score  # 0.95
    assert result.max_score != chunks[1].score   # not 0.72


# ---------------------------------------------------------------------------
# R15 — each RetrievedChunk in chunks carries citation metadata
# ---------------------------------------------------------------------------

def test_result_chunks_carry_metadata():
    """R15: each RetrievedChunk in RetrievalResult.chunks retains source metadata."""
    chunk_a = _make_chunk(
        chunk_id="a1",
        source_url="https://wowhead.com/a",
        title="Spell A",
        section="Sec A",
    )
    chunk_b = _make_chunk(
        chunk_id="b1",
        source_url="https://wowhead.com/b",
        title="Spell B",
        section="Sec B",
    )
    rc_a = RetrievedChunk(chunk=chunk_a, score=0.88)
    rc_b = RetrievedChunk(chunk=chunk_b, score=0.65)
    result = RetrievalResult(chunks=[rc_a, rc_b], max_score=0.88, below_threshold=False)

    assert result.chunks[0].source_url == "https://wowhead.com/a"
    assert result.chunks[0].title == "Spell A"
    assert result.chunks[0].section == "Sec A"
    assert result.chunks[1].source_url == "https://wowhead.com/b"
    assert result.chunks[1].title == "Spell B"
    assert result.chunks[1].section == "Sec B"
