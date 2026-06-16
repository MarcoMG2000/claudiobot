# Tasks — f4-vector-store-pgvector

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests unitarios usan solo stdlib + fakes (`FakeVectorStore`,
> `FakeEmbeddingProvider`); sin Postgres, sin driver, sin red. La trazabilidad
> `R<n>` ↔ test es obligatoria (`docs/verification.md`); nombra o comenta cada
> test con su `R<n>`.
>
> **Entrega: 3 PRs encadenados (stacked).** En la puerta de aprobación el humano
> decidió partir f4 en 3 slices (ver `design.md` §0). Cada slice es
> **auto-contenido, verde bajo `init.sh` e independientemente commiteable**.
> Constrúyelos y mándalos **en orden A → B → C** (B se apila sobre A, C sobre B).
> `similarity_search` devuelve `list[tuple[Chunk, float]]` (par `(chunk, score)`,
> score desc) usando el `Chunk` existente — `models.py` NO se toca en f4 (el
> wrapper `RetrievedChunk` se difiere a f5).

---

## Slice A — interfaz + fake + config

> Interfaz + excepción + fake in-memory + 2 campos de `Settings` + exports + sus
> tests unitarios. Sin DB, sin driver, sin `psycopg`/`pgvector`.

- [x] **A1 — Interfaz `VectorStore` y excepción `VectorStoreError`.**
  Crear `src/wowrag/store/base.py` con:
  - `VectorStoreError(Exception)` — excepción de dominio.
  - `VectorStore` Protocol con: propiedad de solo lectura `dimension: int`;
    `ensure_schema() -> None`; `upsert(chunks, embeddings) -> int`;
    `similarity_search(query_vector, k) -> list[tuple[Chunk, float]]` (importa
    `Chunk` de `wowrag.models`; NO importa ningún `RetrievedChunk`). Docstrings con
    el contrato: `ensure_schema` idempotente; `upsert` empareja por índice,
    valida longitudes, upsert por `chunk_id`, persiste metadata;
    `similarity_search` devuelve ≤ k pares `(Chunk, float)` por coseno score desc,
    almacén vacío → [], dimensión incorrecta → `VectorStoreError`.
  _(Cubre R1, R2, R3, R4, R5, R24)_

- [x] **A2 — `FakeVectorStore` in-memory.**
  Crear `src/wowrag/store/fake.py` con `FakeVectorStore` (solo stdlib `math`):
  - Constructor `__init__(self, dimension: int = 1024)`; propiedad `dimension`.
  - `ensure_schema()` no-op idempotente.
  - `upsert(chunks, embeddings)`: si longitudes difieren → `VectorStoreError`;
    guarda en `dict[chunk_id] -> (Chunk, vector)` (upsert por id); devuelve N.
  - `similarity_search(query_vector, k)`: dim incorrecta → `VectorStoreError`;
    almacén vacío → `[]`; calcula coseno con `math`, ordena score desc, devuelve
    top-k como pares `(Chunk, float)` (el `Chunk` conserva metadata).
  - Cero imports de `psycopg`/`pgvector`/red.
  _(Cubre R7, R8, R9, R10, R11, R18, R19, R26, R27, R28, R29)_

- [x] **A3 — Nuevos campos en `Settings`.**
  Editar `src/wowrag/config.py`, añadir a `Settings`:
  - `vector_table: str = "chunks"`
  - `distance_metric: str = "cosine"`
  NO redefinir `postgres_dsn`, `embedding_dim` ni `top_k` (ya existen; se
  reutilizan).
  _(Cubre R30, R31, R32)_

- [x] **A4 — Re-exportar desde `store/__init__.py`.**
  _(Slice A: re-exporta `VectorStore`, `VectorStoreError`, `FakeVectorStore`. El
  re-export de `PgVectorStore` se añade al apilar Slice B, cuando exista el módulo
  `pgvector_store.py` — importarlo antes rompería `init.sh`.)_
  Reemplazar el placeholder de `src/wowrag/store/__init__.py` con imports y
  `__all__` que exporten `VectorStore`, `VectorStoreError`, `FakeVectorStore`,
  `PgVectorStore`. (El re-export de `PgVectorStore` apunta al módulo de Slice B;
  como el import del driver es lazy en su `__init__`, el módulo es importable sin
  el driver — coordina el orden si construyes A antes que B, ver criterios.)
  _(Cubre R33)_

