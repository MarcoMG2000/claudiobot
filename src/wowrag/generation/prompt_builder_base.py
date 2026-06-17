"""PromptBuilder Protocol and domain exception for f6.

The interface lives in its own module (NOT generation/base.py, which is reserved
for LLMProvider in f7) to keep one interface per file and avoid collision.
See design.md §3 for the rationale.
"""

from __future__ import annotations

from typing import Protocol

from wowrag.models import BuiltPrompt, RetrievalResult
from wowrag.personas import Persona


class PromptBuilderError(Exception):
    """Domain exception for prompt-builder input failures.

    Raised for an empty/whitespace query (R8, R25). A missing persona surfaces as
    PersonaNotFoundError from the f0 loader and is NOT wrapped here (R24, R26).
    """


class PromptBuilder(Protocol):
    """Swap point: (query + RetrievalResult + persona) -> BuiltPrompt.

    Concrete implementation: DefaultPromptBuilder. Callers (f8/f9) depend on
    this Protocol, never on a concrete impl.

    Contract:
    - persona=None  -> resolves Settings.default_persona via default_persona() (f0).
    - Empty query   -> PromptBuilderError (R8).
    - Empty context -> BuiltPrompt valid with sources=[] (R21); does NOT abstain (f8).
    - Missing persona -> PersonaNotFoundError propagated, NOT wrapped (R24, R26).

    f6 builds the prompt STRINGS only; it does NOT call any LLM (f7),
    orchestrate, or decide abstention (f8).
    """

    def build(
        self,
        query: str,
        result: RetrievalResult,
        persona: Persona | None = None,
    ) -> BuiltPrompt:
        """Build the system+user prompt with persona, grounding and citable context.

        Parameters
        ----------
        query:   User's question (non-empty; raises PromptBuilderError if blank).
        result:  RetrievalResult from f5 (already retrieved; f6 does not retrieve).
        persona: Explicit persona override; None -> Settings.default_persona (R10, R11).

        Returns
        -------
        BuiltPrompt with system (persona style + grounding) and user
        (query + formatted context with [n] markers) and sources list (R2, R5, R19).
        """
        ...
