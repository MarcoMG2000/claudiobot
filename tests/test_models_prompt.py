"""Tests for Source and BuiltPrompt models added by f6.

All tests are DB-free, GPU-free, and network-free.
Traceability: each test is annotated with its R<n> requirement(s).
"""

from __future__ import annotations

import pytest

from wowrag.models import BuiltPrompt, Source


# ---------------------------------------------------------------------------
# Source model
# ---------------------------------------------------------------------------


def test_source_fields() -> None:
    """Source exposes n, title, and url fields correctly.

    R2 — BuiltPrompt.sources contains Source(n, title, url).
    """
    src = Source(n=1, title="Fireball - Spell", url="https://www.wowhead.com/spell=133")
    assert src.n == 1
    assert src.title == "Fireball - Spell"
    assert src.url == "https://www.wowhead.com/spell=133"


# ---------------------------------------------------------------------------
# BuiltPrompt model
# ---------------------------------------------------------------------------


def test_builtprompt_fields() -> None:
    """BuiltPrompt exposes system, user, and sources fields.

    R1 — BuiltPrompt has system: str and user: str.
    R2 — BuiltPrompt has sources: list[Source].
    """
    src = Source(n=1, title="Some Title", url="https://example.com/page")
    prompt = BuiltPrompt(
        system="You are helpful.",
        user="CONTEXTO:\n[1] Some Title\ntext\n(Fuente: ...)\n\nPREGUNTA:\nWhat?",
        sources=[src],
    )
    assert prompt.system == "You are helpful."
    assert "What?" in prompt.user
    assert len(prompt.sources) == 1
    assert prompt.sources[0].n == 1


def test_builtprompt_accepts_empty_sources() -> None:
    """BuiltPrompt is valid with sources=[].

    R22 (border case) — sources is an empty list when context is empty.
    """
    prompt = BuiltPrompt(
        system="System text.",
        user="CONTEXTO:\n(No hay contexto disponible.)\n\nPREGUNTA:\nHello?",
        sources=[],
    )
    assert prompt.sources == []


def test_models_exported() -> None:
    """BuiltPrompt and Source are importable from wowrag.models.

    R27 — wowrag.models re-exports BuiltPrompt and Source.
    """
    # The import at the top of this module already tests this; we also assert
    # the names appear in models.__all__ for belt-and-suspenders.
    import wowrag.models as m

    assert "Source" in m.__all__
    assert "BuiltPrompt" in m.__all__
