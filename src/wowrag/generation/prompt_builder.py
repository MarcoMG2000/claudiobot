"""DefaultPromptBuilder — concrete implementation of the PromptBuilder Protocol.

Composes persona style + strict grounding instructions into a system prompt, and
formats the retrieved context with numbered citation markers into the user prompt.

No imports of LLM/network/DB/ML — fully testable without Postgres, GPU, or
network (R7). Persona resolution delegates to f0's default_persona() helper (R10,
R23). PersonaNotFoundError propagates unmasked (R24, R26).
"""

from __future__ import annotations

from wowrag.config import Settings
from wowrag.config import default_persona as resolve_default_persona
from wowrag.generation.prompt_builder_base import PromptBuilderError
from wowrag.models import BuiltPrompt, RetrievalResult, Source
from wowrag.personas import Persona

# ---------------------------------------------------------------------------
# Grounding instructions — module-level constants, persona-independent (R16).
# These three sentences implement R13, R14, and R15 respectively.
# ---------------------------------------------------------------------------
_GROUNDING_INSTRUCTIONS = (
    "Responde ÚNICAMENTE con la información del CONTEXTO de abajo. "       # R13
    "No uses conocimiento externo ni inventes datos. "                     # R13
    "Si el CONTEXTO no contiene evidencia suficiente para responder, dilo "  # R14
    "explícitamente en lugar de inventar. "                                # R14
    "Cita cada afirmación con su marcador [n] correspondiente del CONTEXTO."  # R15
)

_NO_CONTEXT_NOTICE = "(No hay contexto disponible.)"  # R21


class DefaultPromptBuilder:
    """Builds a BuiltPrompt from (query, RetrievalResult, persona).

    Depends only on models / persona / Settings (R7): testable without network,
    GPU, or Postgres. Does NOT call any LLM nor decide abstention (f7/f8 boundary).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def build(
        self,
        query: str,
        result: RetrievalResult,
        persona: Persona | None = None,
    ) -> BuiltPrompt:
        """Build system+user prompt with persona, grounding, and citable context.

        Raises PromptBuilderError for empty/whitespace query (R8).
        PersonaNotFoundError from the persona loader propagates unmasked (R24, R26).
        """
        if not query or not query.strip():
            raise PromptBuilderError("query must be a non-empty string")  # R8

        # R10/R11/R23/R24: explicit persona wins; None -> resolve from config.
        # default_persona() can raise PersonaNotFoundError -> propagates (R24, R26).
        resolved: Persona = (
            persona if persona is not None
            else resolve_default_persona(self._settings)
        )

        system = self._build_system(resolved)                       # R3, R12, R13-R16
        context_block, sources = self._format_context(result)      # R17-R22
        user = self._build_user(query, context_block)              # R4, R9

        return BuiltPrompt(system=system, user=user, sources=sources)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_system(self, persona: Persona) -> str:
        """Combine persona style with grounding instructions (R3, R12, R13-R16).

        Grounding block is always appended regardless of persona (R16).
        """
        return f"{persona.system_style}\n\n{_GROUNDING_INSTRUCTIONS}"

    def _format_context(
        self, result: RetrievalResult
    ) -> tuple[str, list[Source]]:
        """Format retrieved chunks into a numbered citation block (R17-R22).

        Returns (context_text, sources). sources is [] when result.chunks is empty
        (R21). Each chunk yields exactly one Source entry aligned with its [n]
        marker (R5, R19, R22). Only chunk data is used — no external facts (R20).
        """
        if not result.chunks:  # R21
            return _NO_CONTEXT_NOTICE, []

        lines: list[str] = []
        sources: list[Source] = []
        for i, rc in enumerate(result.chunks, start=1):  # R17: 1-indexed, score-desc order
            # R18/R20: ONLY data from RetrievedChunk (text, title, source_url)
            lines.append(
                f"[{i}] {rc.title}\n{rc.chunk.text}\n(Fuente: {rc.source_url})"
            )
            sources.append(Source(n=i, title=rc.title, url=rc.source_url))  # R5, R19, R22

        return "\n\n".join(lines), sources

    def _build_user(self, query: str, context_block: str) -> str:
        """Combine context block with the literal query (R4, R9, R20).

        Context comes first so the model sees evidence before the question.
        """
        return f"CONTEXTO:\n{context_block}\n\nPREGUNTA:\n{query}"