- [x] **A5 — `tests/test_store_interface.py`** (contrato vía `FakeVectorStore`).
  _(Slice A: todos los casos DB-free hechos. `test_pgvector_module_importable_without_driver`
  (R13) se añade al apilar Slice B — requiere el módulo `pgvector_store.py`.)_
  - `test_empty_store_search_returns_empty`: `similarity_search` sobre fake
    vacío → `[]`. _(R11)_
  - `test_upsert_returns_count`: `upsert(N chunks, N vecs)` → N. _(R6)_
  - `test_upsert_length_mismatch_raises`: longitudes distintas →
    `VectorStoreError`. _(R7)_
  - `test_search_wrong_dimension_raises`: `query_vector` de dim incorrecta →
    `VectorStoreError`. _(R19)_
  - `test_fake_satisfies_protocol`: `FakeVectorStore` asignable a `VectorStore`
    (Protocol estructural). _(R1, R26)_
  - `test_ensure_schema_idempotent_noop`: llamar `ensure_schema()` dos veces no
    lanza. _(R2, R29)_
  - `test_pgvector_module_importable_without_driver`:
    `import wowrag.store.pgvector_store` no lanza `ImportError` sin el driver. _(R13)_
    (Requiere que el módulo de Slice B exista; si construyes A primero, este caso
    se habilita al apilar B — déjalo verde en el slice donde el módulo ya exista.)

- [x] **A6 — `tests/test_store_fake.py`** (propiedades del fake).
  _(Slice A: todos los casos del fake hechos. `test_pgvector_instantiation_raises_without_driver`
  (R14) se añade al apilar Slice B — requiere la clase `PgVectorStore`.)_
  - `test_search_orders_by_cosine_desc`: con vectores conocidos, los pares
    `(Chunk, float)` salen ordenados por score coseno descendente. _(R9, R10)_
  - `test_search_returns_chunk_score_pairs`: cada elemento es `(Chunk, float)`
    (no un modelo `RetrievedChunk`). _(R4, R9)_
  - `test_search_respects_k`: con M > k filas, `similarity_search(q, k)` devuelve
    exactamente k. _(R9)_
  - `test_upsert_replaces_by_chunk_id`: upsert dos veces del mismo `chunk_id`
    deja una sola entrada (la última). _(R8, R28)_
  - `test_result_carries_metadata`: el `Chunk` del par devuelto conserva
    `source_url`, `title`, `section`. _(R18)_
  - `test_dimension_default_and_custom`: `FakeVectorStore()` → `dimension == 1024`;
    `FakeVectorStore(dimension=64)` → 64. _(R5)_
  - `test_pgvector_instantiation_raises_without_driver`: `PgVectorStore(dsn=...,
    dimension=...)` lanza `VectorStoreError` (no `ImportError`) sin driver. _(R14)_
    (Requiere el módulo de Slice B; ver nota en A5.)

- [x] **A7 — `tests/test_config.py`** (editar, añadir casos).
  - Añadir `vector_table` y `distance_metric` a `EXPECTED_DEFAULTS` (defaults
    `"chunks"` y `"cosine"`) → cubierto por el test de defaults. _(R30, R31)_
  - `test_vector_table_and_metric_overridable_from_env`: `monkeypatch.setenv`
    `VECTOR_TABLE` y `DISTANCE_METRIC` → `Settings` los refleja. _(R30, R31)_

**Slice A — exit criteria:** `./init.sh` exit 0 con los tests de A5–A7 (+ previos)
en verde; `from wowrag.store import VectorStore, VectorStoreError, FakeVectorStore`
funciona; `models.py` sin cambios; cada campo nuevo de `Settings` con test de
default y de override. (Los tests que tocan el módulo `pgvector_store` se habilitan
en cuanto exista ese módulo: si A se commitea antes que B, déjalos verdes al apilar
B, o crea un `pgvector_store.py` mínimo importable en A.)

