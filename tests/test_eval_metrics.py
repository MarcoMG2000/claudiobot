"""Tests for the pure evaluation metric functions (f10-evaluation-harness).

Trazabilidad: R8, R9, R10, R11 (hit-rate); R12, R13, R14 (faithfulness proxy);
R15, R16, R17 (LLM judge); R18, R19, R20, R21 (abstention). All network-free,
stdlib + hand-built Answer fixtures only.
"""

from __future__ import annotations

import pytest

from wowrag.eval.metrics import (
    abstention_scores,
    count_excluded_abstained,
    faithfulness_llm_judge,
    faithfulness_proxy,
    faithfulness_proxy_mean,
    retrieval_hit_rate,
)
from wowrag.eval.models import GoldenItem
from wowrag.llm.fake import FakeLLMProvider
from wowrag.models import Answer, AnswerMetadata, Source


# ---------------------------------------------------------------------------
# Fixture helpers — hand-built GoldenItem / Answer pairs
# ---------------------------------------------------------------------------

def _meta() -> AnswerMetadata:
    return AnswerMetadata(model="fake-llm", persona="default", max_score=0.9, scores=[0.9])


def _answer(
    text: str = "Fireball deals fire damage.",
    urls: list[str] | None = None,
    abstained: bool = False,
) -> Answer:
    urls = urls if urls is not None else ["https://wowhead.com/spell=133"]
    sources = [Source(n=i + 1, title=f"T{i}", url=u) for i, u in enumerate(urls)]
    return Answer(answer=text, sources=sources, abstained=abstained, metadata=_meta())


def _item(
    question: str = "What does Fireball do?",
    urls: list[str] | None = None,
    in_corpus: bool = True,
    reference: str | None = "Fireball deals fire damage.",
) -> GoldenItem:
    if in_corpus:
        urls = urls if urls is not None else ["https://wowhead.com/spell=133"]
    else:
        urls = []
    return GoldenItem(
        question=question,
        expected_urls=urls,
        in_corpus=in_corpus,
        reference_answer=reference if in_corpus else None,
    )


# ===========================================================================
# Metric 1 — Retrieval hit-rate (R8-R11)
# ===========================================================================

def test_hit_rate_counts_url_intersection():
    """R8/R9: fraction of in-corpus items whose source URLs intersect expected."""
    pairs = [
        # hit: expected url present in sources
        (_item(urls=["https://a"]), _answer(urls=["https://a", "https://z"])),
        # miss: no intersection
        (_item(urls=["https://b"]), _answer(urls=["https://x"])),
    ]
    assert retrieval_hit_rate(pairs) == 0.5


def test_hit_rate_only_over_in_corpus_items():
    """R8: out-of-corpus items are excluded from the hit-rate denominator."""
    pairs = [
        (_item(urls=["https://a"]), _answer(urls=["https://a"])),       # in-corpus hit
        (_item(in_corpus=False), _answer(urls=[], abstained=True)),     # excluded
    ]
    assert retrieval_hit_rate(pairs) == 1.0


def test_hit_rate_none_when_no_in_corpus():
    """R10: no in-corpus items -> None (no division by zero)."""
    pairs = [(_item(in_corpus=False), _answer(urls=[], abstained=True))]
    assert retrieval_hit_rate(pairs) is None


def test_hit_rate_only_from_sources():
    """R11: changing answer.sources changes the hit-rate; no re-retrieval."""
    item = _item(urls=["https://a"])
    assert retrieval_hit_rate([(item, _answer(urls=["https://a"]))]) == 1.0
    assert retrieval_hit_rate([(item, _answer(urls=["https://other"]))]) == 0.0


# ===========================================================================
# Metric 2 — Faithfulness proxy (R12-R14)
# ===========================================================================

def test_faithfulness_proxy_cited_and_high_overlap():
    """R12/R13: cited answer matching the reference scores near 1.0, in [0,1]."""
    item = _item(reference="Fireball deals fire damage")
    ans = _answer(text="Fireball deals fire damage", urls=["https://a"])
    score = faithfulness_proxy(item, ans)
    assert score == pytest.approx(1.0)
    assert 0.0 <= score <= 1.0


