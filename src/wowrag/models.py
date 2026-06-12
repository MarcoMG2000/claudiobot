"""Shared domain models for the wow-classic-rag pipeline.

This module is the single home for all data-layer pydantic models.
``Document`` is created in f1; ``Chunk``, ``RetrievedChunk`` and ``Answer``
will be added by later features (f2, f3, …).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


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
