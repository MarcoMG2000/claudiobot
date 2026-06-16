# Sesión actual

- **Feature en curso:** ninguna — `f3-embeddings-provider` cerrada como `done`
- **Última actualización:** 2026-06-15
- **Agente:** leader

F3 cerrada esta sesión (spec aprobado por humano → implementer → reviewer CHANGES_REQUESTED → fix → reviewer APROBADO). Suite total: 86 tests verdes + 1 skipped (integración bge_m3), `./init.sh` exit 0.

## Bitácora

- Humano aprobó spec de F3 (puerta de aprobación superada). Decisión registrada: mantener FastAPI (no Django) para f9.
- Implementer F3: `EmbeddingProvider` Protocol + `EmbeddingError` (`src/wowrag/embeddings/base.py`), `FakeEmbeddingProvider` stdlib-only (`fake.py`), `BgeM3Embeddings` con import lazy de FlagEmbedding (`bge_m3.py`), re-exports (`__init__.py`), campos `embedding_batch_size`/`embedding_device` en `Settings` (`config.py`), `requirements-ml.txt` (deps ML aisladas de init.sh). Informe en `progress/impl_f3-embeddings-provider.md`.
- Reviewer F3: primera pasada CHANGES_REQUESTED — R10 sin cobertura (los dos campos nuevos de Settings no estaban testeados).
- Implementer fix: `test_embedding_batch_size_and_device_overridable_from_env` + `EXPECTED_DEFAULTS` ampliado en `tests/test_config.py`.
- Reviewer re-review: APROBADO (R10 verificado por mutación, sin regresión). Informe en `progress/review_f3-embeddings-provider.md`.
- F3 marcada `done` en `feature-list.json`; entrada añadida a `progress/history.md`.

## Próximo paso

Siguiente feature por orden de roadmap: **`f4-vector-store-pgvector`** (status `pending`, depende de f3 ✅). Flujo: leader lanza spec-author → `spec_ready` → ⏸ aprobación humana → implementer → reviewer.

Alternativa desbloqueada: **`f7-llm-provider-ollama`** (depende solo de f0 ✅), buen candidato para paralelizar — no toca pgvector ni torch.

## Riesgos anotados

- Python 3.14: f4 (pgvector) necesita `psycopg`/driver con wheels para 3.14; el spec de f4 debe aislar la dependencia de BD detrás de la interfaz `VectorStore` con un fake en memoria para tests unitarios (mismo patrón que f3 con `FakeEmbeddingProvider` + `@pytest.mark.integration` para la implementación real).
- f4 requiere un Postgres+pgvector real para tests de integración → marcar `@pytest.mark.integration`, excluido de init.sh.