def test_faithfulness_proxy_uncited_is_low():
    """R13a: an answer with no sources loses the 0.5 citation component."""
    item = _item(reference="Fireball deals fire damage")
    cited = faithfulness_proxy(item, _answer(text="Fireball deals fire damage", urls=["https://a"]))
    uncited = faithfulness_proxy(item, _answer(text="Fireball deals fire damage", urls=[]))
    assert uncited < cited
    assert uncited == pytest.approx(0.5)  # overlap 1.0 * 0.5, citation 0


def test_faithfulness_proxy_low_overlap_is_low():
    """R13b: cited answer with no lexical overlap scores only the citation half."""
    item = _item(reference="Frostbolt slows the target with frost")
    ans = _answer(text="Fireball deals fire damage", urls=["https://a"])
    score = faithfulness_proxy(item, ans)
    assert score == pytest.approx(0.5)  # cited 0.5 + overlap 0.0


def test_faithfulness_proxy_no_reference_degrades_to_citation():
    """R13b: without reference_answer the proxy degrades to the citation signal."""
    item = _item(in_corpus=False)  # reference_answer is None
    assert faithfulness_proxy(item, _answer(urls=["https://a"])) == pytest.approx(1.0)
    assert faithfulness_proxy(item, _answer(urls=[])) == pytest.approx(0.0)


def test_faithfulness_proxy_in_range():
    """R13: the proxy is always within [0, 1]."""
    item = _item(reference="alpha beta gamma delta")
    for text, urls in [
        ("alpha beta", ["https://a"]),
        ("zzz", []),
        ("alpha beta gamma delta", ["https://a"]),
    ]:
        score = faithfulness_proxy(item, _answer(text=text, urls=urls))
        assert 0.0 <= score <= 1.0


def test_faithfulness_proxy_is_deterministic():
    """R12: same input -> same score, no network."""
    item = _item(reference="Fireball deals fire damage")
    ans = _answer(text="Fireball deals fire damage", urls=["https://a"])
    assert faithfulness_proxy(item, ans) == faithfulness_proxy(item, ans)


def test_faithfulness_excludes_abstained():
    """R14: abstained answers are excluded from the mean and counted separately."""
    pairs = [
        (_item(reference="Fireball deals fire damage"),
         _answer(text="Fireball deals fire damage", urls=["https://a"])),
        (_item(in_corpus=False), _answer(text="I cannot answer", urls=[], abstained=True)),
    ]
    # Only the non-abstained pair contributes (score 1.0).
    assert faithfulness_proxy_mean(pairs) == pytest.approx(1.0)
    assert count_excluded_abstained(pairs) == 1


def test_faithfulness_proxy_mean_none_when_all_abstained():
    """R14: when every pair abstained the mean is None."""
    pairs = [(_item(in_corpus=False), _answer(urls=[], abstained=True))]
    assert faithfulness_proxy_mean(pairs) is None


# ===========================================================================
# Metric 3 — Abstention precision / recall (R18-R21)
# ===========================================================================

def test_abstention_precision_recall():
    """R18/R19: TP/FP/FN of abstention produce correct precision and recall."""
    pairs = [
        # out-of-corpus correctly abstained (TP)
        (_item(in_corpus=False), _answer(urls=[], abstained=True)),
        # out-of-corpus NOT abstained (FN -> lowers recall)
        (_item(in_corpus=False), _answer(urls=["https://x"], abstained=False)),
        # in-corpus abstained (FP -> lowers precision)
        (_item(urls=["https://a"]), _answer(urls=[], abstained=True)),
        # in-corpus correctly answered (true negative for abstention)
        (_item(urls=["https://a"]), _answer(urls=["https://a"], abstained=False)),
    ]
    scores = abstention_scores(pairs)
    # correct_abst = 1 (the single TP); out_of_corpus = 2; abstained = 2
    assert scores["abstention_recall"] == pytest.approx(0.5)     # 1/2
    assert scores["abstention_precision"] == pytest.approx(0.5)  # 1/2
    assert scores["in_corpus"] == 2
    assert scores["out_of_corpus"] == 2


