"""CLI entrypoint for the f10 evaluation harness (R24-R26).

Runs the golden dataset through a ``RagOrchestrator`` and emits an ``EvalReport``:
a human-readable summary to stdout (R24) and, optionally, a JSON artifact via
``--out`` (R25).

The real orchestrator (bge-m3 + pgvector + Ollama) is composed **lazily** in
``_build_orchestrator`` — its only heavy import (``build_orchestrator`` from f9)
lives inside the function (R26). So importing ``wowrag.eval`` / ``wowrag.eval.cli``
never pulls torch / psycopg / the Ollama HTTP client, and the import-isolation
guarantee from Slice A holds. ``main`` takes an **injectable** orchestrator so unit
tests pass a fake and never build the real stack — zero DB/ML/Ollama/network in
the default suite (R29).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from wowrag.eval.dataset import load_golden
from wowrag.eval.harness import EvalHarness
from wowrag.eval.models import EvalReport

if TYPE_CHECKING:  # interfaces only; no heavy imports at module load (R26)
    from wowrag.rag.base import RagOrchestrator


def _build_orchestrator() -> RagOrchestrator:
    """Real composition point — LAZY heavy imports (R26).

    Reuses f9's ``build_orchestrator`` (bge-m3 + pgvector + Ollama) so the real
    wiring is not duplicated (DRY) and the production config/grounding is reused.
    The import is INSIDE the function so importing ``wowrag.eval`` /
    ``wowrag.eval.cli`` never pulls torch / psycopg / httpx (R26); the heavy
    dependencies resolve only when the script actually runs without an injected
    orchestrator.
    """
    from wowrag.api.dependencies import build_orchestrator

    return build_orchestrator()


def _default_dataset_path() -> Path | None:
    """Default dataset path from ``Settings.eval_dataset_path`` (R28), or ``None``.

    ``None`` lets ``load_golden`` fall back to the committed fixture. Reading
    ``Settings`` here is lazy (inside the function) so importing the CLI module
    stays free of config side effects; ``None`` means "use the fixture".
    """
    from wowrag.config import Settings

    configured = Settings().eval_dataset_path
    return Path(configured) if configured else None


def _format_summary(report: EvalReport) -> str:
    """Render a human-readable stdout summary of an ``EvalReport`` (R24)."""

    def _pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.3f}"

    return "\n".join(
        [
            "=== wowrag eval report ===",
            f"items evaluated   : {report.total}",
            f"  in-corpus       : {report.in_corpus}",
            f"  out-of-corpus   : {report.out_of_corpus}",
            f"  excluded (abst.): {report.excluded_abstained}",
            f"retrieval hit-rate: {_pct(report.hit_rate)}",
            f"faithfulness proxy: {_pct(report.faithfulness_proxy)}",
            f"faithfulness (LLM): {_pct(report.faithfulness_llm)}",
            f"abstention prec.  : {_pct(report.abstention_precision)}",
            f"abstention recall : {_pct(report.abstention_recall)}",
        ]
    )


def main(
    argv: list[str] | None = None,
    orchestrator: RagOrchestrator | None = None,
) -> int:
    """Run the evaluation harness and emit the report (R24-R26).

    Parses ``--dataset`` (default: ``Settings.eval_dataset_path`` or the committed
    fixture) and ``--out`` (optional JSON artifact path). Loads the golden dataset,
    runs ``EvalHarness`` over an orchestrator, prints a stdout summary (R24) and,
    when ``--out`` is given, writes the serialized ``EvalReport`` JSON there (R25).

    ``orchestrator`` is **injectable** (R29): when provided, the real composition
    point is never reached, so unit tests pass a ``FakeOrchestrator`` and never
    build the real stack. When ``None``, the real orchestrator is built lazily via
    ``_build_orchestrator`` (R26).
    """
    parser = argparse.ArgumentParser(prog="python -m wowrag.eval")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to a golden JSONL dataset (default: configured path or fixture).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the EvalReport as JSON.",
    )
    args = parser.parse_args(argv)

    dataset_path = args.dataset if args.dataset is not None else _default_dataset_path()
    items = load_golden(dataset_path)

    # Injected orchestrator short-circuits the real (lazy, heavy) composition (R29).
    orch = orchestrator if orchestrator is not None else _build_orchestrator()
    report = EvalHarness(orch).run(items)

    print(_format_summary(report))  # stdout summary (R24)
    if args.out is not None:  # R25
        args.out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return 0