---

## Slice B — pgvector implementation + migration

> Implementación real respaldada por PostgreSQL + pgvector, migración SQL,
> dependencias del driver aisladas, y tests de integración (excluidos de
> `init.sh`). El módulo importa sin el driver instalado.

- [x] **B1 — `migrations.sql`.**
  Crear `src/wowrag/store/migrations.sql` con DDL idempotente parametrizada por
  `{table}` y `{dim}`: `CREATE EXTENSION IF NOT EXISTS vector`; tabla con
  `chunk_id TEXT PRIMARY KEY`, `text`, `source_url`, `title`, `section` (NOT
  NULL) y `embedding vector({dim}) NOT NULL`; índice HNSW
  `vector_cosine_ops`. Ver `design.md` §7.
  _(Cubre R15, R16, R17)_

- [x] **B2 — `PgVectorStore` con import lazy.**
  Crear `src/wowrag/store/pgvector_store.py` con `PgVectorStore`:
  - Constructor `__init__(self, dsn, dimension, table="chunks", metric="cosine")`.
  - Import de `psycopg` y `pgvector.psycopg.register_vector` **dentro del
    constructor** (no a nivel de módulo); si falla → `VectorStoreError` con
    mensaje de instalación (`requirements-pg.txt`).
  - Propiedad `dimension` sin tocar la DB.
  - `_connect()`: conecta; registra vector; fallo de conexión → `VectorStoreError`.
  - `ensure_schema()`: lee `migrations.sql`, `.format(table=, dim=)`, ejecuta y
    commitea (idempotente).
  - `upsert(chunks, embeddings)`: longitudes desemparejadas → `VectorStoreError`;
    `INSERT ... ON CONFLICT (chunk_id) DO UPDATE` con todos los campos +
    embedding (valores siempre por parámetros psycopg, nunca interpolados);
    devuelve N.
  - `similarity_search(query_vector, k) -> list[tuple[Chunk, float]]`: dim
    incorrecta → `VectorStoreError`; `SELECT chunk_id, text, source_url, title,
    section, 1 - (embedding <=> %s) AS score ... ORDER BY embedding <=> %s LIMIT
    k`; mapea cada fila a un par `(Chunk(...), score)` usando el `Chunk` existente.
  _(Cubre R12, R13, R14, R7, R8, R10, R16, R17, R18, R19, R25)_

- [x] **B3 — Crear `requirements-pg.txt`.**
  Crear `requirements-pg.txt` en la raíz con `psycopg[binary]>=3.2.0` y
  `pgvector>=0.3.0`, con comentario que lo identifique como dependencia manual
  excluida de `init.sh`. NO añadir estas dependencias a `requirements.txt` (el
  test `test_requirements_pinned.py` ya prohíbe `psycopg` ahí).
  _(Condición necesaria para R12, R13, R14; salvaguarda riesgo driver/Python 3.14)_

- [x] **B4 — `tests/test_store_pgvector.py`** (integración).
  Crear el fichero con `@pytest.mark.integration` en cada test. Se excluyen
  automáticamente por `init.sh`. Casos mínimos (requieren Postgres+pgvector):
  - `test_ensure_schema_creates_and_idempotent`: `ensure_schema()` crea esquema;
    segunda llamada no falla. _(R15, R17)_
  - `test_upsert_and_search_roundtrip`: upsert de chunks+vectores, luego
    `similarity_search` devuelve pares `(Chunk, float)` ordenados por coseno con
    metadata en el `Chunk`. _(R12, R10, R18)_
  - `test_upsert_replaces_existing_chunk_id`: upsert del mismo `chunk_id`
    reemplaza, no duplica. _(R8)_
  - `test_vector_column_uses_embedding_dim`: la columna es `vector(embedding_dim)`.
    _(R16)_
  - `test_bad_dsn_raises_vector_store_error`: DSN inválido / Postgres caído →
    `VectorStoreError`. _(R25)_

