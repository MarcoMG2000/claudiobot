"""Tests for the Settings configuration system. Covers R3, R4, R5, R6."""

import pytest

from wowrag.config import Settings

EXPECTED_DEFAULTS = {
    "postgres_dsn": "postgresql://wowrag:wowrag@localhost:5432/wowrag",
    "ollama_url": "http://localhost:11434",
    "llm_model": "qwen2.5:7b-instruct",
    "embedding_model": "BAAI/bge-m3",
    "embedding_dim": 1024,
    "embedding_batch_size": 32,
    "embedding_device": "cpu",
    "top_k": 5,
    "score_threshold": 0.30,
    "default_persona": "simple",
}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    # Ensure no ambient env var leaks into the default-value tests.
    for key in EXPECTED_DEFAULTS:
        monkeypatch.delenv(key.upper(), raising=False)


def test_settings_defaults_without_env(monkeypatch):  # R3, R5
    # Disable .env loading so only the in-code defaults apply.
    settings = Settings(_env_file=None)
    for field, expected in EXPECTED_DEFAULTS.items():
        assert getattr(settings, field) == expected


def test_settings_exposes_all_required_fields():  # R5
    settings = Settings(_env_file=None)
    for field in EXPECTED_DEFAULTS:
        assert hasattr(settings, field), field


def test_env_var_overrides_default(monkeypatch):  # R4
    monkeypatch.setenv("TOP_K", "42")
    monkeypatch.setenv("DEFAULT_PERSONA", "orc")
    settings = Settings(_env_file=None)
    assert settings.top_k == 42
    assert settings.default_persona == "orc"


def test_embedding_batch_size_and_device_overridable_from_env(monkeypatch):  # R10
    # R10: embedding_batch_size and embedding_device must be configurable
    # from the environment, not just hardcoded defaults.
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "8")
    monkeypatch.setenv("EMBEDDING_DEVICE", "cuda")
    settings = Settings(_env_file=None)
    assert settings.embedding_batch_size == 8
    assert settings.embedding_device == "cuda"


def test_reads_values_from_env_file(tmp_path):  # R6
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_MODEL=custom-model\nTOP_K=9\n", encoding="utf-8"
    )
    settings = Settings(_env_file=str(env_file))
    assert settings.llm_model == "custom-model"
    assert settings.top_k == 9
    # Fields not in the .env keep their defaults.
    assert settings.embedding_dim == 1024


def test_env_var_takes_priority_over_env_file(tmp_path, monkeypatch):  # R4, R6
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_MODEL=from-file\n", encoding="utf-8")
    monkeypatch.setenv("LLM_MODEL", "from-env")
    settings = Settings(_env_file=str(env_file))
    assert settings.llm_model == "from-env"
