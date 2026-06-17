"""Evaluation runner: drives a RagOrchestrator over a golden dataset (R6, R7).

``EvalHarness`` depends only on the ``RagOrchestrator`` Protocol (f8) injected at
construction (R6), so it is testable with a fake orchestrator — no Postgres, GPU,
Ollama, or network (R29). It calls ``answer`` exactly once per item (R7) and
aggregates the pure metric functions into an ``EvalReport``. Zero DB/ML/network
imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wowrag.eval.metrics import (
    Pair,
    abstention_scores,
    count_excluded_abstained,
    faithfulness_llm_judge,
    faithfulness_proxy_mean,
    retrieval_hit_rate,
)
from wowrag.eval.models import EvalReport, GoldenItem

if TYPE_CHECKING:  # interfaces only; no heavy imports at module load (R29)
    from wowrag.llm.base import LLMProvider
    from wowrag.rag.base import RagOrchestrator


class EvalHarness:
    """Runs a golden dataset through a ``RagOrchestrator`` and aggregates metrics.

    Depends only on the ``RagOrchestrator`` Protocol (R6): construct it with a
    fake orchestrator in tests — no Postgres/GPU/Ollama/network (R29).
    """

    def __init__(self, orchestrator: RagOrchestrator) -> None:
        self._orchestrator = orchestrator

    def run(
        self,
        items: list[GoldenItem],
        judge: LLMProvider | None = None,
    ) -> EvalReport:
        """Evaluate ``items`` and return an aggregated ``EvalReport``.

        Calls ``orchestrator.answer(item.question)`` exactly once per item (R7)
        and keeps each returned ``Answer`` unmodified. Aggregates hit-rate
        (R8-R11), the faithfulness proxy (R12-R14), the abstention metrics
        (R18-R21), and — only when a ``judge`` is supplied — the optional LLM
        judge (R15-R17). With no judge, ``faithfulness_llm`` stays ``None`` and no
        LLM is ever contacted (R16).
        """
        pairs: list[Pair] = [
            (item, self._orchestrator.answer(item.question))  # one call/item (R7)
            for item in items
        ]
        abstention = abstention_scores(pairs)  # precision/recall + corpus counts
        return EvalReport(
            total=len(pairs),
            in_corpus=abstention["in_corpus"],
            out_of_corpus=abstention["out_of_corpus"],
            excluded_abstained=count_excluded_abstained(pairs),  # R14
            hit_rate=retrieval_hit_rate(pairs),                  # R8-R11
            faithfulness_proxy=faithfulness_proxy_mean(pairs),   # R12-R14
            faithfulness_llm=(
                faithfulness_llm_judge(pairs, judge)             # R15-R17
                if judge is not None
                else None                                        # R16
            ),
            abstention_precision=abstention["abstention_precision"],  # R19, R20
            abstention_recall=abstention["abstention_recall"],        # R19, R20
        )
