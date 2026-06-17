"""Pure metric functions for the f10 evaluation harness (R8-R21).

Every metric is a pure function over the ``(GoldenItem, Answer)`` pairs already
produced by the runner: none of them call the orchestrator, retrieve, or embed
(R11, R21). The default faithfulness path is a deterministic, stdlib-only proxy
(R12-R14); the optional LLM judge (R15-R17) takes an injected ``LLMProvider`` and
is never instantiated here, so importing this module never contacts Ollama (R16).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid importing the LLM layer at module load (R16)
    from wowrag.llm.base import LLMProvider

from wowrag.eval.models import GoldenItem
from wowrag.models import Answer

# Small bilingual stopword set used by the lexical-overlap proxy (R13). Kept as a
# module constant so the normalization is documented and stable across runs.
STOPWORDS: frozenset[str] = frozenset(
    {
        # English
        "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or",
        "is", "are", "was", "were", "be", "it", "its", "this", "that", "with",
        "as", "by", "from", "does", "do", "what", "how", "much",
        # Spanish
        "el", "la", "los", "las", "de", "del", "y", "o", "un", "una", "en",
        "es", "son", "que", "con", "por", "para", "se", "su",
    }
)

# A type alias used throughout: a golden item paired with the Answer f8 produced.
Pair = tuple[GoldenItem, Answer]

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    """Tokenize ``text`` to a set of content tokens (R13).

    Normalization: lowercase, split on ``[a-z0-9]+`` words, drop stopwords.
    """
    return {w for w in _TOKEN_RE.findall(text.lower()) if w not in STOPWORDS}


# ---------------------------------------------------------------------------
# Metric 1 — Retrieval hit-rate (R8-R11)
# ---------------------------------------------------------------------------

def _has_hit(item: GoldenItem, answer: Answer) -> bool:
    """True when expected URLs intersect the answer's source URLs (R9).

    Exact URL string comparison; derived only from ``answer.sources`` (R11).
    """
    return bool(set(item.expected_urls) & {s.url for s in answer.sources})


def retrieval_hit_rate(pairs: list[Pair]) -> float | None:
    """Fraction of in-corpus items whose answer cites an expected URL (R8).

    Computed only over ``in_corpus`` items (R8); an item "hits" when its
    ``expected_urls`` intersect the answer's source URLs (R9). Returns ``None``
    when there are no in-corpus items, to avoid dividing by zero (R10). Derived
    exclusively from ``answer.sources`` — never re-runs retrieval (R11).
    """
    in_corpus = [(item, ans) for item, ans in pairs if item.in_corpus]
    if not in_corpus:
        return None  # R10
    hits = sum(1 for item, ans in in_corpus if _has_hit(item, ans))
    return hits / len(in_corpus)  # R8


# ---------------------------------------------------------------------------
# Metric 2 — Faithfulness proxy (R12-R14)
# ---------------------------------------------------------------------------

def faithfulness_proxy(item: GoldenItem, answer: Answer) -> float:
    """Deterministic faithfulness proxy for one non-abstained pair (R12, R13).

    ``faithfulness = 0.5 * cited + 0.5 * overlap`` where:
      - ``cited`` is 1.0 if the answer carries at least one ``Source`` else 0.0
        (grounding signal, R13a);
      - ``overlap`` is the fraction of ``reference_answer`` tokens covered by the
        generated answer's tokens (R13b); when there is no ``reference_answer``
        the proxy degrades to the citation signal (1.0 if cited else 0.0).

    The result is in ``[0, 1]``. This is a pure function — same input, same
    output, no network (R12). Callers must exclude abstained answers (R14).
    """
    cited = 1.0 if len(answer.sources) >= 1 else 0.0  # R13a
    ref = item.reference_answer
    if ref:
        ref_tokens = _tokens(ref)
        if ref_tokens:
            overlap = len(_tokens(answer.answer) & ref_tokens) / len(ref_tokens)
        else:
            # Reference is all stopwords/empty after normalization: fall back to
            # the citation signal so the proxy stays in [0, 1] and monotone.
            overlap = cited
    else:
        overlap = cited  # R13b: no reference -> degrade to the citation signal
    return 0.5 * cited + 0.5 * overlap  # R13


def faithfulness_proxy_mean(pairs: list[Pair]) -> float | None:
    """Mean faithfulness proxy over non-abstained pairs (R12-R14).

    Abstained answers are excluded from the mean (R14); returns ``None`` when
    every pair abstained (nothing to score).
    """
    scored = [
        faithfulness_proxy(item, ans)
        for item, ans in pairs
        if not ans.abstained  # R14
    ]
    if not scored:
        return None
    return sum(scored) / len(scored)


def count_excluded_abstained(pairs: list[Pair]) -> int:
    """Number of pairs excluded from the faithfulness mean by abstention (R14)."""
    return sum(1 for _, ans in pairs if ans.abstained)


# ---------------------------------------------------------------------------
# Metric 3 — Abstention precision / recall (R18-R21)
# ---------------------------------------------------------------------------

def abstention_scores(pairs: list[Pair]) -> dict[str, float | int | None]:
    """Abstention precision/recall plus corpus counts (R18-R21).

    An out-of-corpus item is correct when ``answer.abstained`` is True; an
    in-corpus item is correct when it is False (R18). Derived exclusively from
    ``answer.abstained`` (R21):

      - ``abstention_recall``    = correctly-abstained out-of-corpus / out-of-corpus
      - ``abstention_precision`` = correctly-abstained out-of-corpus / all abstained

    ``recall`` is ``None`` when there are no out-of-corpus items; ``precision`` is
    ``None`` when nothing abstained (R20). Also returns the ``in_corpus`` and
    ``out_of_corpus`` counts so the report can populate them (R22).
    """
    out_of_corpus = [(item, ans) for item, ans in pairs if not item.in_corpus]
    abstained = [(item, ans) for item, ans in pairs if ans.abstained]
    correct_abst = [(item, ans) for item, ans in out_of_corpus if ans.abstained]  # R18

    recall: float | None
    precision: float | None
    recall = len(correct_abst) / len(out_of_corpus) if out_of_corpus else None  # R19/R20
    precision = len(correct_abst) / len(abstained) if abstained else None       # R19/R20

    return {
        "abstention_precision": precision,
        "abstention_recall": recall,
        "in_corpus": sum(1 for item, _ in pairs if item.in_corpus),
        "out_of_corpus": len(out_of_corpus),
    }


# ---------------------------------------------------------------------------
# Optional LLM-judge hook (R15-R17) — decoupled from the default path
# ---------------------------------------------------------------------------

_SCORE_RE = re.compile(r"[01](?:\.\d+)?|\.\d+")


def _parse_score(text: str) -> float:
    """Parse the first ``[0, 1]`` float from an LLM judge's reply.

    Clamps to ``[0, 1]``; raises ``ValueError`` if no number is present so a
    malformed judge reply is surfaced rather than silently scored as zero.
    """
    match = _SCORE_RE.search(text)
    if match is None:
        raise ValueError(f"no [0,1] score found in judge output: {text!r}")
    return max(0.0, min(1.0, float(match.group())))


def _judge_prompt(item: GoldenItem, answer: Answer) -> str:
    """Build the judge prompt asking for a single ``[0, 1]`` faithfulness score."""
    reference = item.reference_answer or "(no reference answer provided)"
    return (
        "You are a strict faithfulness judge. Rate how well the ANSWER is "
        "grounded in / consistent with the REFERENCE, on a scale from 0 to 1. "
        "Reply with only the number.\n"
        f"QUESTION: {item.question}\n"
        f"REFERENCE: {reference}\n"
        f"ANSWER: {answer.answer}\n"
        "SCORE:"
    )


def faithfulness_llm_judge(
    pairs: list[Pair],
    llm: LLMProvider,
) -> float | None:
    """Mean faithfulness scored by an injected ``LLMProvider`` (R15-R17).

    Optional and fully decoupled from the default path: the harness only calls
    this when a judge is supplied (R16). For each non-abstained pair it builds a
    judge prompt, asks the injected ``llm`` for a ``[0, 1]`` score, parses it, and
    returns the mean (``None`` if every pair abstained). The provider is injected,
    not instantiated here, so this never imports ``OllamaLLM`` (R15, R16); it is
    testable with a ``FakeLLMProvider`` (R17).
    """
    scored = [
        _parse_score(llm.generate(_judge_prompt(item, ans)))
        for item, ans in pairs
        if not ans.abstained
    ]
    if not scored:
        return None
    return sum(scored) / len(scored)
