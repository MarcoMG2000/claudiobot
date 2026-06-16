# Review — feature f4-vector-store-pgvector · Slice B (pgvector + migration)

**Veredicto:** APPROVED

> Alcance juzgado: SOLO Slice B (tasks B1–B4 + "Slice B exit criteria").
> Slice A ya commiteada/aprobada; Slice C (`IndexingPipeline`, módulo `index/`)
> deliberadamente NO implementada — fuera de alcance, no se penaliza.

## Resultados objetivos clave

- **Lazy-import isolation (crítico): OK.**
  - `import wowrag.store.pgvector_store` y
    `from wowrag.store import PgVectorStore, VectorStore, VectorStoreError, FakeVectorStore`
    funcionan SIN `psycopg`/`pgvector` instalados (verificado: `IMPORT_OK driver-free`).
  - El import del driver es lazy, dentro de `__init__` (`pgvector_store.py:49-57`),
    espejo de `bge_m3.py:29-35`.
  - `PgVectorStore(dsn=..., dimension=...)` sin driver lanza `VectorStoreError`
    (mensaje "Postgres driver not installed. Install store dependencies: pip install
    -r requirements-pg.txt"), NO `ImportError` (verificado en runtime).
  - R13 (`test_pgvector_module_importable_without_driver`, `test_store_interface.py:65`)
    y R14 (`test_pgvector_instantiation_raises_without_driver`, `test_store_fake.py:104`)
    son tests unit (NO `@pytest.mark.integration`), corren en `init.sh` y PASAN
    (`2 passed`).

- **Dep isolation: OK.**
  - `requirements-pg.txt` existe con `psycopg[binary]>=3.2.0` y `pgvector>=0.3.0`
    (`requirements-pg.txt:6-7`) + comentario que lo marca excluido de `init.sh`.
  - NO referenciado en `requirements.txt` (solo deps base pineadas) ni en `init.sh`
    (grep `requirements-pg` en `init.sh` → sin coincidencias).
  - `requirements.txt` no contiene `psycopg`/`pgvector` (solo el comentario
    "deferred" pre-existente). `test_requirements_pinned.py` sigue verde dentro de
    los 101 passed.

- **Contract conformance: OK.**
  - `PgVectorStore` satisface el Protocol `VectorStore` estructuralmente (property
    `dimension`, `ensure_schema`, `upsert`, `similarity_search`); sin herencia.
  - `similarity_search` devuelve `list[tuple[Chunk, float]]` (`pgvector_store.py:136-170`);
    SQL `1 - (embedding <=> %s) AS score ... ORDER BY embedding <=> %s LIMIT %s`
    → orden por distancia asc == score desc (R9/R10).
  - Dimensión desde `embedding_dim` (param `dimension`, single source of truth,
    `pgvector_store.py:74-76`); tabla desde `vector_table` (param `table`).
  - `distance_metric` mapeado a operador pgvector vía `_METRIC_OPERATORS`
    (`cosine`→`<=>`, `l2`→`<->`, `inner_product`→`<#>`, `pgvector_store.py:26-30`);
    métrica desconocida → `VectorStoreError`. Default `cosine`.
  - Cero referencias a `RetrievedChunk` en código Slice B (la única mención en
    `src/` es docstring forward-looking pre-existente en `models.py`, intacto).

- **Migration: OK.**
  - `migrations.sql` idempotente: `CREATE EXTENSION IF NOT EXISTS vector`,
    `CREATE TABLE IF NOT EXISTS {table}`, `CREATE INDEX IF NOT EXISTS` HNSW
    `vector_cosine_ops` (`migrations.sql:6-18`).
  - Parametrizada por `{table}`/`{dim}` (de `Settings`, confianza); valores de fila
    siempre por parámetros psycopg, nunca interpolados.

- **Integration tests: OK.**
  - Los 5 tests de `test_store_pgvector.py` llevan `@pytest.mark.integration`
    (líneas 66,72,94,106,123) + `importorskip("psycopg"/"pgvector")` a nivel de
    módulo. Se omiten en `init.sh` (verificado: `SKIPPED ... could not import 'psycopg'`).

- **`./init.sh`: VERDE — exit 0.**
  - `101 passed, 2 skipped in 0.23s`. Los 2 skipped son exactamente
    `test_store_pgvector.py` (importorskip psycopg) y `test_embeddings_bge_m3.py`
    (importorskip FlagEmbedding, pre-existente). Coincide con lo esperado.

- **Slice isolation: OK.**
  - No existe `src/wowrag/index/` ni `IndexingPipeline` (glob vacío; grep sin
    coincidencias en `src/`).
  - `base.py`, `fake.py`, `models.py` NO modificados (git status/diff: no aparecen).
  - `feature-list.json` mantiene f4 en `in_progress`, NO `done`.

- **Conventions: OK.**
  - `from __future__ import annotations` (`pgvector_store.py:15`).
  - Excepción de dominio `VectorStoreError` para todos los fallos (driver ausente,
    métrica inválida, longitudes, dimensión, conexión `pgvector_store.py:81-82` R25).
  - Lazy import refleja `bge_m3.py`. Sin `print()`/TODO/secretos/credenciales
    hardcodeadas en SQL o código (grep sin coincidencias).

## Trazabilidad requirements ↔ tests (R's de Slice B)
- R12: [x] `test_upsert_and_search_roundtrip` (`test_store_pgvector.py:73`, integration)
- R13: [x] `test_pgvector_module_importable_without_driver` (`test_store_interface.py:65`, unit, corre en init.sh, PASA)
- R14: [x] `test_pgvector_instantiation_raises_without_driver` (`test_store_fake.py:104`, unit, corre en init.sh, PASA)
- R15: [x] `test_ensure_schema_creates_and_idempotent` (`test_store_pgvector.py:67`, integration)
- R16: [x] `test_vector_column_uses_embedding_dim` (`test_store_pgvector.py:107`, integration)
- R17: [x] `test_ensure_schema_creates_and_idempotent` + `migrations.sql` cargado por `ensure_schema`
- R18: [x] `test_upsert_and_search_roundtrip` (asserts source_url/title/section, `test_store_pgvector.py:88-91`)
- R25: [x] `test_bad_dsn_raises_vector_store_error` (`test_store_pgvector.py:124`, integration)
- R7/R8/R10/R19 (refuerzo real): cubiertos a nivel contrato por el fake (Slice A) y
  reforzados en integración (`test_upsert_replaces_existing_chunk_id` R8); guards
  idénticos en `PgVectorStore.upsert`/`similarity_search`.

## Tasks completas (Slice B)
- B1 — `migrations.sql`: [x]
- B2 — `PgVectorStore` (import lazy): [x]
- B3 — `requirements-pg.txt`: [x]
- B4 — `tests/test_store_pgvector.py` (integración) + R13/R14 unit deferidos: [x]
- C1, C2, Z1: [ ] (Slice C / cierre — fuera de alcance de Slice B, correcto)

## Checkpoints (relevantes a Slice B)
- C1 (`init.sh` exit 0): [x]
- C2 (≤1 feature `in_progress`; f4 `in_progress`, no `done`): [x]
- C3 (capas: store detrás de interfaz, SQL solo en capa store; reqs pineadas; sin prints/secretos/TODOs): [x]
- C4 (tests por módulo; lógica con fakes; integración marcada; `not integration` >0 verde): [x]
- C5 (grounding/abstención): [ ] N/A en f4 (diferido a f5/f8)
- C6 (SDD: specs presentes; EARS; R↔test de Slice B cubierto): [x] (cierre total R1–R33 se valida en Z1 al cerrar la feature completa)

## Cambios requeridos
Ninguno. Slice B cumple todos los criterios objetivos y de exit. APPROVED.