def test_abstention_recall_none_when_no_out_of_corpus():
    """R20: no out-of-corpus items -> recall is None."""
    pairs = [(_item(urls=["https://a"]), _answer(urls=["https://a"], abstained=False))]
    scores = abstention_scores(pairs)
    assert scores["abstention_recall"] is None


def test_abstention_precision_none_when_no_abstentions():
    """R20: nothing abstained -> precision is None."""
    pairs = [
        (_item(urls=["https://a"]), _answer(urls=["https://a"], abstained=False)),
        (_item(in_corpus=False), _answer(urls=["https://x"], abstained=False)),
    ]
    scores = abstention_scores(pairs)
    assert scores["abstention_precision"] is None
    assert scores["abstention_recall"] == pytest.approx(0.0)  # out-of-corpus exists, no TP


def test_abstention_only_from_flag():
    """R21: the metric is derived solely from answer.abstained."""
    item = _item(in_corpus=False)
    # Same item; only the abstained flag differs -> recall flips.
    abstained = abstention_scores([(item, _answer(urls=[], abstained=True))])
    not_abstained = abstention_scores([(item, _answer(urls=[], abstained=False))])
    assert abstained["abstention_recall"] == pytest.approx(1.0)
    assert not_abstained["abstention_recall"] == pytest.approx(0.0)


# ===========================================================================
# Optional LLM judge (R15-R17)
# ===========================================================================

def test_faithfulness_llm_judge_with_fake():
    """R15/R17: an injected FakeLLMProvider returning a score yields the mean."""
    # FakeLLMProvider echoes "<prefix><prompt>"; a prefix of "0.8 " makes the
    # parser pick up 0.8 as the score deterministically, no network.
    judge = FakeLLMProvider(prefix="0.8 ")
    pairs = [
        (_item(reference="Fireball deals fire damage"),
         _answer(text="Fireball deals fire damage", urls=["https://a"])),
        (_item(reference="Frostbolt slows the target"),
         _answer(text="Frostbolt slows the target", urls=["https://b"])),
    ]
    assert faithfulness_llm_judge(pairs, judge) == pytest.approx(0.8)


def test_faithfulness_llm_judge_skips_abstained():
    """R17: abstained pairs are not scored by the judge; None if all abstained."""
    judge = FakeLLMProvider(prefix="0.8 ")
    pairs = [(_item(in_corpus=False), _answer(urls=[], abstained=True))]
    assert faithfulness_llm_judge(pairs, judge) is None


def test_metrics_import_does_not_pull_heavy_backends():
    """R16: importing wowrag.eval.metrics never pulls torch/psycopg/httpx.

    Runs in a fresh subprocess so the assertion is independent of what the test
    session already imported. The metrics module uses an injected LLMProvider and
    only TYPE_CHECKING imports of the LLM layer, so the default path never
    contacts Ollama nor pulls the heavy deps.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")

    code = (
        "import sys; import wowrag.eval.metrics; "
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


def test_judge_uses_injected_provider_only(monkeypatch):
    """R15/R16: the judge calls the injected provider; no LLM is instantiated."""
    calls: list[str] = []

    class _StubLLM:
        @property
        def model(self) -> str:
            return "stub"

        def generate(self, prompt: str) -> str:
            calls.append(prompt)
            return "0.5"

        def generate_stream(self, prompt: str):  # pragma: no cover - unused
            yield "0.5"

    item = _item(reference="Fireball deals fire damage")
    ans = _answer(text="Fireball deals fire damage", urls=["https://a"])
    score = faithfulness_llm_judge([(item, ans)], _StubLLM())

    assert score == pytest.approx(0.5)
    assert len(calls) == 1  # one judge call for the single non-abstained pair
