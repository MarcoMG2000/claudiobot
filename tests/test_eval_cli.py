"""Tests for the f10 evaluation CLI entrypoint (Slice B).

Trazabilidad: R24 (stdout summary + runnable entrypoint), R25 (JSON --out
artifact), R26 (lazy real composition — never built when injected; import-free of
heavy deps), R30 (final package exports). All run with a FakeOrchestrator injected
into ``main`` — no Postgres, GPU, Ollama, or network (R29).
"""

from __future__ import annotations

import json

import pytest

from wowrag.eval import EvalReport, GoldenItem
from wowrag.eval.cli import main
from wowrag.models import Answer, AnswerMetadata, Source
from wowrag.personas import Persona


# ---------------------------------------------------------------------------
# FakeOrchestrator — implements the RagOrchestrator Protocol (R26, R29)
# ---------------------------------------------------------------------------

class FakeOrchestrator:
    """Maps question -> predefined Answer; counts calls. No network (R26, R29).

    Implements the RagOrchestrator Protocol structurally (a single ``answer``
    method), so the CLI runs end-to-end without touching the real stack. Falls
    back to a generic abstention for any question not pre-seeded so it works
    against the committed fixture too.
    """

    def __init__(self, answers: dict[str, Answer] | None = None) -> None:
        self._answers = answers or {}
        self.calls: list[str] = []

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        self.calls.append(query)
        if query in self._answers:
            return self._answers[query]
        # Default: abstain (fixture out-of-corpus items; unseeded questions).
        return _answer("I cannot answer that.", [], abstained=True)


def _meta() -> AnswerMetadata:
    return AnswerMetadata(model="fake-llm", persona="default", max_score=0.9, scores=[0.9])


def _answer(text: str, urls: list[str], abstained: bool = False) -> Answer:
    sources = [Source(n=i + 1, title=f"T{i}", url=u) for i, u in enumerate(urls)]
    return Answer(answer=text, sources=sources, abstained=abstained, metadata=_meta())


