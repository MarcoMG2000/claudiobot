"""Tests for WowheadNormalizer: HTML -> Document (Slice B): R12-R16, R25, R31.

``selectolax`` is pinned in ``requirements.txt`` and installed by ``init.sh``, so
the parser-backed tests RUN in the default suite (no skip guard). The
missing-parser test (R31) and the import-isolation test (R25) block selectolax in
``sys.modules`` to prove the lazy import + ScrapeError behaviour regardless.

All network-free: the normalizer parses committed HTML fixtures (no fetcher).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from wowrag.ingest.wowhead import ScrapeError, WowheadNormalizer
from wowrag.models import Document

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wowhead"
SOURCE_URL = "https://www.wowhead.com/spell=133/fireball"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def normalizer() -> WowheadNormalizer:
    """A real normalizer (selectolax is installed by init.sh via requirements.txt)."""
    return WowheadNormalizer()


# ---------------------------------------------------------------------------
# R12, R13, R14, R15: Document fields populated from the fixture
# ---------------------------------------------------------------------------


def test_normalize_populates_document_fields(normalizer):  # R12, R13, R14, R15
    """text / source_url / title / section are all populated from the fixture."""
    doc = normalizer.normalize(_fixture("spell_fireball.html"), SOURCE_URL)
    assert isinstance(doc, Document)
    assert doc.source_url == SOURCE_URL  # R13
    assert doc.title == "Fireball"  # R14 (from <h1>)
    assert doc.section == "Spell Details"  # R15 (from <h2>)
    assert "Fire damage" in doc.text  # R12 (main content extracted)
    assert "1.5 seconds" in doc.text


# ---------------------------------------------------------------------------
# R12: boilerplate (nav / ads / scripts / footer) is stripped from text
# ---------------------------------------------------------------------------


def test_boilerplate_stripped(normalizer):  # R12
    """Nav, ad, script and footer content never appears in the extracted text."""
    doc = normalizer.normalize(_fixture("spell_fireball.html"), SOURCE_URL)
    assert doc is not None
    text = doc.text
    assert "BUY GOLD NOW" not in text  # ad (aside.ad)
    assert "Database" not in text  # nav menu
    assert "Copyright" not in text  # footer
    assert "console.log" not in text  # script
    assert "ADBLOCK" not in text  # head script
    assert "tooltip" not in text  # style


# ---------------------------------------------------------------------------
# R15: section defaults to "" when the page has no sub-section heading
# ---------------------------------------------------------------------------


def test_section_empty_when_absent(normalizer):  # R15
    """A page without an <h2> yields section == ''."""
    html = (
        "<html><head><title>No Section</title></head>"
        "<body><main id='main-contents'><h1>Item</h1>"
        "<p>An item with no sub-section heading.</p></main></body></html>"
    )
    doc = normalizer.normalize(html, SOURCE_URL)
    assert doc is not None
    assert doc.section == ""  # R15
    assert doc.title == "Item"


def test_title_falls_back_to_title_tag(normalizer):  # R14
    """When there is no <h1>, the title comes from the <title> tag."""
    html = (
        "<html><head><title>Onyxia - NPC</title></head>"
        "<body><main id='main-contents'>"
        "<p>A black dragon broodmother.</p></main></body></html>"
    )
    doc = normalizer.normalize(html, SOURCE_URL)
    assert doc is not None
    assert doc.title == "Onyxia - NPC"  # R14 (fallback to <title>)


# ---------------------------------------------------------------------------
# R16: a page with no main text returns None (no empty-text Document)
# ---------------------------------------------------------------------------


def test_empty_body_returns_none(normalizer):  # R16
    """A page whose body is only boilerplate yields None (skip, not empty doc)."""
    doc = normalizer.normalize(_fixture("empty_body.html"), SOURCE_URL)
    assert doc is None  # R16


# ---------------------------------------------------------------------------
# R31: instantiating the normalizer without selectolax raises ScrapeError
# ---------------------------------------------------------------------------


def test_missing_parser_raises_scrapeerror(monkeypatch):  # R31
    """WowheadNormalizer() raises ScrapeError (not ImportError) without selectolax.

    Blocks ``selectolax.parser`` in sys.modules so the lazy import inside
    __init__ raises ImportError, which must surface as ScrapeError naming
    selectolax. Needs no real parser available (blocked here regardless).
    """
    monkeypatch.setitem(sys.modules, "selectolax", None)
    monkeypatch.setitem(sys.modules, "selectolax.parser", None)
    with pytest.raises(ScrapeError, match="selectolax"):
        WowheadNormalizer()


# ---------------------------------------------------------------------------
# R25: importing the normalizer module does not eagerly import selectolax
# ---------------------------------------------------------------------------


def test_import_module_is_lazy_no_selectolax(monkeypatch):  # R25
    """Importing wowrag.ingest.wowhead.normalizer does not import selectolax.

    Even with selectolax blocked in sys.modules, importing the module succeeds
    because the parser import is lazy (inside WowheadNormalizer.__init__).
    """
    import importlib

    monkeypatch.setitem(sys.modules, "selectolax", None)
    monkeypatch.setitem(sys.modules, "selectolax.parser", None)
    monkeypatch.delitem(
        sys.modules, "wowrag.ingest.wowhead.normalizer", raising=False
    )
    mod = importlib.import_module("wowrag.ingest.wowhead.normalizer")
    assert mod is not None  # no ImportError at module import time
