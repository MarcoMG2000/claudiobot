# Implementación — f4-vector-store-pgvector · Slice B (pgvector + migración)

- **Feature:** `f4-vector-store-pgvector` (stacked-PR slice 2 de 3)
- **Slice:** B — `PgVectorStore` + `migrations.sql` + `requirements-pg.txt`
- **Agente:** implementer
- **Fecha:** 2026-06-16
- **Estado:** completado, pendiente de review (NO marcada `done`)
- **Baseline previo:** Slice A DONE, aprobada por reviewer; `./init.sh` 99 passed,
  1 skipped, exit 0.

## Alcance ejecutado (tasks B1–B4 — y nada más)

Slice A NO se rehízo. Slice C (`IndexingPipeline`, módulo `index/`) NO se tocó.
`models.py`, `base.py`, `fake.py` (contrato), `feature-list.json` NO se modificaron.

## Archivos creados / modificados

| Archivo | Acción | Task |
|---------|--------|------|
| `src/wowrag/store/migrations.sql` | NUEVO — DDL idempotente parametrizada `{table}`/`{dim}`; `CREATE EXTENSION IF NOT EXISTS vector`; tabla con PK `chunk_id` + metadata + `embedding vector({dim})`; índice HNSW `vector_cosine_ops` | B1 |
| `src/wowrag/store/pgvector_store.py` | NUEVO — `PgVectorStore` con import lazy de `psycopg`/`pgvector` en `__init__` → `VectorStoreError` si falta (espejo de `BgeM3Embeddings`); `ensure_schema`/`upsert` (ON CONFLICT)/`similarity_search` (`<=>`, `1 - dist`, ORDER BY dist asc) | B2 |
| `requirements-pg.txt` | NUEVO — `psycopg[binary]>=3.2.0`, `pgvector>=0.3.0`; comentario que lo marca excluido de `init.sh` y del base `requirements.txt` | B3 |
| `src/wowrag/store/__init__.py` | EDITADO — ahora re-exporta también `PgVectorStore` (diferido por Slice A en A4) | B2/B4 |
| `tests/test_store_pgvector.py` | NUEVO — 5 tests `@pytest.mark.integration` + `importorskip("psycopg"/"pgvector")` | B4 |
| `tests/test_store_interface.py` | EDITADO — añadido `test_pgvector_module_importable_without_driver` (R13, unit, corre en init.sh) | B4 (deferido A5) |
| `tests/test_store_fake.py` | EDITADO — añadido `test_pgvector_instantiation_raises_without_driver` (R14, unit, corre en init.sh) | B4 (deferido A6) |
| `specs/f4-vector-store-pgvector/tasks.md` | EDITADO — B1–B4 marcadas `[x]`; C/Z sin tocar | — |

## Trazabilidad R↔test (R's de Slice B)

R's cubiertos por Slice B según `tasks.md` B1–B4: **R12, R13, R14, R15, R16, R17,
R18, R25** (más R7/R8/R10/R19 que la implementación real comparte con el contrato,
ya cubiertos a nivel de contrato por el fake en Slice A y reforzados aquí en
integración).

| R | Requisito | Test que lo cubre | Tipo | Corre en init.sh |
|---|-----------|-------------------|------|------------------|
| R12 | `PgVectorStore` concreta pgvector | `test_upsert_and_search_roundtrip` (`test_store_pgvector.py`) | integration | no (skip) |
| R13 | módulo importable sin driver | `test_pgvector_module_importable_without_driver` (`test_store_interface.py`) | unit | **sí (pasa)** |
| R14 | instanciar sin driver → `VectorStoreError` no `ImportError` | `test_pgvector_instantiation_raises_without_driver` (`test_store_fake.py`) | unit (skipif driver instalado) | **sí (pasa)** |
| R15 | `ensure_schema` crea + idempotente | `test_ensure_schema_creates_and_idempotent` | integration | no (skip) |
| R16 | columna `vector(embedding_dim)` | `test_vector_column_uses_embedding_dim` | integration | no (skip) |
| R17 | DDL desde `migrations.sql` | `test_ensure_schema_creates_and_idempotent` (lee `migrations.sql`) + `test_upsert_and_search_roundtrip` | integration | no (skip) |
| R18 | metadata persistida en el `Chunk` devuelto | `test_upsert_and_search_roundtrip` (asserts source_url/title/section) | integration | no (skip) |
| R25 | conexión fallida → `VectorStoreError` | `test_bad_dsn_raises_vector_store_error` | integration | no (skip) |
| R8 (refuerzo real) | upsert por `chunk_id` reemplaza | `test_upsert_replaces_existing_chunk_id` | integration | no (skip) |
| R10 (refuerzo real) | coseno, score desc | `test_upsert_and_search_roundtrip` (orden + score sorted desc) | integration | no (skip) |

> R7/R19 (validación de longitudes / dimensión) ya están cubiertos a nivel de
> contrato por `FakeVectorStore` en Slice A; la rama equivalente en
> `PgVectorStore` es el mismo guard inicial antes de tocar la DB.

