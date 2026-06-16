# Implementación — f4-vector-store-pgvector · Slice A (interfaz + fake + config)

- **Feature:** `f4-vector-store-pgvector` (status `in_progress`, spec aprobado)
- **Slice:** A únicamente (de 3 stacked: A → B → C). B y C NO implementados.
- **Agente:** implementer
- **Fecha:** 2026-06-16
- **Resultado:** success — `./init.sh` exit 0, 99 passed + 1 skipped.

## Alcance ejecutado (A1–A7) y nada más

Implementado: interfaz `VectorStore` + excepción de dominio, `FakeVectorStore`
in-memory (coseno stdlib), re-exports del paquete `store`, 2 campos nuevos de
`Settings`, y los tests unitarios DB-free del contrato + fake + config.

NO implementado (fuera de Slice A, por diseño):
- Slice B: `PgVectorStore`, `migrations.sql`, `requirements-pg.txt`, import de
  `psycopg`/`pgvector`, tests `@pytest.mark.integration`.
- Slice C: `IndexingPipeline`, módulo `index/`.
- `models.py` intacto. `feature-list.json` NO marcado `done`.

## Ficheros creados

- `src/wowrag/store/base.py` — `VectorStoreError(Exception)` + `VectorStore`
  Protocol (estructural, sin herencia): propiedad `dimension`, `ensure_schema`,
  `upsert`, `similarity_search -> list[tuple[Chunk, float]]` (par `(chunk, score)`,
  score desc). Importa `Chunk` de `wowrag.models`; sin `RetrievedChunk`.
- `src/wowrag/store/fake.py` — `FakeVectorStore` solo stdlib (`math`), in-memory
  (`dict[chunk_id] -> (Chunk, vector)`), coseno + top-k score desc, upsert por id,
  validación de longitudes y de dimensión, `ensure_schema` no-op. Cero imports
  de psycopg/pgvector/red.
- `tests/test_store_interface.py` — contrato vía `FakeVectorStore` (6 tests).
- `tests/test_store_fake.py` — propiedades del fake (6 tests).

## Ficheros editados

- `src/wowrag/config.py` — añadidos `vector_table: str = "chunks"` y
  `distance_metric: str = "cosine"` a `Settings`. `postgres_dsn`/`embedding_dim`/
  `top_k` NO redefinidos (R32).
- `src/wowrag/store/__init__.py` — reemplazado placeholder f0; re-exporta
  `VectorStore`, `VectorStoreError`, `FakeVectorStore` (`__all__`). El re-export de
  `PgVectorStore` se difiere a Slice B (su módulo aún no existe; importarlo
  rompería `init.sh`).
- `tests/test_config.py` — `EXPECTED_DEFAULTS` ampliado con `vector_table`
  (`"chunks"`) y `distance_metric` (`"cosine"`); nuevo
  `test_vector_table_and_metric_overridable_from_env` (env-override).
- `specs/f4-vector-store-pgvector/tasks.md` — A1–A7 marcadas `[x]` (con notas de
  los sub-casos diferidos a B); B/C sin marcar.
- `progress/current.md` — feature en curso + plan.

## Trazabilidad R↔test (R's de Slice A)

