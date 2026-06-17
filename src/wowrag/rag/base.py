"""RagOrchestrator interface and domain exception for the orchestration layer.

``RagOrchestrator`` is the swap point (Protocol) that all orchestrator
implementations must satisfy. The concrete implementation is
``DefaultRagOrchestrator`` (composes Retriever + PromptBuilder + LLMProvider).
``OrchestratorError`` covers orchestrator input failures (empty query);
infrastructure errors from the lower layers propagate as-is (R26).
"""

from __future__ import annotations

from typing import Protocol

from wowrag.models import Answer
from wowrag.personas import Persona


class OrchestratorError(Exception):
    """Domain exception for orchestrator input failures.

    Raised for an empty/whitespace query, BEFORE touching retriever/prompt/LLM
    (R24, R25). Infrastructure errors from lower layers (RetrieverError,
    EmbeddingError, VectorStoreError, LLMError, PersonaNotFoundError) are NOT
    wrapped: they propagate as-is (R26). Abstention is a valid Answer, never an
    exception (docs/conventions.md).
    """


class RagOrchestrator(Protocol):
    """Swap point: query -> (retrieve -> [abstain] -> prompt -> generate) -> Answer.

    Concrete implementation: ``DefaultRagOrchestrator`` (composes Retriever +
    PromptBuilder + LLMProvider). Callers (f9) depend on this Protocol, never on
    a concrete impl.

    Contract
    --------
    - Empty/whitespace query -> OrchestratorError (no retrieve/prompt/LLM call).
    - below_threshold == True  -> abstain: Answer(abstained=True, sources=[]),
      WITHOUT calling PromptBuilder or LLMProvider (R14).
    - below_threshold == False -> build prompt + generate; Answer(abstained=False)
      with sources = BuiltPrompt.sources (R13, R19, R20).
    - Infrastructure errors propagate unmasked (R26).
    """

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        """Run the RAG pipeline for a query and return a structured Answer.

        persona=None -> resolved via Settings.default_persona (f0), used both to
        build the prompt and to report the persona name in the metadata.
        Empty/whitespace query -> OrchestratorError.
        """
        ...
