"""Tests for repo hygiene: .gitignore and .env.example. Covers R14."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Fields of Settings (R5) that .env.example must document.
R5_FIELDS = [
    "POSTGRES_DSN",
    "OLLAMA_URL",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "TOP_K",
    "SCORE_THRESHOLD",
    "DEFAULT_PERSONA",
]


def test_gitignore_ignores_secrets_and_caches():  # R14
    text = GITIGNORE.read_text(encoding="utf-8")
    for pattern in [".env", ".venv", "__pycache__"]:
        assert pattern in text, f"{pattern!r} missing from .gitignore"


def test_env_example_exists_and_documents_r5_fields():  # R14
    assert ENV_EXAMPLE.exists(), ".env.example must exist"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for field in R5_FIELDS:
        assert field in text, f"{field} not documented in .env.example"
