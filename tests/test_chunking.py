"""Tests for the chunking pipeline (src/wowrag/ingest/chunking.py).

Traceability
------------
R4  — Chunker Protocol: OverlapChunker is usable via the Chunker interface.
R5  — OverlapChunker splits with sliding window; at least 1 Chunk per Document.
R6  — metadata (source_url, title, section) copied unchanged to each Chunk.
R7  — chunk_id is deterministic: same inputs always yield the same id.
R8  — processing the same Document twice yields identical chunk_id lists.
R9  — Settings exposes chunk_size as an integer; can be passed to OverlapChunker.
R10 — Settings exposes chunk_overlap as an integer; can be passed to OverlapChunker.
R11 — chunk_overlap >= chunk_size raises ChunkingError in OverlapChunker.__init__.
R12 — Text shorter than chunk_size produces exactly 1 Chunk with the full text.
R13 — Union of all chunk fragments covers the full original text (no gaps).
"""

from __future__ import annotations

import pytest

from wowrag.config import Settings
from wowrag.ingest.chunking import Chunker, ChunkingError, OverlapChunker
from wowrag.models import Document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(text: str, source_url: str = "https://example.com/page",
              title: str = "Test Page", section: str = "Intro") -> Document:
    return Document(text=text, source_url=source_url, title=title, section=section)


# ---------------------------------------------------------------------------
# R11 — invalid overlap raises ChunkingError
# ---------------------------------------------------------------------------


def test_invalid_overlap_equal_raises():  # R11
    """OverlapChunker(size=100, overlap=100) must raise ChunkingError."""
    with pytest.raises(ChunkingError):
        OverlapChunker(chunk_size=100, chunk_overlap=100)


def test_invalid_overlap_greater_raises():  # R11
    """OverlapChunker(size=100, overlap=110) must raise ChunkingError."""
    with pytest.raises(ChunkingError):
        OverlapChunker(chunk_size=100, chunk_overlap=110)


# ---------------------------------------------------------------------------
# R12 — short text produces exactly 1 chunk
# ---------------------------------------------------------------------------


def test_short_text_single_chunk():  # R12
    """Text of 10 chars with chunk_size=512 must yield exactly 1 Chunk."""
    doc = _make_doc("Hello WoW!")  # 10 chars
    chunker = OverlapChunker(chunk_size=512, chunk_overlap=64)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello WoW!"


def test_text_equal_to_chunk_size():  # R12, R13
    """Text of exactly chunk_size chars must produce exactly 1 Chunk."""
    text = "x" * 512
    doc = _make_doc(text)
    chunker = OverlapChunker(chunk_size=512, chunk_overlap=64)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == text


# ---------------------------------------------------------------------------
# R5, R13 — overlap produces correct multiple chunks
# ---------------------------------------------------------------------------


def test_overlap_produces_multiple_chunks():  # R5, R13
    """200-char text, chunk_size=100, overlap=20 must yield 3 chunks.

    step = 100 - 20 = 80
    positions: 0, 80, 160
    chunk[0]: text[0:100]
    chunk[1]: text[80:180]
    chunk[2]: text[160:260] but text ends at 200, so text[160:200]
    """
    text = "A" * 200
    doc = _make_doc(text)
    chunker = OverlapChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 3
    assert chunks[0].text == text[0:100]
    assert chunks[1].text == text[80:180]
    assert chunks[2].text == text[160:200]


# ---------------------------------------------------------------------------
# R13 — full coverage: union of fragments covers original text (no gaps)
# ---------------------------------------------------------------------------


def test_full_coverage():  # R13
    """The union of all chunk fragments must cover the original text with no gaps."""
    text = "The quick brown fox jumps over the lazy dog. " * 10  # 450 chars
    doc = _make_doc(text)
    chunker = OverlapChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk(doc)

    # Reconstruct coverage: mark each character position covered by at least 1 chunk.
    # Because chunks overlap, we verify no position in [0, len(text)) is uncovered.
    step = 100 - 20
    covered = set()
    start = 0
    for chunk in chunks:
        end = start + len(chunk.text)
        covered.update(range(start, end))
        start += step

    for pos in range(len(text)):
        assert pos in covered, f"Position {pos} not covered by any chunk"


# ---------------------------------------------------------------------------
# R6 — metadata preserved in each chunk
# ---------------------------------------------------------------------------


def test_metadata_preserved():  # R6
    """Each Chunk must have source_url, title, section equal to the source Document."""
    doc = _make_doc(
        text="Some long text that will be split. " * 5,
        source_url="https://www.wowhead.com/classic/spell=133",
        title="Fireball",
        section="Effects",
    )
    chunker = OverlapChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.source_url == doc.source_url
        assert chunk.title == doc.title
        assert chunk.section == doc.section


# ---------------------------------------------------------------------------
# R7, R8 — chunk_id is deterministic (same document → same ids)
# ---------------------------------------------------------------------------


def test_chunk_id_stable():  # R7, R8
    """Processing the same Document twice must yield identical chunk_id lists."""
    doc = _make_doc("Some text that is long enough to chunk. " * 3)
    chunker = OverlapChunker(chunk_size=50, chunk_overlap=10)
    run1 = [c.chunk_id for c in chunker.chunk(doc)]
    run2 = [c.chunk_id for c in chunker.chunk(doc)]
    assert run1 == run2
    assert len(run1) > 0


def test_chunk_id_differs_across_documents():  # R7
    """Two Documents with different source_url must have different chunk_id at index 0."""
    doc_a = _make_doc("Hello World text here.", source_url="https://example.com/a")
    doc_b = _make_doc("Hello World text here.", source_url="https://example.com/b")
    chunker = OverlapChunker(chunk_size=512, chunk_overlap=64)
    chunks_a = chunker.chunk(doc_a)
    chunks_b = chunker.chunk(doc_b)
    assert chunks_a[0].chunk_id != chunks_b[0].chunk_id


# ---------------------------------------------------------------------------
# R4 — OverlapChunker is usable as Chunker (Protocol compatibility)
# ---------------------------------------------------------------------------


def test_chunker_protocol_compatible():  # R4
    """OverlapChunker must satisfy the Chunker Protocol: assign and call chunk()."""
    chunker: Chunker = OverlapChunker(chunk_size=100, chunk_overlap=20)
    doc = _make_doc("Hello WoW Classic!")
    chunks = chunker.chunk(doc)
    assert isinstance(chunks, list)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello WoW Classic!"


# ---------------------------------------------------------------------------
# R9, R10 — Settings exposes chunk_size and chunk_overlap
# ---------------------------------------------------------------------------


def test_settings_chunk_params():  # R9, R10
    """Settings() must expose chunk_size and chunk_overlap as ints usable by OverlapChunker."""
    settings = Settings()
    assert isinstance(settings.chunk_size, int)
    assert isinstance(settings.chunk_overlap, int)
    # Must not raise ChunkingError with the default values
    chunker = OverlapChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    doc = _make_doc("Test text for settings-driven chunker.")
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 1
