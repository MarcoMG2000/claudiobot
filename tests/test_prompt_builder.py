"""Tests for DefaultPromptBuilder (f6-prompt-builder).

All tests are DB-free, GPU-free, and network-free. They construct
RetrievalResult/RetrievedChunk objects by hand and rely on the real persona YAML
files from f0 (simple/orc/troll).

Traceability: each test is annotated with its R<n> requirement(s).
"""

from __future__ import annotations

import pytest

from wowrag.config import Settings
from wowrag.generation import DefaultPromptBuilder, PromptBuilder, PromptBuilderError
from wowrag.models import Chunk, RetrievalResult, RetrievedChunk
from wowrag.personas import PersonaNotFoundError, load_persona


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str,
    text: str,
    source_url: str,
    title: str,
    section: str = "",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_url=source_url,
        title=title,
        section=section,
    )


def _make_retrieved_chunk(
    n: int,
    text: str = "Some chunk text.",
    source_url: str | None = None,
    title: str | None = None,
    score: float = 0.9,
) -> RetrievedChunk:
    url = source_url or f"https://www.wowhead.com/chunk/{n}"
    ttl = title or f"Title {n}"
    chunk = _make_chunk(
        chunk_id=f"chunk-{n}",
        text=text,
        source_url=url,
        title=ttl,
    )
    return RetrievedChunk(chunk=chunk, score=score)


def _make_result(
    n_chunks: int = 2,
    chunks: list[RetrievedChunk] | None = None,
    below_threshold: bool = False,
) -> RetrievalResult:
    """Build a RetrievalResult with n_chunks auto-generated chunks (score desc)."""
    if chunks is None:
        chunks = [
            _make_retrieved_chunk(i, score=1.0 - i * 0.1)
            for i in range(1, n_chunks + 1)
        ]
    max_score = chunks[0].score if chunks else 0.0
    return RetrievalResult(
        chunks=chunks,
        max_score=max_score,
        below_threshold=below_threshold,
    )


def _settings_simple() -> Settings:
    """Settings with default_persona='simple', no .env file."""
    return Settings(_env_file=None, default_persona="simple")


def _settings_orc() -> Settings:
    """Settings with default_persona='orc', no .env file."""
    return Settings(_env_file=None, default_persona="orc")


# ---------------------------------------------------------------------------
# R8 — Empty / whitespace query raises PromptBuilderError
# ---------------------------------------------------------------------------


def test_empty_query_raises() -> None:
    """Empty string and whitespace-only query both raise PromptBuilderError.

    R8 — build("", ...) and build("   ", ...) raise PromptBuilderError.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()

    with pytest.raises(PromptBuilderError):
        builder.build("", result)

    with pytest.raises(PromptBuilderError):
        builder.build("   ", result)


# ---------------------------------------------------------------------------
# R9 — User prompt contains the literal query text
# ---------------------------------------------------------------------------


def test_user_contains_query() -> None:
    """The literal query text appears in BuiltPrompt.user.

    R9 — build(query, result).user includes query literal.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()
    query = "What spell does a fire mage use?"

    prompt = builder.build(query, result)

    assert query in prompt.user


# ---------------------------------------------------------------------------
# R3, R4 — system and user are non-empty after construction
# ---------------------------------------------------------------------------


def test_system_and_user_nonempty() -> None:
    """Both system and user are non-empty strings after build().

    R3 — BuiltPrompt.system is non-empty.
    R4 — BuiltPrompt.user is non-empty.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()

    prompt = builder.build("What is a fireball?", result)

    assert prompt.system.strip() != ""
    assert prompt.user.strip() != ""


# ---------------------------------------------------------------------------
# R10, R23 — Default persona resolved from Settings.default_persona
# ---------------------------------------------------------------------------


def test_default_persona_from_config() -> None:
    """When build() is called without persona, uses Settings.default_persona.

    R10 — persona=None resolves from Settings.default_persona.
    R23 — Uses existing Settings.default_persona field (no new config fields).
    """
    settings = _settings_orc()
    builder = DefaultPromptBuilder(settings=settings)
    result = _make_result()
    orc_persona = load_persona("orc")

    prompt = builder.build("What is a fireball?", result)

    assert orc_persona.system_style in prompt.system


# ---------------------------------------------------------------------------
# R11 — Explicit persona overrides Settings.default_persona
# ---------------------------------------------------------------------------


def test_explicit_persona_overrides_config() -> None:
    """Explicit persona argument wins over Settings.default_persona.

    R11 — build(..., persona=troll) uses troll style, ignores default_persona.
    """
    settings = _settings_simple()
    builder = DefaultPromptBuilder(settings=settings)
    result = _make_result()

    troll_persona = load_persona("troll")
    simple_persona = load_persona("simple")

    prompt = builder.build("What is a fireball?", result, persona=troll_persona)

    assert troll_persona.system_style in prompt.system
    assert simple_persona.system_style not in prompt.system


# ---------------------------------------------------------------------------
# R12 — Persona system_style is injected into system prompt
# ---------------------------------------------------------------------------


def test_persona_style_injected() -> None:
    """system_style of the resolved persona appears in BuiltPrompt.system.

    Changing persona changes the style text.

    R12 — system includes persona.system_style; different personas give different text.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()

    simple_persona = load_persona("simple")
    orc_persona = load_persona("orc")

    prompt_simple = builder.build("question", result, persona=simple_persona)
    prompt_orc = builder.build("question", result, persona=orc_persona)

    assert simple_persona.system_style in prompt_simple.system
    assert orc_persona.system_style in prompt_orc.system
    # Different personas produce different system text.
    assert prompt_simple.system != prompt_orc.system


