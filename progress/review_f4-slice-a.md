# Review — f4-vector-store-pgvector · Slice A (interfaz + fake + config)

**Veredicto:** APPROVED

> Alcance juzgado: **solo Slice A** (tasks A1–A7). Slice B (pgvector/migración) y
> Slice C (pipeline de indexado) NO implementados — correcto por diseño (stacked
> PRs A → B → C). Los R's de B (R12–R17, R25) y C (R20–R23) NO se evalúan aquí.

## Trazabilidad requirements ↔ tests (R's de Slice A)

R's de Slice A según tasks.md A1–A7: R1–R11, R18, R19, R24, R26–R33. Confirmado
contra tasks.md. Cada uno con ≥1 test que lo ejercita de verdad:

- R1  [x] `test_store_interface.py::test_fake_satisfies_protocol` (asignación a `VectorStore`)
- R2  [x] `test_store_interface.py::test_ensure_schema_idempotent_noop`
- R3  [x] `test_store_interface.py::test_upsert_returns_count` (firma + retorno int)
- R4  [x] `test_store_fake.py::test_search_returns_chunk_score_pairs` (par `(Chunk, float)`)
- R5  [x] `test_store_fake.py::test_dimension_default_and_custom`
- R6  [x] `test_store_interface.py::test_upsert_returns_count` (N → N)
- R7  [x] `test_store_interface.py::test_upsert_length_mismatch_raises`
- R8  [x] `test_store_fake.py::test_upsert_replaces_by_chunk_id` (last-write-wins)
- R9  [x] `test_store_fake.py::test_search_orders_by_cosine_desc`, `::test_search_respects_k`
- R10 [x] `test_store_fake.py::test_search_orders_by_cosine_desc` (orden coseno desc)
- R11 [x] `test_store_interface.py::test_empty_store_search_returns_empty`
- R18 [x] `test_store_fake.py::test_result_carries_metadata` (source_url/title/section)
- R19 [x] `test_store_interface.py::test_search_wrong_dimension_raises`
- R24 [x] ejercitado en `test_upsert_length_mismatch_raises` + `test_search_wrong_dimension_raises` (se lanza `VectorStoreError`)
- R26 [x] `test_store_interface.py::test_fake_satisfies_protocol` + verificado: `fake.py` solo importa `math`, sin psycopg/pgvector/red
- R27 [x] `test_store_fake.py::test_search_orders_by_cosine_desc` (coseno con math, top-k score desc)
- R28 [x] `test_store_fake.py::test_upsert_replaces_by_chunk_id` (paridad R8)
- R29 [x] `test_store_interface.py::test_ensure_schema_idempotent_noop` (no-op idempotente)
- R30 [x] `test_config.py::test_settings_defaults_without_env` (default `"chunks"` vía EXPECTED_DEFAULTS) + `::test_vector_table_and_metric_overridable_from_env` (override)
- R31 [x] `test_config.py::test_settings_defaults_without_env` (default `"cosine"`) + `::test_vector_table_and_metric_overridable_from_env` (override)
- R32 [x] `test_config.py::test_settings_defaults_without_env` (postgres_dsn/embedding_dim/top_k siguen presentes, no redefinidos; config.py no los reescribe)
- R33 [x] `from wowrag.store import FakeVectorStore, VectorStore, VectorStoreError` en cabecera de ambos test files (import real, no comentado)

**Resultado: todos los R's de Slice A cubiertos. Cero huecos.**

