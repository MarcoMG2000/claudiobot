"""Tests for the golden dataset schema and loader (f10-evaluation-harness).

Trazabilidad: R1, R2, R3, R4, R5. All network-free, stdlib + tmp_path only.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from wowrag.eval import GoldenItem, GoldenDatasetError, load_golden


# ---------------------------------------------------------------------------
# R1 — GoldenItem fields
# ---------------------------------------------------------------------------

def test_golden_item_fields():
    """R1: GoldenItem with the four fields constructs and stores them."""
    item = GoldenItem(
        question="What does Fireball do?",
        expected_urls=["https://wowhead.com/spell=133"],
        in_corpus=True,
        reference_answer="Fireball deals fire damage.",
    )

    assert item.question == "What does Fireball do?"
    assert item.expected_urls == ["https://wowhead.com/spell=133"]
    assert item.in_corpus is True
    assert item.reference_answer == "Fireball deals fire damage."


def test_golden_item_defaults():
    """R1: expected_urls defaults to [] and reference_answer to None."""
    item = GoldenItem(question="Out of corpus?", in_corpus=False)

    assert item.expected_urls == []
    assert item.reference_answer is None


def test_golden_item_blank_question_rejected():
    """R1: a blank/whitespace question is rejected."""
    with pytest.raises(ValidationError):
        GoldenItem(question="   ", in_corpus=False)


# ---------------------------------------------------------------------------
# R2 — in-corpus item must declare expected_urls
# ---------------------------------------------------------------------------

def test_in_corpus_requires_expected_urls():
    """R2: in_corpus=True with empty expected_urls -> ValidationError."""
    with pytest.raises(ValidationError):
        GoldenItem(question="Has answer?", expected_urls=[], in_corpus=True)


# ---------------------------------------------------------------------------
# R3 — out-of-corpus item must not declare expected_urls
# ---------------------------------------------------------------------------

def test_out_of_corpus_rejects_expected_urls():
    """R3: in_corpus=False with non-empty expected_urls -> ValidationError."""
    with pytest.raises(ValidationError):
        GoldenItem(
            question="No answer expected",
            expected_urls=["https://wowhead.com/x"],
            in_corpus=False,
        )


# ---------------------------------------------------------------------------
# R4 — load_golden parses a valid JSONL file
# ---------------------------------------------------------------------------

def test_load_golden_parses_jsonl(tmp_path):
    """R4: a valid JSONL file -> list[GoldenItem] in file order."""
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"question": "Q1", "expected_urls": ["https://a"], "in_corpus": true}\n'
        '{"question": "Q2", "expected_urls": [], "in_corpus": false}\n',
        encoding="utf-8",
    )

    items = load_golden(path)

    assert len(items) == 2
    assert all(isinstance(i, GoldenItem) for i in items)
    assert items[0].question == "Q1"
    assert items[0].in_corpus is True
    assert items[1].in_corpus is False


def test_load_golden_tolerates_blank_lines(tmp_path):
    """R4: blank lines are tolerated (not parsed, not errored)."""
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"question": "Q1", "expected_urls": ["https://a"], "in_corpus": true}\n'
        "\n"
        "   \n"
        '{"question": "Q2", "expected_urls": [], "in_corpus": false}\n',
        encoding="utf-8",
    )

    items = load_golden(path)

    assert len(items) == 2


def test_load_golden_malformed_json_raises(tmp_path):
    """R4: a broken-JSON line -> GoldenDatasetError naming the 1-based line."""
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"question": "Q1", "expected_urls": ["https://a"], "in_corpus": true}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    with pytest.raises(GoldenDatasetError) as exc:
        load_golden(path)

    assert "line 2" in str(exc.value)


def test_load_golden_invalid_item_raises(tmp_path):
    """R4: a line failing GoldenItem validation (R2) -> GoldenDatasetError(line)."""
    path = tmp_path / "golden.jsonl"
    # in_corpus=true but no expected_urls violates R2 -> must not be silenced.
    path.write_text(
        '{"question": "Q1", "expected_urls": [], "in_corpus": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(GoldenDatasetError) as exc:
        load_golden(path)

    assert "line 1" in str(exc.value)


# ---------------------------------------------------------------------------
# R5 — committed default fixture loads with in-corpus + out-of-corpus
# ---------------------------------------------------------------------------

def test_default_fixture_loads():
    """R5: load_golden() loads the committed fixture with >=1 of each kind."""
    items = load_golden()

    assert len(items) >= 2
    assert any(i.in_corpus for i in items)
    assert any(not i.in_corpus for i in items)
    # in-corpus items must carry expected_urls (R2 invariant of the fixture)
    assert all(i.expected_urls for i in items if i.in_corpus)
    # out-of-corpus items must not (R3 invariant of the fixture)
    assert all(not i.expected_urls for i in items if not i.in_corpus)