# ---------------------------------------------------------------------------
# R13, R14, R15 — All three grounding instructions present in system
# ---------------------------------------------------------------------------


def test_grounding_instructions_present() -> None:
    """system prompt contains all three grounding instructions.

    R13 — Instruction to respond ONLY from context (no external knowledge).
    R14 — Instruction to declare insufficient evidence rather than hallucinate.
    R15 — Instruction to cite claims with [n] markers.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()

    prompt = builder.build("What is Fireball?", result)
    system = prompt.system

    # R13: respond only from provided context
    assert "ÚNICAMENTE" in system or "conocimiento externo" in system
    # R14: declare lack of evidence
    assert "evidencia suficiente" in system
    # R15: cite with [n] markers
    assert "[n]" in system or "marcador" in system


# ---------------------------------------------------------------------------
# R16 — Grounding instructions are persona-independent
# ---------------------------------------------------------------------------


def test_grounding_independent_of_persona() -> None:
    """Changing persona does NOT remove or weaken grounding instructions.

    R16 — All three grounding clauses present for simple, orc, and troll.
    """
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()
    personas = [load_persona("simple"), load_persona("orc"), load_persona("troll")]

    for persona in personas:
        prompt = builder.build("Question?", result, persona=persona)
        system = prompt.system
        # R13
        assert "ÚNICAMENTE" in system or "conocimiento externo" in system, (
            f"R13 grounding missing for persona={persona.name}"
        )
        # R14
        assert "evidencia suficiente" in system, (
            f"R14 grounding missing for persona={persona.name}"
        )
        # R15
        assert "[n]" in system or "marcador" in system, (
            f"R15 grounding missing for persona={persona.name}"
        )


# ---------------------------------------------------------------------------
# R17 — Sequential [1]..[N] citation markers in user prompt
# ---------------------------------------------------------------------------


def test_context_has_sequential_citation_markers() -> None:
    """user prompt contains [1]..[N] in order, 1-indexed, same order as result.chunks.

    R17 — Each chunk gets a sequential [n] marker starting at [1].
    """
    n_chunks = 3
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result(n_chunks=n_chunks)

    prompt = builder.build("question", result)

    for i in range(1, n_chunks + 1):
        assert f"[{i}]" in prompt.user, f"Marker [{i}] missing in user prompt"


# ---------------------------------------------------------------------------
# R18 — Context includes chunk.text, source_url, and title per chunk
# ---------------------------------------------------------------------------


def test_context_includes_chunk_text_and_url() -> None:
    """For each chunk, text, source_url, and title appear in the context block.

    R18 — Context includes chunk.text and source_url (and title).
    """
    rc = _make_retrieved_chunk(
        1,
        text="Fireball deals fire damage.",
        source_url="https://www.wowhead.com/spell=133/fireball",
        title="Fireball - Spell",
    )
    result = _make_result(chunks=[rc])
    builder = DefaultPromptBuilder(settings=_settings_simple())

    prompt = builder.build("question", result)

    assert "Fireball deals fire damage." in prompt.user
    assert "https://www.wowhead.com/spell=133/fireball" in prompt.user
    assert "Fireball - Spell" in prompt.user


# ---------------------------------------------------------------------------
# R5, R19, R22 — sources list aligns exactly with [n] markers
# ---------------------------------------------------------------------------


def test_sources_match_markers() -> None:
    """Each [n] marker in user has exactly one Source(n=n, url=source_url).

    len(sources) == number of chunks formatted in context.

    R5  — sources[n].n matches [n] marker in context.
    R19 — Each [n] has exactly one Source with the chunk's source_url.
    R22 — len(sources) == number of chunks cited.
    """
    chunks = [
        _make_retrieved_chunk(
            i,
            source_url=f"https://www.wowhead.com/page/{i}",
            title=f"Page {i}",
            score=1.0 - i * 0.1,
        )
        for i in range(1, 4)
    ]
    result = _make_result(chunks=chunks)
    builder = DefaultPromptBuilder(settings=_settings_simple())

    prompt = builder.build("question", result)

    assert len(prompt.sources) == len(chunks)  # R22
    for i, src in enumerate(prompt.sources, start=1):
        assert src.n == i, f"Source {i}: n mismatch"  # R5
        assert src.url == f"https://www.wowhead.com/page/{i}", (  # R19
            f"Source {i}: url mismatch"
        )


# ---------------------------------------------------------------------------
# R20 — Context only contains data from result.chunks (no external facts)
# ---------------------------------------------------------------------------


def test_context_only_from_result() -> None:
    """The context block contains no URLs/titles absent from result.chunks.

    R20 — Only data from RetrievedChunk instances is injected into the prompt.
    """
    known_url = "https://www.wowhead.com/spell=133/fireball"
    known_title = "Fireball - Spell"
    rc = _make_retrieved_chunk(
        1,
        source_url=known_url,
        title=known_title,
        text="Deals fire damage.",
    )
    result = _make_result(chunks=[rc])
    builder = DefaultPromptBuilder(settings=_settings_simple())

    prompt = builder.build("question", result)

    # Only the known URL appears in the user prompt; no foreign URLs.
    import re

    found_urls = re.findall(r"https?://[^\s)\"']+", prompt.user)
    for url in found_urls:
        assert url == known_url, f"Unexpected URL in context: {url}"


# ---------------------------------------------------------------------------
# R21 — Empty context builds a valid prompt with sources=[] without exception
# ---------------------------------------------------------------------------


def test_empty_context_builds_valid_prompt() -> None:
    """result.chunks=[] produces a valid BuiltPrompt, sources=[], no exception.

    R21 — Empty context -> BuiltPrompt valid, user indicates no context, sources=[].
    """
    result = _make_result(n_chunks=0, chunks=[])
    builder = DefaultPromptBuilder(settings=_settings_simple())

    prompt = builder.build("Any question?", result)

    assert prompt.sources == []
    assert prompt.system.strip() != ""
    assert prompt.user.strip() != ""
    # user should indicate absence of context (R21)
    assert "contexto" in prompt.user.lower() or "disponible" in prompt.user.lower()


# ---------------------------------------------------------------------------
# R24, R26 — PersonaNotFoundError propagates unmasked
# ---------------------------------------------------------------------------


def test_missing_persona_propagates() -> None:
    """PersonaNotFoundError is not wrapped as PromptBuilderError or a blank prompt.

    R24 — If configured persona doesn't exist, PersonaNotFoundError propagates.
    R26 — PersonaNotFoundError is NOT masked as PromptBuilderError.
    """
    settings = Settings(_env_file=None, default_persona="does_not_exist")
    builder = DefaultPromptBuilder(settings=settings)
    result = _make_result()

    with pytest.raises(PersonaNotFoundError):
        builder.build("question", result)


# ---------------------------------------------------------------------------
# R7 — Builder depends only on models/persona/Settings (no LLM/DB/GPU/net)
# ---------------------------------------------------------------------------


def test_builder_depends_only_on_models() -> None:
    """DefaultPromptBuilder() and build() work without LLMProvider/Retriever/etc.

    R7 — Constructable and callable with zero LLM/Retriever/VectorStore/Embeddings.
    """
    # No LLMProvider, Retriever, VectorStore or EmbeddingProvider imported or used.
    builder = DefaultPromptBuilder(settings=_settings_simple())
    result = _make_result()

    # Must succeed without any external service
    prompt = builder.build("Tell me about frost nova.", result)

    assert prompt.system
    assert prompt.user
    assert isinstance(prompt.sources, list)


# ---------------------------------------------------------------------------
# R27 — Re-exports from wowrag.generation package
# ---------------------------------------------------------------------------


def test_exports_from_package() -> None:
    """PromptBuilder, PromptBuilderError, DefaultPromptBuilder are importable
    from wowrag.generation.

    R27 — generation.__init__ re-exports the three names.
    """
    from wowrag.generation import (  # noqa: F401  (import-test)
        DefaultPromptBuilder as DPB,
        PromptBuilder as PB,
        PromptBuilderError as PBE,
    )

    assert PB is PromptBuilder
    assert PBE is PromptBuilderError
    assert DPB is DefaultPromptBuilder
