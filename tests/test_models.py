"""Tests for the Document pydantic model (src/wowrag/models.py).

Traceability
------------
R1 — Document has text, source_url, title, section fields.
R2 — text empty or blank raises ValidationError mentioning 'text';
     missing required fields also raise ValidationError.
R3 — section is optional, defaults to "".
"""

import pytest
from pydantic import ValidationError

from wowrag.models import Document


# ---------------------------------------------------------------------------
# R1 — valid construction
# ---------------------------------------------------------------------------


def test_document_valid_all_fields():  # R1
    """A fully-specified Document is constructed and all fields are preserved."""
    doc = Document(
        text="Fireball deals fire damage to the target.",
        source_url="https://www.wowhead.com/classic/spell=133/fireball",
        title="Fireball - Spell",
        section="Effects",
    )
    assert doc.text == "Fireball deals fire damage to the target."
    assert doc.source_url == "https://www.wowhead.com/classic/spell=133/fireball"
    assert doc.title == "Fireball - Spell"
    assert doc.section == "Effects"


def test_document_minimal_fields():  # R1, R3
    """Constructing a Document with only the required fields works."""
    doc = Document(
        text="Some text.",
        source_url="https://www.wowhead.com/classic/item=12345",
        title="Some Item",
    )
    assert doc.text == "Some text."
    assert doc.source_url == "https://www.wowhead.com/classic/item=12345"
    assert doc.title == "Some Item"


# ---------------------------------------------------------------------------
# R3 — section defaults to ""
# ---------------------------------------------------------------------------


def test_document_section_defaults_to_empty_string():  # R3
    """When 'section' is not provided, it defaults to an empty string."""
    doc = Document(
        text="Some text.",
        source_url="https://www.wowhead.com/classic/item=1",
        title="Item Title",
    )
    assert doc.section == ""


def test_document_section_explicit_empty_string():  # R3
    """Explicitly passing section='' is valid and stays ''."""
    doc = Document(
        text="Some text.",
        source_url="https://www.wowhead.com/classic/item=1",
        title="Item Title",
        section="",
    )
    assert doc.section == ""


# ---------------------------------------------------------------------------
# R2 — empty / blank text raises ValidationError mentioning 'text'
# ---------------------------------------------------------------------------


def test_document_text_empty_raises_validation_error():  # R2
    """text='' must raise a ValidationError referencing the 'text' field."""
    with pytest.raises(ValidationError) as exc_info:
        Document(
            text="",
            source_url="https://www.wowhead.com/classic/item=1",
            title="Title",
        )
    errors = exc_info.value.errors()
    assert any(
        "text" in str(e.get("loc", "")) or "text" in str(e.get("msg", ""))
        for e in errors
    ), f"Expected error referencing 'text', got: {errors}"


def test_document_text_whitespace_only_raises_validation_error():  # R2
    """text='   ' (only spaces) must raise a ValidationError referencing 'text'."""
    with pytest.raises(ValidationError) as exc_info:
        Document(
            text="   ",
            source_url="https://www.wowhead.com/classic/item=1",
            title="Title",
        )
    errors = exc_info.value.errors()
    assert any(
        "text" in str(e.get("loc", "")) or "text" in str(e.get("msg", ""))
        for e in errors
    ), f"Expected error referencing 'text', got: {errors}"


def test_document_text_tab_only_raises_validation_error():  # R2
    """text='\\t' (only tab) counts as blank and must raise ValidationError."""
    with pytest.raises(ValidationError):
        Document(
            text="\t",
            source_url="https://www.wowhead.com/classic/item=1",
            title="Title",
        )


# ---------------------------------------------------------------------------
# R2 — missing required fields raise ValidationError
# ---------------------------------------------------------------------------


def test_document_missing_source_url_raises_validation_error():  # R2
    """Omitting source_url must raise a ValidationError."""
    with pytest.raises(ValidationError):
        Document(text="Some text.", title="Title")  # type: ignore[call-arg]


def test_document_missing_title_raises_validation_error():  # R2
    """Omitting title must raise a ValidationError."""
    with pytest.raises(ValidationError):
        Document(  # type: ignore[call-arg]
            text="Some text.",
            source_url="https://www.wowhead.com/classic/item=1",
        )


def test_document_missing_text_raises_validation_error():  # R2
    """Omitting text entirely must raise a ValidationError."""
    with pytest.raises(ValidationError):
        Document(  # type: ignore[call-arg]
            source_url="https://www.wowhead.com/classic/item=1",
            title="Title",
        )
