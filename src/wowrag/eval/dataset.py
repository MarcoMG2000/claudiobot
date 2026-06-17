"""Golden dataset loader for the f10 evaluation harness (R4, R5).

The dataset is a JSONL file (one ``GoldenItem`` per line). ``load_golden``
validates every non-blank line against the schema and raises a clear error that
names the offending line; it never silences or skips an invalid line.
"""

from __future__ import annotations

import json
from pathlib import Path

from wowrag.eval.models import GoldenItem

# The committed default fixture, resolved relative to this package so the default
# path works regardless of the caller's cwd (same pattern as personas/*.yaml).
_DEFAULT_DATASET = Path(__file__).parent / "data" / "golden.jsonl"


class GoldenDatasetError(Exception):
    """Raised when the golden dataset file is malformed.

    The message identifies the 1-based line number of the offending entry so the
    error points at the exact problem (R4).
    """


def load_golden(path: str | Path | None = None) -> list[GoldenItem]:
    """Load and validate a golden JSONL dataset (R4).

    Parameters
    ----------
    path:
        Path to a JSONL file (one ``GoldenItem`` per line). ``None`` resolves to
        the committed default fixture ``eval/data/golden.jsonl`` (R5).

    Returns
    -------
    list[GoldenItem]
        One validated item per non-blank line, in file order.

    Raises
    ------
    GoldenDatasetError
        If a line is not valid JSON or fails ``GoldenItem`` validation (including
        the R2/R3 coherence rules). The error names the 1-based line number; the
        line is neither silenced nor skipped (R4).
    """
    src = Path(path) if path is not None else _DEFAULT_DATASET
    items: list[GoldenItem] = []
    for lineno, raw in enumerate(src.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # blank lines are tolerated, not parsed
        try:
            data = json.loads(line)
            items.append(GoldenItem(**data))
        except Exception as exc:  # JSON decode error or pydantic ValidationError
            raise GoldenDatasetError(
                f"invalid golden item at line {lineno}: {exc}"
            ) from exc
    return items
