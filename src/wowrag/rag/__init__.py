"""RAG orchestration layer (f8): RagOrchestrator interface, domain exception,
and DefaultRagOrchestrator.

Re-exports for R27: consumers (f9) import from this package, not from internal
modules. ``Answer``/``AnswerMetadata`` live in ``wowrag.models``.
"""

from __future__ import annotations

from wowrag.rag.base import OrchestratorError, RagOrchestrator
from wowrag.rag.orchestrator import DefaultRagOrchestrator

__all__ = ["RagOrchestrator", "OrchestratorError", "DefaultRagOrchestrator"]
