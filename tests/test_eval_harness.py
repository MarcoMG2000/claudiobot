"""Tests for the EvalHarness runner (f10-evaluation-harness).

Trazabilidad: R6 (DI / Protocol-only), R7 (one call per item), R22 (aggregated
report), R23 (JSON-serializable), R29 (network-free fakes). All run with a fake
orchestrator that implements the RagOrchestrator Protocol — no Postgres, GPU,
Ollama, or network.
"""

from __future__ import annotations

import json

import pytest

from wowrag.eval import EvalHarness, EvalReport, GoldenItem
from wowrag.models import Answer, AnswerMetadata, Source
from wowrag.personas import Persona


# ---------------------------------------------------------------------------
# FakeOrchestrator — implements the RagOrchestrator Protocol (R6, R29)
# ---------------------------------------------------------------------------

class FakeOrchestrator:
    """Maps question -> predefined Answer; counts calls. No network (R6, R29).

    Implements the RagOrchestrator Protocol structurally (a single ``answer``
    method), so EvalHarness can be built with it without touching the concrete
    DefaultRagOrchestrator.
    """

    def __init__(self, answers: dict[str, Answer]) -> None:
        self._answers = answers
        self.calls: list[str] = []

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        self.calls.append(query)
        return self._answers[query]


def _meta() -> AnswerMetadata:
    return AnswerMetadata(model="fake-llm", persona="default", max_score=0.9, scores=[0.9])


def _answer(text: str, urls: list[str], abstained: bool = False) -> Answer:
    sources = [Source(n=i + 1, title=f"T{i}", url=u) for i, u in enumerate(urls)]
    return Answer(answer=text, sources=sources, abstained=abstained, metadata=_meta())


def _dataset() -> tuple[list[GoldenItem], FakeOrchestrator]:
    items = [
        GoldenItem(
            question="What does Fireball do?",
            expected_urls=["https://a"],
            in_corpus=True,
            reference_answer="Fireball deals fire damage",
        ),
        GoldenItem(question="Off-topic question?", expected_urls=[], in_corpus=False),
    ]
    orch = FakeOrchestrator(
        {
            "What does Fireball do?": _answer(
                "Fireball deals fire damage", ["https://a"], abstained=False
            ),
            "Off-topic question?": _answer("I cannot answer", [], abstained=True),
        }
    )
    return items, orch


# ---------------------------------------------------------------------------
# R7 — one orchestrator call per GoldenItem
# ---------------------------------------------------------------------------

def test_run_calls_orchestrator_once_per_item():
    """R7: answer() is invoked exactly once per GoldenItem, in order."""
    items, orch = _dataset()

    EvalHarness(orch).run(items)

    assert orch.calls == ["What does Fireball do?", "Off-topic question?"]
    assert len(orch.calls) == len(items)


# ---------------------------------------------------------------------------
# R6 / R22 — depends only on the Protocol and produces an aggregated report
# ---------------------------------------------------------------------------

def test_run_depends_only_on_protocol_and_produces_report():
    """R6/R22: built from a Protocol-only fake; returns a fully-aggregated report."""
    items, orch = _dataset()

    report = EvalHarness(orch).run(items)

    assert isinstance(report, EvalReport)
    assert report.total == 2
    assert report.in_corpus == 1
    assert report.out_of_corpus == 1
    assert report.excluded_abstained == 1          # the abstained out-of-corpus item
    assert report.hit_rate == pytest.approx(1.0)   # in-corpus item cites https://a
    assert report.faithfulness_proxy == pytest.approx(1.0)  # cited + full overlap
    assert report.faithfulness_llm is None          # no judge by default (R16)
    assert report.abstention_recall == pytest.approx(1.0)   # out-of-corpus abstained
    assert report.abstention_precision == pytest.approx(1.0)


def test_run_no_judge_by_default_leaves_llm_none():
    """R16: with no judge, faithfulness_llm stays None and no LLM is contacted."""
    items, orch = _dataset()
    report = EvalHarness(orch).run(items)
    assert report.faithfulness_llm is None


def test_run_with_fake_judge_populates_llm_score():
    """R15/R17: passing a fake judge populates faithfulness_llm."""
    from wowrag.llm.fake import FakeLLMProvider

    items, orch = _dataset()
    report = EvalHarness(orch).run(items, judge=FakeLLMProvider(prefix="0.7 "))
    # only the single non-abstained item is scored by the judge
    assert report.faithfulness_llm == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# R23 — EvalReport is JSON-serializable
# ---------------------------------------------------------------------------

def test_report_json_serializable():
    """R23: report.model_dump_json() produces stable, parseable JSON."""
    items, orch = _dataset()
    report = EvalHarness(orch).run(items)

    payload = report.model_dump_json()
    data = json.loads(payload)

    assert data["total"] == 2
    assert data["hit_rate"] == 1.0
    assert data["faithfulness_llm"] is None
    # round-trips back into the model
    assert EvalReport.model_validate_json(payload) == report
