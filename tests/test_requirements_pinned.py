"""Tests for requirements.txt pinning. Covers R13."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements.txt"

# fastapi/uvicorn/httpx promoted from DEFERRED to PINNED in f9-http-api: the
# default test suite exercises the FastAPI app via TestClient (needs httpx), so
# init.sh must install them. torch/sentence-transformers/psycopg stay deferred
# (f3/f4 use lazy imports; not installed by init.sh).  (R24)
PINNED = ["pydantic-settings", "pyyaml", "pytest", "fastapi", "uvicorn", "httpx"]
DEFERRED = ["torch", "sentence-transformers", "psycopg"]


def _dependency_lines() -> list[str]:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def test_required_dependencies_are_pinned():  # R13
    lines = _dependency_lines()
    for dep in PINNED:
        matches = [
            line for line in lines if line.lower().startswith(dep.lower())
        ]
        assert matches, f"{dep} missing from requirements.txt"
        assert any("==" in line for line in matches), (
            f"{dep} not pinned with == in requirements.txt"
        )


def test_deferred_dependencies_absent():  # R13
    text = REQUIREMENTS.read_text(encoding="utf-8").lower()
    for dep in DEFERRED:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            assert not stripped.startswith(dep), (
                f"deferred dependency {dep!r} must not appear in requirements.txt"
            )
