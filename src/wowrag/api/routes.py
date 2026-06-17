"""HTTP routes for the RAG API (f9): ``GET /health`` and ``POST /ask``.

Thin transport layer. NO retrieval / prompt / LLM logic and NO SQL or HTTP-to-
Ollama here: the route depends only on the ``RagOrchestrator`` Protocol
(injected via ``Depends``) and reuses ``Answer`` (f8) as the response model.

Handlers are **synchronous (`def`)** on purpose: ``RagOrchestrator.answer`` is
synchronous and potentially blocking (embeddings, pgvector query, HTTP to
Ollama), and FastAPI runs ``def`` handlers in its threadpool, so the event loop
is never blocked. No manual ``run_in_threadpool`` wrapper is needed (R22).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from wowrag.api.dependencies import get_orchestrator
from wowrag.api.schemas import AskRequest
from wowrag.embeddings.base import EmbeddingError
from wowrag.llm.base import LLMError
from wowrag.models import Answer
from wowrag.personas import Persona, PersonaNotFoundError, load_persona
from wowrag.rag import OrchestratorError, RagOrchestrator
from wowrag.retrieval.base import RetrieverError
from wowrag.store.base import VectorStoreError

logger = logging.getLogger(__name__)

router = APIRouter()

# Infrastructure failures from the lower layers -> 503 (upstream component down).
# These propagate unmasked from f8 (R26); f9 maps them to a clean 5xx (R17).
_INFRA_ERRORS = (RetrieverError, EmbeddingError, VectorStoreError, LLMError)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. 200 OK, no orchestrator / retriever / LLM / DB / network.

    (R3)
    """
    return {"status": "ok"}


def _resolve_persona(name: str | None) -> Persona | None:
    """Resolve a persona name to a ``Persona``; ``None`` -> ``None`` (R10, R11, R12).

    ``None`` is forwarded as-is so f8 resolves ``Settings.default_persona`` (the
    HTTP layer does not duplicate that default). An unknown name raises
    ``PersonaNotFoundError`` (mapped to 400 in :func:`ask`).
    """
    if name is None:
        return None  # R11: f8 resolves the default persona
    return load_persona(name)  # R10; PersonaNotFoundError -> 400 (R12)


@router.post("/ask", response_model=Answer)
def ask(
    body: AskRequest,  # R15: pydantic validation (empty/missing query -> 422)
    orchestrator: RagOrchestrator = Depends(get_orchestrator),  # R19
) -> Answer:
    """Run the RAG pipeline for ``body.query`` and return the f8 ``Answer``.

    Maps the answer 1:1 to JSON (R2, R4-R9). Error mapping (design §5): unknown
    persona / ``OrchestratorError`` -> 400; infrastructure failures -> 503; all
    error bodies are JSON, never stack traces (R12, R16, R17, R18).
    """
    try:
        persona = _resolve_persona(body.persona)  # str|None -> Persona|None
    except PersonaNotFoundError as exc:
        # R12: unknown persona -> 400 with a clean JSON body, no stack trace.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        # R4: invoke the orchestrator exactly once. R22: sync handler -> threadpool.
        return orchestrator.answer(body.query, persona)
    except HTTPException:
        raise
    except OrchestratorError as exc:
        # R16: orchestrator-level input error -> 400 with a clean JSON body.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except _INFRA_ERRORS as exc:
        # R17/R18: infrastructure failure -> 503, JSON body, no internal trace.
        logger.exception("orchestrator infrastructure failure")
        raise HTTPException(
            status_code=503, detail="upstream RAG component failed"
        ) from exc
    except Exception as exc:  # defensive catch-all: never leak a 500 + traceback
        # R18: any unexpected failure still returns a clean JSON 503, not HTML.
        logger.exception("unexpected orchestrator failure")
        raise HTTPException(
            status_code=503, detail="upstream RAG component failed"
        ) from exc
