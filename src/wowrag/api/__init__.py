"""HTTP API layer (f9): FastAPI app exposing the RAG pipeline over HTTP.

Re-exports ``create_app`` so consumers import from the package, not from the
internal ``app`` module. Importing this package is light: the real orchestrator
composition (bge-m3 / pgvector / Ollama) is built lazily inside
``dependencies.build_orchestrator`` and never runs during import or in tests.
"""

from __future__ import annotations

from wowrag.api.app import create_app

__all__ = ["create_app"]
