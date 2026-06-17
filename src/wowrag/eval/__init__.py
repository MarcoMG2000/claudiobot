"""Evaluation harness for the wow-classic-rag pipeline (f10).

Offline evaluation flow that COMPOSES the f8 ``RagOrchestrator``: runs a golden
dataset through the pipeline and aggregates metrics into a report. Lives in its
own package (like ``index/``) and depends only on public interfaces.

Public surface (R30): consumers import from ``wowrag.eval``, not from the internal
modules. Importing this package never pulls torch/psycopg/httpx — the heavy real
composition is lazy and lives in the CLI (Slice B).

NOTE (Slice A): the CLI entrypoint (``main``) is added in Slice B; this re-export
set covers the deterministic core only.
"""

from __future__ import annotations

from wowrag.eval.dataset import GoldenDatasetError, load_golden
from wowrag.eval.harness import EvalHarness
from wowrag.eval.metrics import (
    abstention_scores,
    faithfulness_llm_judge,
    faithfulness_proxy,
    faithfulness_proxy_mean,
    retrieval_hit_rate,
)
from wowrag.eval.models import EvalReport, GoldenItem

__all__ = [
    "GoldenItem",
    "EvalReport",
    "load_golden",
    "GoldenDatasetError",
    "EvalHarness",
    "retrieval_hit_rate",
    "faithfulness_proxy",
    "faithfulness_proxy_mean",
    "abstention_scores",
    "faithfulness_llm_judge",
]
