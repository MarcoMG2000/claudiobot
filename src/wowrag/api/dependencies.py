"""Dependency injection for the HTTP API (f9).

``get_orchestrator`` is the FastAPI dependency the route depends on; it is typed
as the ``RagOrchestrator`` Protocol, never as the concrete impl, so tests can
override it via ``app.dependency_overrides`` with a fake (R19, R20).

``build_orchestrator`` is the single real composition point. Its imports of the
real implementations (bge-m3, pgvector, Ollama) are **lazy (inside the
function)**, so importing ``wowrag.api`` in tests never pulls torch / psycopg /
the Ollama HTTP client. Unit tests never reach this function because the
dependency is overridden (R20, R21). Mirrors the lazy-import strategy of
``OllamaLLM`` (f7), ``BgeM3Embeddings`` (f3) and ``PgVectorStore`` (f4).
"""

from __future__ import annotations

from wowrag.rag import RagOrchestrator  # the INTERFACE (Protocol), not the impl


def get_orchestrator() -> RagOrchestrator:
    """FastAPI dependency: provide the ``RagOrchestrator``.

    Overridable in tests via ``app.dependency_overrides[get_orchestrator]``
    (R19, R20). In real runtime it delegates to ``build_orchestrator``.
    """
    return build_orchestrator()


def build_orchestrator() -> RagOrchestrator:
    """Real composition point: assemble ``DefaultRagOrchestrator`` with real impls.

    Composes ``DefaultRetriever`` (bge-m3 embeddings + pgvector store) +
    ``DefaultPromptBuilder`` + ``OllamaLLM`` from ``Settings``. ALL heavy imports
    are lazy (inside this function) so importing the API package stays free of
    torch / psycopg / the HTTP client (R20). Unit tests never call this — the
    dependency is overridden with a fake (R20, R21).
    """
    # Lazy imports: only resolved at real runtime, never during unit tests.
    from wowrag.config import Settings
    from wowrag.embeddings.bge_m3 import BgeM3Embeddings
    from wowrag.generation.prompt_builder import DefaultPromptBuilder
    from wowrag.llm.ollama import OllamaLLM
    from wowrag.rag.orchestrator import DefaultRagOrchestrator
    from wowrag.retrieval.retriever import DefaultRetriever
    from wowrag.store.pgvector_store import PgVectorStore

    settings = Settings()

    embedder = BgeM3Embeddings(
        model_name=settings.embedding_model,
        dimension=settings.embedding_dim,
        batch_size=settings.embedding_batch_size,
        device=settings.embedding_device,
    )
    store = PgVectorStore(
        dsn=settings.postgres_dsn,
        dimension=settings.embedding_dim,
        table=settings.vector_table,
        metric=settings.distance_metric,
    )
    retriever = DefaultRetriever(embedder, store, settings)
    prompt_builder = DefaultPromptBuilder(settings)
    llm = OllamaLLM(model=settings.llm_model, base_url=settings.ollama_url)

    return DefaultRagOrchestrator(retriever, prompt_builder, llm, settings)
