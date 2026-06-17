"""Pydantic models for the f10 evaluation harness.

These models belong to the *evaluation tool* (golden dataset + report), not to
the data pipeline; per ``design.md`` §2 they live in ``wowrag.eval`` rather than
the global ``wowrag.models``. ``GoldenItem`` describes one golden Q&A case
(R1-R3); ``EvalReport`` aggregates the computed metrics (R22, R23).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator


class GoldenItem(BaseModel):
    """A single case of the golden evaluation dataset (R1).

    in_corpus=True  -> the answer is in the corpus; the system MUST NOT abstain
                       and SHOULD cite at least one of ``expected_urls`` (hit-rate).
    in_corpus=False -> out-of-corpus question; the system MUST abstain.
    """

    question: str
    expected_urls: list[str] = []
    in_corpus: bool
    reference_answer: str | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, v: str) -> str:
        # R1: question must be a non-empty string.
        if not v or not v.strip():
            raise ValueError("question must be a non-empty string")
        return v

    @model_validator(mode="after")
    def _coherent_labels(self) -> GoldenItem:
        # R2: an in-corpus item without an expected source is not evaluable for
        # hit-rate.
        if self.in_corpus and not self.expected_urls:
            raise ValueError("in_corpus item must declare at least one expected_url")
        # R3: an out-of-corpus question cannot declare expected sources.
        if not self.in_corpus and self.expected_urls:
            raise ValueError("out-of-corpus item must not declare expected_urls")
        return self


class EvalReport(BaseModel):
    """Aggregated evaluation report; JSON-serializable via pydantic (R22, R23).

    Every field is traceable to its requirement:
    - counts (``total``/``in_corpus``/``out_of_corpus``/``excluded_abstained``)
      summarize the dataset and the faithfulness exclusions (R14, R22).
    - ``hit_rate`` is the retrieval hit-rate or ``None`` (R8-R11).
    - ``faithfulness_proxy`` is the deterministic proxy mean or ``None`` (R12-R14).
    - ``faithfulness_llm`` is the optional LLM-judge mean or ``None`` (R15-R17).
    - ``abstention_precision``/``abstention_recall`` are the abstention metrics or
      ``None`` at the boundaries (R18-R21).
    """

    total: int                          # items evaluated
    in_corpus: int                      # # in-corpus items
    out_of_corpus: int                  # # out-of-corpus items
    excluded_abstained: int             # # excluded from faithfulness (R14)

    hit_rate: float | None              # R8-R11 (None if no in-corpus items)
    faithfulness_proxy: float | None    # R12-R14 (None if all abstained)
    faithfulness_llm: float | None      # R15-R17 (None if no judge used)
    abstention_precision: float | None  # R19, R20
    abstention_recall: float | None     # R19, R20