## Estado de las tasks

- [x] B1 — `migrations.sql`
- [x] B2 — `PgVectorStore` (import lazy)
- [x] B3 — `requirements-pg.txt`
- [x] B4 — `tests/test_store_pgvector.py` (integración) + R13/R14 unit deferidos
- C1, C2, Z1 — sin tocar (Slice C / cierre, fuera de alcance)

## Conteo de tests nuevos

- **Unit (corren en init.sh): 2** → R13 `test_pgvector_module_importable_without_driver`,
  R14 `test_pgvector_instantiation_raises_without_driver`.
- **Integration (excluidos de init.sh): 5** → en `test_store_pgvector.py`
  (`test_ensure_schema_creates_and_idempotent`, `test_upsert_and_search_roundtrip`,
  `test_upsert_replaces_existing_chunk_id`, `test_vector_column_uses_embedding_dim`,
  `test_bad_dsn_raises_vector_store_error`).

## Self-verify — `./init.sh`

```
==> Ejecutando pytest (no integration)
101 passed, 2 skipped in 0.24s
==> init OK
```

- **Exit code:** 0
- **Passed:** 101 (99 previos + 2 unit nuevos R13/R14) — coincide con lo esperado.
- **Skipped:** 2 = `test_store_pgvector.py` (importorskip psycopg, driver ausente)
  + `test_embeddings_bge_m3.py` (importorskip FlagEmbedding, pre-existente).
  Confirmado vía `-rs`:
  `SKIPPED tests/test_store_pgvector.py:29: could not import 'psycopg'`.
- `from wowrag.store import PgVectorStore, VectorStore, VectorStoreError, FakeVectorStore`
  funciona SIN el driver instalado (verificado con `PYTHONPATH=src python -c ...`).
- `requirements-pg.txt` NO está referenciado en `requirements.txt` ni en `init.sh`
  (verificado por grep; la única mención de `psycopg` en `requirements.txt` es el
  comentario "deferred" ya existente, que `test_requirements_pinned.py` ignora →
  sigue verde dentro de los 101 passed).

## Conformidad con convenciones

- `from __future__ import annotations` en `pgvector_store.py`.
- Import lazy de `psycopg`/`pgvector` dentro de `__init__` (idéntico en espíritu a
  `bge_m3.py`); driver ausente → excepción de dominio `VectorStoreError` con hint de
  instalación, nunca `ImportError`.
- Conformidad estructural con el Protocol `VectorStore` (no herencia).
- Retorno `list[tuple[Chunk, float]]`; sin referencias a `RetrievedChunk`.
- Valores (texto, vectores) siempre vía parámetros psycopg; solo `{table}`/`{dim}`
  (de `Settings`, confianza) se interpolan en el DDL.

## Desviaciones

Ninguna desviación del spec. Detalles de decisiones tomadas dentro del margen del
diseño:

1. **`metric` → operador**: añadido un mapeo `_METRIC_OPERATORS`
   (`cosine`→`<=>`, `l2`→`<->`, `inner_product`→`<#>`) y validación del `metric`
   en `__init__`. El diseño §6 nombra `<=>` como operador coseno y menciona el
   mapeo métrica→operador; el dict lo materializa sin cambiar el contrato (default
   `cosine`). Una métrica desconocida lanza `VectorStoreError` (coherente con la
   excepción de dominio R24).
2. **`upsert` usa `executemany`** con `ON CONFLICT (chunk_id) DO UPDATE` (R8) y
   retorna `len(chunks)`; `len==0` → `0` (sin tocar DB). El diseño dejaba el cuerpo
   con `...`; esta es la materialización directa del contrato.
3. **R14 test con `skipif`**: el test de instanciación-sin-driver se salta si el
   driver SÍ estuviera instalado (no es el caso en este entorno: el driver está
   ausente, así que el test EJECUTA y pasa). Esto evita un falso fallo en una
   máquina con psycopg instalado, manteniendo R14 verificado en el entorno objetivo.
   No es integration: corre en `init.sh`.
4. **`test_vector_column_uses_embedding_dim` (R16)** consulta `pg_attribute.atttypmod`
   (pgvector almacena la dimensión declarada ahí); fixture con tabla throwaway por
   test (`DROP TABLE IF EXISTS` en teardown) y skip si `WOWRAG_TEST_DSN` no está.

## Notas para el reviewer

- Los 5 tests de integración requieren Postgres+pgvector vivo (`WOWRAG_TEST_DSN`) y
  el driver (`pip install -r requirements-pg.txt`); por diseño NO corren en
  `init.sh`. Su verde real se comprueba fuera de la suite base.
- Tras apilar Slice B, los 2 casos diferidos de A5/A6 (R13/R14) quedan verdes en
  `init.sh`, cumpliendo el "Slice B exit criteria".
- NO marcar la feature `done`: pendiente Slice C + cierre Z1.