R13/R14 (import lazy / instanciación sin driver de `PgVectorStore`) son R's de
Slice B; A5/A6 los difieren explícitamente con nota en tasks.md ("se habilitan al
apilar B — requieren el módulo `pgvector_store.py`"). Deferral legítimo, no omisión.

## Return contract (objetivo 2)

[x] `similarity_search` declara `-> list[tuple[Chunk, float]]` en `base.py:72-74`
    y `fake.py:49-51`; devuelve pares `(chunk, score)` ordenados score-desc
    (`fake.py:60-66`).
[x] Usa el `Chunk` existente (`from wowrag.models import Chunk`, base.py:17,
    fake.py:13). Validado por `test_search_returns_chunk_score_pairs`
    (`isinstance(chunk, Chunk)`, `isinstance(score, float)`).
[x] NO existe `RetrievedChunk` en `src/` ni en `tests/` (grep: 0 coincidencias en
    código; las menciones en docstrings son descriptivas).
[x] `models.py` INTACTO — `git diff HEAD -- src/wowrag/models.py` vacío.

## Config-gap mutation result (objetivo 3 — CRÍTICO, lo que hundió f3)

[x] Ambos campos en `EXPECTED_DEFAULTS` (test_config.py:18-19) → cubiertos por
    `test_settings_defaults_without_env` (default-assert).
[x] Ambos con env-override en `test_vector_table_and_metric_overridable_from_env`
    (test_config.py:61-68; `VECTOR_TABLE`, `DISTANCE_METRIC`).
[x] **Mutación verificada en venv (.venv/Scripts/python.exe):**
    - Renombrar `vector_table` → `vector_table_X`: **3 failed, 4 passed** (rompe
      defaults, exposes-all-fields y el env-override). Exit 1.
    - Borrar la línea de `distance_metric`: **3 failed, 4 passed** (mismas).
      Exit 1.
    Renombrar/borrar cualquiera de los dos campos rompe la suite. El hueco de f3
    está cerrado.

## Slice isolation (objetivo 4)

[x] Sin `PgVectorStore` (clase) en código — solo en docstrings/`__init__.py`
    comentario. Sin `import psycopg` / `import pgvector` (grep en `src/wowrag/store/`:
    0 imports reales; todas las coincidencias son texto de docstring).
[x] Sin `migrations.sql` — `src/wowrag/store/` contiene solo `__init__.py`,
    `base.py`, `fake.py`.
[x] Sin `requirements-pg.txt` (raíz) — ausente, correcto.
[x] Sin `IndexingPipeline` / módulo `index/` — `src/wowrag/index/` no existe.
[x] Deferrals A4/A5/A6 coinciden con las notas de tasks.md:
    - A4: re-export de `PgVectorStore` diferido a B (su módulo no existe;
      importarlo rompería `init.sh`). `__init__.py` re-exporta los 3 disponibles.
    - A5: `test_pgvector_module_importable_without_driver` (R13) → B.
    - A6: `test_pgvector_instantiation_raises_without_driver` (R14) → B.
    Legítimos, documentados en tasks.md y en `impl_f4-slice-a.md` §Desviaciones.

## Tests green (objetivo 5)

[x] `./init.sh` → exit 0.
    ```
    ==> Python: Python 3.14.4
    ==> Ejecutando pytest (no integration)
    99 passed, 1 skipped in 0.23s
    ==> init OK
    INIT_EXIT=0
    ```
    99 passed, 1 skipped — coincide exactamente con lo reportado por el implementer.

## Conventions (objetivo 6) — paridad con f3

[x] `from __future__ import annotations` en `base.py:13` y `fake.py:9`.
[x] Protocol estructural (`VectorStore(Protocol)`, base.py:28) — sin herencia,
    consistente con `CorpusLoader`/`Chunker`/`EmbeddingProvider`.
[x] Excepción de dominio `VectorStoreError(Exception)` en `base.py:20`.
[x] Re-exports vía `store/__init__.py` con `__all__` (R33).
[x] Sin `print()` de debug, sin TODO/FIXME/XXX, sin secretos (grep: 0 en `store/`).

## Tasks (objetivo 7)

[x] A1–A7 marcadas `[x]` en tasks.md (líneas 24, 37, 49, 57, 68, 87, 106).
[x] B1–B4 y C1–C2 y Z1 siguen `[ ]` (no implementadas — correcto).

## Checkpoints (recortados al alcance Slice A)

- C1 [x] Arnés completo; `./init.sh` exit 0.
- C2 [x] Una sola feature `in_progress` (f4); `progress/current.md` describe la sesión.
- C3 [x] Capa `store/` respeta arquitectura; vector store detrás de su interfaz;
         sin SQL/HTTP fuera de capa; sin print/secretos/TODO. (pgvector real → B.)
- C4 [x] Test por módulo nuevo (`base.py`+`fake.py` → `test_store_interface.py`,
         `test_store_fake.py`); lógica con fakes; `pytest -m "not integration"`
         99 verdes.
- C5 [~] No aplica a Slice A (abstención/citas/prompt son de f5/f6/f8).
- C6 [x] `specs/f4-vector-store-pgvector/` con requirements/design/tasks; EARS;
         cada R de Slice A con test. (No `done`: f4 sigue `in_progress`.)

## Cambios requeridos

Ninguno. Slice A aprobado.

## Nota para el encadenado a Slice B

Al apilar B, recordar (ya previsto en tasks.md, no es defecto de A):
1. Añadir el re-export de `PgVectorStore` en `store/__init__.py` + a `__all__`.
2. Habilitar `test_pgvector_module_importable_without_driver` (R13) y
   `test_pgvector_instantiation_raises_without_driver` (R14) — dejarlos verdes con
   el módulo `pgvector_store.py` presente.
