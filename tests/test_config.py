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
    "vector_table": "chunks",       # R30
    "distance_metric": "cosine",    # R31
    "eval_dataset_path": None,      # R28 (f10-evaluation-harness)
    "cors_allow_origins": ["*"],            # R14 (f9-http-api)
    "cors_allow_credentials": False,        # R14 (f9-http-api)
    "cors_allow_methods": ["*"],            # R14 (f9-http-api)
    "cors_allow_headers": ["*"],            # R14 (f9-http-api)
    # f11-wowhead-ingestion (Slice A) scraper settings: new optional fields with
    # courteous defaults; do not alter any existing key.
    "scrape_user_agent": (                  # R10 (f11)
        "wow-classic-rag-bot/0.1 "
        "(+https://github.com/wow-classic-rag/wow-classic-rag)"
    ),
    "scrape_min_interval_s": 1.0,           # R8  (f11)
    "scrape_allowed_host": "www.wowhead.com",  # R17, R18 (f11)
    "scrape_max_pages": 100,                # R8 defense (f11)
    "scrape_corpus_path": "data/corpus",    # R21 (f11)
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


def test_vector_table_and_metric_overridable_from_env(monkeypatch):  # R30, R31
    # R30/R31: vector_table and distance_metric must be configurable from the
    # environment, not just hardcoded defaults.
    monkeypatch.setenv("VECTOR_TABLE", "wow_chunks")
    monkeypatch.setenv("DISTANCE_METRIC", "l2")
    settings = Settings(_env_file=None)
    assert settings.vector_table == "wow_chunks"
    assert settings.distance_metric == "l2"


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


def test_score_threshold_overridable_from_env(monkeypatch):  # R19 (f5-retriever)
    # R19: score_threshold must be configurable from the SCORE_THRESHOLD env var.
    # The default-assert already exists in EXPECTED_DEFAULTS (0.30).
    # This test closes the env-override gap identified in design.md §6.
    monkeypatch.setenv("SCORE_THRESHOLD", "0.5")
    settings = Settings(_env_file=None)
    assert settings.score_threshold == 0.5


def test_ollama_url_and_llm_model_overridable_from_env(monkeypatch):  # R13 (f7-llm-provider-ollama)
    # R13: ollama_url and llm_model must be configurable from the environment,
    # not just hardcoded defaults. The default-asserts already exist in
    # EXPECTED_DEFAULTS above; this test closes the env-override gap per the
    # f3 R10 / f5 lesson (each Settings field consumed by a feature needs both
    # a default-assert and an env-override test).
    monkeypatch.setenv("OLLAMA_URL", "http://custom-ollama:11434")
    monkeypatch.setenv("LLM_MODEL", "llama3:8b")
    settings = Settings(_env_file=None)
    assert settings.ollama_url == "http://custom-ollama:11434"
    assert settings.llm_model == "llama3:8b"


def test_eval_dataset_path_default_is_none_and_overridable(monkeypatch):  # R28 (f10-evaluation-harness)
    # R28: f10 adds the optional eval_dataset_path field with a sane default
    # (None -> committed fixture) WITHOUT requiring env for the default path,
    # and WITHOUT altering any existing key. The default-assert lives in
    # EXPECTED_DEFAULTS above; this test closes the env-override gap.
    assert Settings(_env_file=None).eval_dataset_path is None
    monkeypatch.setenv("EVAL_DATASET_PATH", "/data/custom_golden.jsonl")
    settings = Settings(_env_file=None)
    assert settings.eval_dataset_path == "/data/custom_golden.jsonl"


def test_cors_allow_origins_override_constructor():  # R14 (f9-http-api)
    # R14: CORS origins are read from Settings, not hardcoded. A constructor
    # override (as create_app/tests use) must take effect, not "*".
    settings = Settings(
        _env_file=None, cors_allow_origins=["https://game.example"]
    )
    assert settings.cors_allow_origins == ["https://game.example"]


def test_cors_allow_origins_override_from_env(monkeypatch):  # R14 (f9-http-api)
    # R14: CORS origins are configurable from the environment (JSON list), so
    # the wildcard default can be closed to a fixed allow-list per deployment.
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", '["https://game.example"]')
    settings = Settings(_env_file=None)
    assert settings.cors_allow_origins == ["https://game.example"]


def test_scrape_settings_overridable_from_env(monkeypatch):  # R8, R10, R17, R21 (f11)
    # R8/R10/R17/R21: the wowhead scraper settings must be configurable from the
    # environment, not just hardcoded defaults (the operator hardens the rate
    # limit / UA / allowlist per deployment). The default-asserts live in
    # EXPECTED_DEFAULTS above; this test closes the env-override gap, matching
    # the project lesson that every Settings field consumed by a feature needs
    # both a default-assert and an env-override test.
    monkeypatch.setenv("SCRAPE_USER_AGENT", "custom-bot/9.9 (+mailto:me@example.com)")
    monkeypatch.setenv("SCRAPE_MIN_INTERVAL_S", "2.5")
    monkeypatch.setenv("SCRAPE_ALLOWED_HOST", "classic.wowhead.com")
    monkeypatch.setenv("SCRAPE_MAX_PAGES", "7")
    monkeypatch.setenv("SCRAPE_CORPUS_PATH", "/data/wowhead")
    settings = Settings(_env_file=None)
    assert settings.scrape_user_agent == "custom-bot/9.9 (+mailto:me@example.com)"
    assert settings.scrape_min_interval_s == 2.5
    assert settings.scrape_allowed_host == "classic.wowhead.com"
    assert settings.scrape_max_pages == 7
    assert settings.scrape_corpus_path == "/data/wowhead"
