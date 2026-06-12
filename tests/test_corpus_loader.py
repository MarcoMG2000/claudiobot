"""Tests for JsonlCorpusLoader and the CorpusLoader Protocol (src/wowrag/ingest/).

Traceability
------------
R4  — CorpusLoader Protocol exists and JsonlCorpusLoader satisfies it.
R5  — JsonlCorpusLoader is selectable as a concrete implementation behind the
      CorpusLoader interface.
R6  — Load *.jsonl from a directory, one Document per non-blank line.
R7  — Non-existent path / file (not a directory) raises CorpusNotFoundError.
R8  — Invalid JSON line or missing required field raises MalformedCorpusError
      with file path and line number.
R9  — Directory without *.jsonl files returns an empty list.
R10 — Blank lines in a .jsonl file are silently ignored.
R11 — All tests pass offline (no network fixtures); the loader uses only
      pathlib and json (stdlib).

All tests use pytest's tmp_path fixture; nothing is written to the repo.
"""

import json
from pathlib import Path
from typing import runtime_checkable

import pytest

from wowrag.ingest import (
    CorpusError,
    CorpusLoader,
    CorpusNotFoundError,
    JsonlCorpusLoader,
    MalformedCorpusError,
)
from wowrag.models import Document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write a list of dicts as JSONL to *path*."""
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_record(**overrides) -> dict:
    base = {
        "text": "Fireball deals fire damage.",
        "source_url": "https://www.wowhead.com/classic/spell=133/fireball",
        "title": "Fireball - Spell",
        "section": "Effects",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# R4, R5 — Protocol satisfaction / interface compatibility
# ---------------------------------------------------------------------------


def test_jsonl_loader_satisfies_corpus_loader_protocol():  # R4, R5
    """JsonlCorpusLoader structurally satisfies the CorpusLoader Protocol."""
    loader = JsonlCorpusLoader()
    # Protocol structural check: the object has a 'load' callable.
    assert callable(getattr(loader, "load", None)), (
        "JsonlCorpusLoader must expose a callable 'load' method"
    )


def test_corpus_loader_usable_via_interface(tmp_path: Path):  # R4, R5
    """JsonlCorpusLoader can be used through a CorpusLoader-typed variable."""
    # Write a minimal corpus
    _write_jsonl(tmp_path / "a.jsonl", [_valid_record()])

    loader: CorpusLoader = JsonlCorpusLoader()  # typed as the interface
    docs = loader.load(tmp_path)
    assert len(docs) == 1
    assert isinstance(docs[0], Document)


# ---------------------------------------------------------------------------
# R6 — happy path: load documents from *.jsonl files
# ---------------------------------------------------------------------------


def test_load_single_file_single_document(tmp_path: Path):  # R6
    """One .jsonl file with one record returns exactly one Document."""
    _write_jsonl(tmp_path / "corpus.jsonl", [_valid_record()])
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.text == "Fireball deals fire damage."
    assert doc.source_url == "https://www.wowhead.com/classic/spell=133/fireball"
    assert doc.title == "Fireball - Spell"
    assert doc.section == "Effects"


def test_load_multiple_records_in_single_file(tmp_path: Path):  # R6
    """Multiple records in a single .jsonl file produce multiple Documents."""
    records = [
        _valid_record(text=f"Text {i}", title=f"Title {i}") for i in range(5)
    ]
    _write_jsonl(tmp_path / "corpus.jsonl", records)
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert len(docs) == 5
    for i, doc in enumerate(docs):
        assert doc.text == f"Text {i}"
        assert doc.title == f"Title {i}"


def test_load_multiple_files_sorted_order(tmp_path: Path):  # R6
    """Files are read in sorted order; documents from earlier files come first."""
    _write_jsonl(tmp_path / "b.jsonl", [_valid_record(text="From B", title="B")])
    _write_jsonl(tmp_path / "a.jsonl", [_valid_record(text="From A", title="A")])
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert len(docs) == 2
    assert docs[0].text == "From A"  # a.jsonl < b.jsonl
    assert docs[1].text == "From B"


def test_load_metadata_preserved(tmp_path: Path):  # R6
    """All metadata fields (source_url, title, section) are correctly loaded."""
    record = _valid_record(
        text="Some spell description.",
        source_url="https://www.wowhead.com/classic/spell=999",
        title="My Spell",
        section="Tips",
    )
    _write_jsonl(tmp_path / "corpus.jsonl", [record])
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert docs[0].source_url == "https://www.wowhead.com/classic/spell=999"
    assert docs[0].title == "My Spell"
    assert docs[0].section == "Tips"


# ---------------------------------------------------------------------------
# R7 — non-existent / non-directory path raises CorpusNotFoundError
# ---------------------------------------------------------------------------


def test_load_nonexistent_path_raises_corpus_not_found_error(tmp_path: Path):  # R7
    """A path that does not exist raises CorpusNotFoundError containing the path."""
    missing = tmp_path / "does_not_exist"
    loader = JsonlCorpusLoader()
    with pytest.raises(CorpusNotFoundError) as exc_info:
        loader.load(missing)
    assert str(missing) in str(exc_info.value), (
        "CorpusNotFoundError message should contain the offending path"
    )


def test_load_file_path_raises_corpus_not_found_error(tmp_path: Path):  # R7
    """Passing a file (not a directory) raises CorpusNotFoundError."""
    file_path = tmp_path / "not_a_dir.jsonl"
    file_path.write_text("{}\n", encoding="utf-8")
    loader = JsonlCorpusLoader()
    with pytest.raises(CorpusNotFoundError) as exc_info:
        loader.load(file_path)
    assert str(file_path) in str(exc_info.value)


def test_corpus_not_found_error_is_corpus_error():  # R7
    """CorpusNotFoundError must be a subclass of CorpusError (family catching)."""
    assert issubclass(CorpusNotFoundError, CorpusError)


# ---------------------------------------------------------------------------
# R8 — malformed line raises MalformedCorpusError with file + line number
# ---------------------------------------------------------------------------


def test_load_invalid_json_line_raises_malformed_corpus_error(tmp_path: Path):  # R8
    """An invalid JSON line raises MalformedCorpusError with the line number."""
    jsonl_path = tmp_path / "bad.jsonl"
    jsonl_path.write_text(
        json.dumps(_valid_record(text="Good line.")) + "\n"
        "NOT VALID JSON\n",
        encoding="utf-8",
    )
    loader = JsonlCorpusLoader()
    with pytest.raises(MalformedCorpusError) as exc_info:
        loader.load(tmp_path)
    msg = str(exc_info.value)
    assert "2" in msg, f"Expected line number 2 in error message, got: {msg!r}"


def test_load_invalid_json_line_message_contains_filename(tmp_path: Path):  # R8
    """MalformedCorpusError message contains the file path."""
    jsonl_path = tmp_path / "bad.jsonl"
    jsonl_path.write_text("INVALID\n", encoding="utf-8")
    loader = JsonlCorpusLoader()
    with pytest.raises(MalformedCorpusError) as exc_info:
        loader.load(tmp_path)
    assert "bad.jsonl" in str(exc_info.value)


def test_load_line_missing_text_field_raises_malformed_corpus_error(tmp_path: Path):  # R8
    """A JSON line valid but missing required 'text' raises MalformedCorpusError."""
    record_no_text = {
        "source_url": "https://www.wowhead.com/classic/item=1",
        "title": "Title",
    }
    _write_jsonl(tmp_path / "missing_text.jsonl", [record_no_text])
    loader = JsonlCorpusLoader()
    with pytest.raises(MalformedCorpusError):
        loader.load(tmp_path)


def test_load_line_with_empty_text_raises_malformed_corpus_error(tmp_path: Path):  # R8
    """A JSON line with text='' fails Document validation → MalformedCorpusError."""
    record_empty_text = _valid_record(text="")
    _write_jsonl(tmp_path / "empty_text.jsonl", [record_empty_text])
    loader = JsonlCorpusLoader()
    with pytest.raises(MalformedCorpusError):
        loader.load(tmp_path)


def test_malformed_corpus_error_is_corpus_error():  # R8
    """MalformedCorpusError must be a subclass of CorpusError (family catching)."""
    assert issubclass(MalformedCorpusError, CorpusError)


def test_malformed_error_reports_correct_line_number(tmp_path: Path):  # R8
    """The line number in MalformedCorpusError is 1-based and accurate."""
    jsonl_path = tmp_path / "lineno.jsonl"
    # Lines 1 and 2 are valid; line 3 is malformed.
    lines = [
        json.dumps(_valid_record(text=f"Text {i}")) for i in range(2)
    ]
    lines.append("BROKEN JSON")
    jsonl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    loader = JsonlCorpusLoader()
    with pytest.raises(MalformedCorpusError) as exc_info:
        loader.load(tmp_path)
    assert "3" in str(exc_info.value), (
        f"Expected line number 3 in the error message, got: {exc_info.value!r}"
    )


# ---------------------------------------------------------------------------
# R9 — empty directory / no .jsonl files returns []
# ---------------------------------------------------------------------------


def test_load_empty_directory_returns_empty_list(tmp_path: Path):  # R9
    """An empty directory returns an empty list without raising."""
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert docs == []


def test_load_directory_with_no_jsonl_files_returns_empty_list(tmp_path: Path):  # R9
    """A directory with only non-.jsonl files returns an empty list."""
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "data.json").write_text("{}", encoding="utf-8")
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert docs == []


# ---------------------------------------------------------------------------
# R10 — blank lines in .jsonl files are silently ignored
# ---------------------------------------------------------------------------


def test_load_blank_lines_are_ignored(tmp_path: Path):  # R10
    """Blank lines between valid records are skipped and do not produce Documents."""
    jsonl_path = tmp_path / "with_blanks.jsonl"
    record = _valid_record()
    jsonl_path.write_text(
        "\n"
        + json.dumps(record) + "\n"
        + "\n"
        + "   \n"  # whitespace-only line
        + json.dumps(_valid_record(text="Second doc.")) + "\n"
        + "\n",
        encoding="utf-8",
    )
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert len(docs) == 2, f"Expected 2 docs (blank lines ignored), got {len(docs)}"


def test_load_file_all_blank_lines_returns_empty_list(tmp_path: Path):  # R10
    """A .jsonl file containing only blank lines returns an empty list."""
    (tmp_path / "blanks.jsonl").write_text("\n\n\n   \n", encoding="utf-8")
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert docs == []


# ---------------------------------------------------------------------------
# R11 — tests pass offline (no network usage; loader uses only pathlib/json)
# ---------------------------------------------------------------------------


def test_loader_uses_no_network_fixtures(tmp_path: Path):  # R11
    """Implicit R11 coverage: this test passes with no network access.

    The test intentionally uses only local tmp_path data and asserts that
    JsonlCorpusLoader.load() completes normally without any I/O beyond the
    local filesystem.  If the implementation were to attempt a network call,
    it would fail or time out in an offline CI environment.
    """
    _write_jsonl(tmp_path / "offline.jsonl", [_valid_record()])
    loader = JsonlCorpusLoader()
    docs = loader.load(tmp_path)
    assert len(docs) == 1
