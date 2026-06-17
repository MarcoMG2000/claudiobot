"""Application configuration via pydantic-settings.

``Settings`` reads from environment variables and an optional ``.env`` file,
falling back to sensible defaults aligned with ``docs/architecture.md`` §2.
``default_persona`` is the single composition point that resolves the configured
default persona through the persona loader.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from wowrag.personas import Persona, load_persona


class Settings(BaseSettings):
    """Central configuration. All values come from env / ``.env`` / defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_dsn: str = "postgresql://wowrag:wowrag@localhost:5432/wowrag"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 32   # número de textos por batch en BgeM3Embeddings
    embedding_device: str = "cpu"    # "cpu" | "cuda"; sin GPU por defecto
    top_k: int = 5
    score_threshold: float = 0.30
    default_persona: str = "simple"
    chunk_size: int = 512      # máximo de caracteres por chunk
    chunk_overlap: int = 64    # caracteres de solapamiento entre chunks consecutivos
    vector_table: str = "chunks"      # nombre de la tabla de chunks en pgvector
    distance_metric: str = "cosine"   # métrica de similitud del almacén vectorial

    # CORS para el frontend in-game futuro (f9). No hardcodeados en la app: el
    # middleware los lee desde aquí, configurables por entorno. El comodín "*" es
    # solo el default explícito y documentado; se puede cerrar a una lista de
    # orígenes. En env, una lista se expresa como JSON, p. ej.
    # WOWRAG_CORS_ALLOW_ORIGINS='["https://game.example"]'. (R14)
    cors_allow_origins: list[str] = ["*"]
    cors_allow_credentials: bool = False
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]


def default_persona(settings: Settings | None = None) -> Persona:
    """Resolve the default persona from ``Settings.default_persona``.

    Single composition point: reads the configured persona name and loads it via
    the persona loader. Pass an explicit ``settings`` to override.
    """
    settings = settings or Settings()
    return load_persona(settings.default_persona)