| R    | Significado (resumen)                              | Test que lo cubre |
|------|----------------------------------------------------|-------------------|
| R1   | `VectorStore` Protocol definido                    | `test_store_interface.py::test_fake_satisfies_protocol` |
| R2   | `ensure_schema()` idempotente                      | `test_store_interface.py::test_ensure_schema_idempotent_noop` |
| R3   | `upsert(chunks, embeddings) -> int`                | `test_store_interface.py::test_upsert_returns_count` (firma + retorno) |
| R4   | `similarity_search -> list[tuple[Chunk, float]]`   | `test_store_fake.py::test_search_returns_chunk_score_pairs` |
| R5   | propiedad `dimension`                              | `test_store_fake.py::test_dimension_default_and_custom` |
| R6   | upsert N → N filas, emparejadas por índice         | `test_store_interface.py::test_upsert_returns_count` |
| R7   | longitudes desiguales → `VectorStoreError`         | `test_store_interface.py::test_upsert_length_mismatch_raises` |
| R8   | upsert por `chunk_id` reemplaza (único)            | `test_store_fake.py::test_upsert_replaces_by_chunk_id` |
| R9   | ≤ k pares, ordenados score desc                    | `test_store_fake.py::test_search_orders_by_cosine_desc`, `::test_search_respects_k` |
| R10  | métrica coseno, mayor = más similar                | `test_store_fake.py::test_search_orders_by_cosine_desc` |
| R11  | almacén vacío → `[]` sin excepción                 | `test_store_interface.py::test_empty_store_search_returns_empty` |
| R18  | `Chunk` devuelto conserva metadata                 | `test_store_fake.py::test_result_carries_metadata` |
| R19  | dim de query incorrecta → `VectorStoreError`       | `test_store_interface.py::test_search_wrong_dimension_raises` |
| R24  | `VectorStoreError(Exception)` definido en base.py  | usado en `test_upsert_length_mismatch_raises`, `test_search_wrong_dimension_raises` |
| R26  | `FakeVectorStore` solo stdlib, sin psycopg/pgvector| `test_store_interface.py::test_fake_satisfies_protocol` (+ grep: cero imports DB en fake.py) |
| R27  | coseno con `math`, top-k score desc, paridad real  | `test_store_fake.py::test_search_orders_by_cosine_desc` |
| R28  | upsert por id en fake reemplaza (paridad R8)       | `test_store_fake.py::test_upsert_replaces_by_chunk_id` |
| R29  | `ensure_schema()` no-op idempotente                | `test_store_interface.py::test_ensure_schema_idempotent_noop` |
| R30  | `vector_table` default `"chunks"` + override env   | `test_config.py::test_settings_defaults_without_env` (default), `::test_vector_table_and_metric_overridable_from_env` (override) |
| R31  | `distance_metric` default `"cosine"` + override    | `test_config.py::test_settings_defaults_without_env` (default), `::test_vector_table_and_metric_overridable_from_env` (override) |
| R32  | reutiliza `postgres_dsn`/`embedding_dim`/`top_k`   | `test_config.py::test_settings_defaults_without_env` (siguen presentes, no redefinidos) |
| R33  | re-export `VectorStore`/`VectorStoreError`/`FakeVectorStore` | import en `test_store_interface.py` + `test_store_fake.py` (`from wowrag.store import ...`) |

> R's de Slice B (R12–R17, R25) y Slice C (R20–R23) NO aplican a este slice.
> R33 en Slice A cubre las 3 clases disponibles; `PgVectorStore` se añadirá al
> re-export en Slice B.

## Checklist A1–A7

- [x] A1 — `store/base.py`: `VectorStore` Protocol + `VectorStoreError`.
- [x] A2 — `store/fake.py`: `FakeVectorStore` in-memory stdlib.
- [x] A3 — `config.py`: `vector_table` + `distance_metric`.
- [x] A4 — `store/__init__.py`: re-export interfaz/excepción/fake (PgVectorStore → B).
- [x] A5 — `tests/test_store_interface.py` (casos DB-free; R13 → B).
- [x] A6 — `tests/test_store_fake.py` (casos del fake; R14 → B).
- [x] A7 — `tests/test_config.py`: defaults + override de ambos campos.

## Verificación final

```
==> wow-classic-rag :: init
==> Python: Python 3.14.4
==> Instalando dependencias
==> Ejecutando pytest (no integration)
99 passed, 1 skipped in 0.23s
==> init OK
EXIT_CODE=0
```

- 86 previos + 13 nuevos Slice-A = 99 passed; 1 skipped (integración bge_m3 de f3).
- `from wowrag.store import VectorStore, FakeVectorStore, VectorStoreError` → OK.
- `models.py` sin cambios (verificado con `git diff --stat`, vacío).
- Sin `import psycopg`/`pgvector` ni modelo `RetrievedChunk` en código de Slice A
  (las menciones en docstrings/comentarios son descriptivas, no código).

## Desviaciones / decisiones

1. **A4 — `PgVectorStore` no re-exportado en Slice A.** El leader acotó el scope
   a "re-export the interface, fake, and exception". El módulo `pgvector_store.py`
   pertenece a Slice B; importarlo ahora rompería `from wowrag.store import ...`
   y por tanto `init.sh`. tasks.md A4 contempla este orden ("coordina el orden si
   construyes A antes que B"). El re-export de `PgVectorStore` se añade al apilar B.
2. **A5/A6 — 2 sub-casos diferidos a Slice B.**
   `test_pgvector_module_importable_without_driver` (R13) y
   `test_pgvector_instantiation_raises_without_driver` (R14) requieren el módulo
   `pgvector_store.py` de Slice B. tasks.md A5/A6 lo permiten explícitamente
   ("se habilitan al apilar B"). Quedan documentados como pendientes de B;
   R13/R14 son R's de Slice B, no de Slice A.

## Pendiente (para el reviewer / siguientes slices)

- Reviewer valida trazabilidad de Slice A antes de cerrar/encadenar.
- Slice B: `PgVectorStore` + `migrations.sql` + `requirements-pg.txt` + tests
  integración; al apilarlo, añadir el re-export de `PgVectorStore` y los 2
  sub-casos R13/R14.
- Slice C: `IndexingPipeline` en `index/`.
- NO marcar la feature `done` hasta cerrar las 3 slices y aprobación del reviewer.
