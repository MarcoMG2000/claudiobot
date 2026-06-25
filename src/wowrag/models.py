"""Shared domain models for the wow-classic-rag pipeline.

This module is the single home for all data-layer pydantic models.
``Document`` is created in f1; ``Chunk`` in f2; ``RetrievedChunk`` and
``RetrievalResult`` in f5; ``Source`` and ``BuiltPrompt`` in f6;
``Answer`` and ``AnswerMetadata`` in f8 (the RAG orchestrator);
``RerankResult`` in f12 (the reranking layer).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

__all__ = [
    "Document",
    "Chunk",
    "RetrievedChunk",
    "RetrievalResult",
    "Source",          # f6
    "BuiltPrompt",     # f6
    "AnswerMetadata",  # f8
    "Answer",          # f8
    "RerankResult",    # f12
]


class Document(BaseModel):
    """A single source document: raw text plus wowhead-style metadata.

    Fields
    ------
    text        : The full body text of the document (required, non-blank).
    source_url  : Canonical URL of the wowhead page this document came from.
    title       : Human-readable page title (e.g. "Fireball - Spell").
    section     : Sub-section heading within the page (optional, default "").
    """

    text: str
    source_url: str
    title: str
    section: str = ""

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be a non-empty string")
        return v


class Chunk(BaseModel):
    """Un fragmento de texto derivado de un Document, con metadata heredada.

    Fields
    ------
    chunk_id   : Identificador estable (determinista) de este chunk.
    text       : Fragmento de texto (obligatorio, no vacío).
    source_url : Heredado de Document; necesario para citas aguas abajo.
    title      : Heredado de Document.
    section    : Heredado de Document.
    """

    chunk_id: str
    text: str
    source_url: str
    title: str
    section: str

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be a non-empty string")
        return v


class RetrievedChunk(BaseModel):
    """Un hit de recuperación citable: el Chunk recuperado + su score de coseno.

    Wrapper de nivel superior sobre el par (Chunk, float) de
    VectorStore.similarity_search. Expone la metadata de cita delegando en chunk,
    de modo que f6/f8 puedan construir citas sin desempaquetar el Chunk interno.
    """

    chunk: Chunk
    score: float  # R3: conservado tal cual de similarity_search, sin recalcular.

    @property
    def source_url(self) -> str:  # R2
        return self.chunk.source_url

    @property
    def title(self) -> str:  # R2
        return self.chunk.title

    @property
    def section(self) -> str:  # R2
        return self.chunk.section


class RetrievalResult(BaseModel):
    """Resultado de una recuperación: chunks (score desc) + señal de abstención.

    f5 SOLO computa y EXPONE below_threshold. El mensaje de abstención, el prompt
    y la llamada al LLM viven en f6/f7/f8, que CONSUMEN esta señal.
    """

    chunks: list[RetrievedChunk]  # ordenados por score desc (R4, R13)
    max_score: float              # score del mejor chunk, o 0.0 si vacío (R5, R20)
    below_threshold: bool         # True si max_score < score_threshold (R6, R7, R20)


class Source(BaseModel):
    """Una fuente citable, numerada para enlazar con el marcador [n] del prompt.

    Forma estable de cita del proyecto: n + title + url (docs/conventions.md).
    f9 la devolverá en la respuesta de la API como {n, title, url}.
    """

    n: int    # número de cita, 1-indexado, coincide con [n] en el prompt (R5, R19)
    title: str
    url: str  # source_url de wowhead del RetrievedChunk citado


class BuiltPrompt(BaseModel):
    """El prompt construido: system + user + las fuentes numeradas que cita.

    f6 produce este objeto; f8 pasa system/user al LLMProvider (f7) y devuelve
    sources en la respuesta final. f6 NO llama al LLM.
    """

    system: str                # estilo de persona + grounding estricto (R3, R12, R13-R16)
    user: str                  # pregunta + contexto formateado con [n] (R4, R9, R17)
    sources: list[Source]      # una por chunk citado; [] si contexto vacío (R2, R22)


class AnswerMetadata(BaseModel):
    """Metadata de diagnóstico de una respuesta RAG (f8).

    Incluye el modelo LLM usado, la persona resuelta y los scores de
    recuperación. f9 la serializa a JSON en la respuesta de la API.
    """

    model: str            # nombre del modelo LLM (LLMProvider.model) (R4)
    persona: str          # nombre de la persona resuelta (R5)
    max_score: float      # mejor score de recuperación, 0.0 si vacío (R6)
    scores: list[float]   # scores por fuente, alineados con sources [n] (R7)


class Answer(BaseModel):
    """Respuesta estructurada final del pipeline RAG (f8).

    abstained=True  -> answer es el mensaje de abstención y sources=[] (R14-R16).
    abstained=False -> answer es el texto del LLM y sources son las citas (R2, R19).
    f9 la serializa a JSON: {answer, sources, abstained, metadata}.
    """

    answer: str                 # texto del LLM, o mensaje de abstención (R2, R15)
    sources: list[Source]       # citas [n]; [] si abstención (R3, R16, R19, R20)
    abstained: bool             # True si se abstuvo por below_threshold (R14)
    metadata: AnswerMetadata    # modelo, persona, scores (R4-R7, R17)


class RerankResult(BaseModel):
    """Resultado de una operación de reranking (f12).

    chunks: lista de RetrievedChunk en el orden producido por el reranker
            (puede diferir del orden de score-desc del retriever).
    top_n: número efectivo de chunks devueltos (len(chunks)).
    reranker_model: identificador del modelo usado; None para PassthroughReranker.
    """

    chunks: list[RetrievedChunk]   # en el orden producido por el reranker (R3)
    top_n: int                     # número de chunks devueltos (R3, R4)
    reranker_model: str | None     # None para PassthroughReranker (R3, R7)