**Slice B — exit criteria:** `./init.sh` exit 0 (los tests de B4 son
`@pytest.mark.integration` y se omiten con `pytest -m "not integration"`);
`import wowrag.store.pgvector_store` y `from wowrag.store import PgVectorStore`
funcionan **sin el driver instalado**; instanciar `PgVectorStore` sin driver →
`VectorStoreError` (no `ImportError`); `requirements-pg.txt` existe y NO está
referenciado en `requirements.txt` ni en `init.sh`; `test_requirements_pinned.py`
sigue verde. Tras apilar B, los casos `test_pgvector_module_importable_without_driver`
(A5) y `test_pgvector_instantiation_raises_without_driver` (A6) quedan verdes.

---

## Slice C — indexing pipeline

> Pipeline de orquestación offline corpus → load → chunk → embed → upsert, en el
> módulo nuevo `index/`, testeado end-to-end solo con fakes (sin servicios reales).

- [x] **C1 — `IndexingPipeline` en módulo `index/`.**
  Crear `src/wowrag/index/pipeline.py` con `IndexingPipeline`:
  - Constructor recibe `loader: CorpusLoader`, `chunker: Chunker`,
    `embedder: EmbeddingProvider`, `store: VectorStore` (solo interfaces).
  - `index(corpus_dir) -> int`: llama `store.ensure_schema()` ANTES de upsert;
    carga documentos; chunkea cada uno; embebe `[c.text for c in chunks]`; hace
    `store.upsert(chunks, embeddings)`; devuelve el nº total de chunks (0 si no
    hay chunks).
  Crear `src/wowrag/index/__init__.py` re-exportando `IndexingPipeline`.
  _(Cubre R20, R21, R22, R23)_

- [x] **C2 — `tests/test_index_pipeline.py`** (end-to-end con fakes).
  - `test_index_ingests_corpus_end_to_end`: con `tmp_path` + un `*.jsonl` de
    prueba, `JsonlCorpusLoader` + `OverlapChunker` + `FakeEmbeddingProvider` +
    `FakeVectorStore`; `IndexingPipeline.index(tmp_path)` devuelve C = nº total
    de chunks, y el store contiene C entradas recuperables. _(R20, R22)_
  - `test_index_calls_ensure_schema_before_upsert`: usar un fake/spy de
    `VectorStore` que registre el orden de llamadas; `ensure_schema` ocurre antes
    del primer `upsert`. _(R21)_
  - `test_index_empty_corpus_returns_zero`: corpus sin documentos/chunks →
    `index` devuelve 0 y no falla. _(R22 borde)_
  - `test_pipeline_depends_only_on_interfaces`: construir `IndexingPipeline` con
    fakes/stubs que solo implementan los Protocols (sin clases concretas reales
    de DB/ML) y ejecutar `index`. _(R23)_

**Slice C — exit criteria:** `./init.sh` exit 0 con los tests de C2 en verde;
`from wowrag.index import IndexingPipeline` funciona; el pipeline corre
end-to-end solo con interfaces/fakes (sin Postgres ni GPU).

---

## Cierre (transversal a las 3 slices)

- [x] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con
  la suite `not integration` en verde (tests previos + A5–A7, C2). Los tests de
  B4 deben existir en disco y estar marcados `@pytest.mark.integration`; no
  tienen que pasar en `init.sh`. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R33) tienen al menos un test
    (unitario o de integración).
  - `from wowrag.store import VectorStore, VectorStoreError, FakeVectorStore,
    PgVectorStore` funciona sin el driver de Postgres instalado.
  - `from wowrag.index import IndexingPipeline` funciona.
  - `similarity_search` devuelve `list[tuple[Chunk, float]]` en fake y real; no
    queda ninguna referencia a `RetrievedChunk` en `src/` ni en tests.
  - `models.py` no fue modificado por f4.
  - `requirements-pg.txt` existe pero no está referenciado en `requirements.txt`
    ni en `init.sh`; `test_requirements_pinned.py` sigue verde.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json`. El cambio de estado y el cierre los hacen el leader /
> reviewer tras validar la trazabilidad `R<n>` ↔ test. Tu trabajo termina cuando
> todas las tasks `[x]` y `./init.sh` pasa en verde para cada slice.
