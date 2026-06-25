"""DefaultRagOrchestrator: composes Retriever + PromptBuilder + LLMProvider.

Online query path — the step that ties everything together (retrieve -> prompt
-> generate) and applies the abstention short-circuit. Depends only on the
interfaces (Retriever, PromptBuilder, LLMProvider), so it is testable with
fakes/stubs without Postgres, GPU, Ollama, or network (R9, R22). Zero DB/ML/HTTP
imports. The abstention decision consumes f5's ``below_threshold`` signal — it
does NOT recompute the threshold (R18, R21).

f12 adds an optional Reranker that operates between the Retriever and the
PromptBuilder. When present and below_threshold=False, it reorders the chunks
before building the prompt (R19-R23).
"""

from __future__ import annotations

from wowrag.config import Settings
from wowrag.config import default_persona as resolve_default_persona
from wowrag.generation.prompt_builder_base import PromptBuilder
from wowrag.llm.base import LLMProvider
from wowrag.models import Answer, AnswerMetadata, RetrievalResult
from wowrag.personas import Persona
from wowrag.rag.base import OrchestratorError
from wowrag.retrieval.base import Retriever
from wowrag.retrieval.reranker import Reranker

# Abstention message — owned by f8 (f5 only exposed the boolean signal). (R15, R18)
_ABSTENTION_MESSAGE = (
    "No hay evidencia suficiente en los documentos para responder con seguridad."
)


class DefaultRagOrchestrator:
    """Orchestrator that composes Retriever + PromptBuilder + LLMProvider.

    Depends only on the interfaces (R9, R22): testable with fakes/stubs of the
    three dependencies, without Postgres, GPU, Ollama, or network. Abstention is
    modelled in the return type (``Answer.abstained``), never as an exception
    (docs/conventions.md).
    """

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm: LLMProvider,
        settings: Settings | None = None,
        reranker: Reranker | None = None,  # f12 (R19) — optional, None = no reranking
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm = llm
        self._settings = settings or Settings()
        self._reranker = reranker  # None -> flujo existente sin cambios (R22)

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        """Run the RAG pipeline for ``query`` and return a structured ``Answer``.

        Parameters
        ----------
        query:
            User's question. Empty/whitespace-only -> OrchestratorError (R25),
            raised BEFORE touching retrieve/build/generate.
        persona:
            Explicit persona override; None -> resolved via Settings.default_persona
            (R23). The resolved persona is reported in the metadata and passed to
            the PromptBuilder so the reported name matches the persona actually used.

        Returns
        -------
        Answer
            below_threshold=True  -> abstained=True, sources=[] (R14-R17).
            below_threshold=False -> abstained=False, answer=LLM text,
            sources=BuiltPrompt.sources (R2, R13, R19, R20).

        Raises
        ------
        OrchestratorError
            Empty/whitespace query (R25).
        Exception
            Infrastructure errors (RetrieverError, EmbeddingError,
            VectorStoreError, LLMError, PersonaNotFoundError) propagate as-is (R26).
        """
        # R25: validate query BEFORE touching any dependency.
        if not query or not query.strip():
            raise OrchestratorError("query must be a non-empty string")

        # R5/R23: resolve the effective persona ONCE. None -> Settings.default_persona
        # via the f0 helper (single source of truth). PersonaNotFoundError propagates
        # unmasked (R26). The same persona is reported in metadata and passed to build.
        effective_persona: Persona = (
            persona if persona is not None
            else resolve_default_persona(self._settings)
        )

        # R10: retrieve. Infra errors (RetrieverError/Embedding/Store) propagate (R26).
        result: RetrievalResult = self._retriever.retrieve(query)

        # R21: scores derived from the RetrievalResult; no recalculation/re-embed.
        scores = [rc.score for rc in result.chunks]

        # R14: short-circuit the LLM when f5's abstention signal is set.
        if result.below_threshold:
            return Answer(
                answer=_ABSTENTION_MESSAGE,                  # R15
                sources=[],                                  # R16
                abstained=True,                              # R14
                metadata=AnswerMetadata(
                    model=self._llm.model,                   # R4
                    persona=effective_persona.name,          # R5, R17
                    max_score=result.max_score,              # R6, R17
                    scores=scores,                           # R7
                ),
            )

        # f12 (R20, R21, R22): apply reranking when reranker is set and we have
        # results above threshold. When below_threshold=True the short-circuit above
        # already returned — so we are always in the "have results" branch here.
        # When self._reranker is None we skip this entirely (R22).
        if self._reranker is not None:
            rerank_result = self._reranker.rerank(
                query,
                result.chunks,
                top_n=self._settings.reranker_top_n,
            )
            # Build a temporary RetrievalResult with reranked chunks (R20).
            # max_score and below_threshold come from the original result so
            # the Answer contract (metadata) is unchanged (R23).
            result = RetrievalResult(
                chunks=rerank_result.chunks,
                max_score=result.max_score,
                below_threshold=result.below_threshold,
            )

        # R11: build the prompt with the resolved persona. PersonaNotFoundError
        # from f6/f0 propagates (R26).
        built = self._prompt_builder.build(query, result, effective_persona)

        # R12: flatten system+user into a single prompt and generate exactly once.
        prompt = f"{built.system}\n\n{built.user}"
        text = self._llm.generate(prompt)  # LLMError propagates (R26)

        # R13/R19/R20: grounded answer with f6's citations returned as-is.
        return Answer(
            answer=text,                                     # R2, R13
            sources=built.sources,                           # R3, R19, R20
            abstained=False,                                 # R13
            metadata=AnswerMetadata(
                model=self._llm.model,                       # R4
                persona=effective_persona.name,              # R5, R23
                max_score=result.max_score,                  # R6
                scores=scores,                               # R7
            ),
        )