def _write_dataset(tmp_path) -> str:
    """Write a small valid golden JSONL to ``tmp_path`` and return its path."""
    path = tmp_path / "golden.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "question": "What does Fireball do?",
                        "expected_urls": ["https://a"],
                        "in_corpus": True,
                        "reference_answer": "Fireball deals fire damage",
                    }
                ),
                json.dumps(
                    {
                        "question": "Off-topic question?",
                        "expected_urls": [],
                        "in_corpus": False,
                        "reference_answer": None,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    return str(path)


def _seeded_fake() -> FakeOrchestrator:
    return FakeOrchestrator(
        {
            "What does Fireball do?": _answer(
                "Fireball deals fire damage", ["https://a"], abstained=False
            ),
            "Off-topic question?": _answer("I cannot answer", [], abstained=True),
        }
    )


# ---------------------------------------------------------------------------
# R24 — runnable entrypoint: prints a summary and returns 0
# ---------------------------------------------------------------------------

def test_main_prints_summary(tmp_path, capsys):
    """R24: main([...], orchestrator=fake) prints a readable summary, returns 0."""
    dataset = _write_dataset(tmp_path)

    rc = main(["--dataset", dataset], orchestrator=_seeded_fake())

    assert rc == 0
    out = capsys.readouterr().out
    assert "eval report" in out
    assert "retrieval hit-rate" in out
    assert "abstention recall" in out


def test_main_runs_against_committed_fixture(capsys):
    """R24: with no --dataset, main loads the committed fixture and runs (returns 0).

    Uses an injected FakeOrchestrator so the default suite never builds the real
    stack nor touches the network (R29).
    """
    rc = main([], orchestrator=FakeOrchestrator())

    assert rc == 0
    out = capsys.readouterr().out
    assert "items evaluated" in out


# ---------------------------------------------------------------------------
# R25 — JSON artifact via --out
# ---------------------------------------------------------------------------

def test_main_writes_json_artifact(tmp_path, capsys):
    """R25: main(["--out", p], orchestrator=fake) writes the EvalReport as JSON."""
    dataset = _write_dataset(tmp_path)
    out_path = tmp_path / "report.json"

    rc = main(["--dataset", dataset, "--out", str(out_path)], orchestrator=_seeded_fake())

    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    # Artifact carries the full aggregated report (R22 fields) and round-trips.
    assert data["total"] == 2
    assert data["hit_rate"] == 1.0
    assert data["abstention_recall"] == 1.0
    report = EvalReport.model_validate_json(out_path.read_text(encoding="utf-8"))
    assert report.total == 2
    # Summary is still printed alongside the artifact (R24 + R25).
    assert "eval report" in capsys.readouterr().out


def test_main_no_out_writes_no_file(tmp_path, capsys):
    """R25: without --out, no artifact is written (summary only)."""
    dataset = _write_dataset(tmp_path)

    main(["--dataset", dataset], orchestrator=_seeded_fake())

    capsys.readouterr()
    assert list(tmp_path.glob("*.json")) == []


# ---------------------------------------------------------------------------
# R26 / R29 — injected orchestrator: the real composition is never built
# ---------------------------------------------------------------------------

def test_main_does_not_build_real_orchestrator_when_injected(tmp_path, monkeypatch, capsys):
    """R26/R29: with an orchestrator injected, _build_orchestrator is never called."""
    import wowrag.eval.cli as cli

    def _boom() -> object:  # pragma: no cover - must never run
        raise AssertionError("real orchestrator must not be built when one is injected")

    monkeypatch.setattr(cli, "_build_orchestrator", _boom)
    dataset = _write_dataset(tmp_path)

    rc = main(["--dataset", dataset], orchestrator=_seeded_fake())

    assert rc == 0
    capsys.readouterr()


def test_import_eval_is_network_free():
    """R16/R26: importing wowrag.eval and wowrag.eval.cli pulls no heavy backends.

    Runs in a fresh subprocess so the assertion is independent of what the test
    session already imported. The CLI composes the real orchestrator lazily inside
    _build_orchestrator, so the module imports never pull torch/psycopg/httpx.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")

    code = (
        "import sys; import wowrag.eval; import wowrag.eval.cli; "
        "heavy = [m for m in ('torch', 'psycopg', 'httpx') if m in sys.modules]; "
        "assert not heavy, heavy; print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_build_orchestrator_reuses_f9_lazily(monkeypatch):
    """R26: _build_orchestrator delegates to f9's build_orchestrator (lazy reuse).

    Patches f9's composition point to a sentinel so we verify reuse without
    building the real bge-m3/pgvector/Ollama stack.
    """
    import wowrag.api.dependencies as deps
    import wowrag.eval.cli as cli

    sentinel = object()
    monkeypatch.setattr(deps, "build_orchestrator", lambda: sentinel)

    assert cli._build_orchestrator() is sentinel


# ---------------------------------------------------------------------------
# R28 — configured default dataset path (optional Settings field)
# ---------------------------------------------------------------------------

def test_default_dataset_path_uses_settings(tmp_path, monkeypatch, capsys):
    """R28: when --dataset is omitted, the configured eval_dataset_path is used."""
    dataset = _write_dataset(tmp_path)
    monkeypatch.setenv("EVAL_DATASET_PATH", dataset)

    rc = main([], orchestrator=_seeded_fake())

    assert rc == 0
    out = capsys.readouterr().out
    # The configured 2-item dataset (not the 4-item fixture) was loaded.
    assert "items evaluated   : 2" in out


# ---------------------------------------------------------------------------
# R30 — final package exports (incl. CLI main)
# ---------------------------------------------------------------------------

def test_exports():
    """R30: the public symbols (incl. main) import from the wowrag.eval package."""
    from wowrag.eval import (  # noqa: F401
        EvalHarness,
        EvalReport,
        GoldenDatasetError,
        GoldenItem,
        abstention_scores,
        faithfulness_llm_judge,
        faithfulness_proxy,
        faithfulness_proxy_mean,
        load_golden,
        main,
        retrieval_hit_rate,
    )

    import wowrag.eval as evalpkg

    for symbol in (
        "GoldenItem",
        "EvalReport",
        "load_golden",
        "GoldenDatasetError",
        "EvalHarness",
        "main",
        "retrieval_hit_rate",
        "faithfulness_proxy",
        "faithfulness_proxy_mean",
        "abstention_scores",
        "faithfulness_llm_judge",
    ):
        assert symbol in evalpkg.__all__
        assert hasattr(evalpkg, symbol)


def test_golden_item_export_is_usable():
    """R30: the re-exported GoldenItem is the real model (constructible)."""
    item = GoldenItem(question="q", expected_urls=["https://a"], in_corpus=True)
    assert item.question == "q"
