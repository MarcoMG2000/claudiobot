# Bitácora histórica (append-only)

> Cada vez que se cierra una sesión, su resumen se añade aquí.
> No edites entradas anteriores. Solo añades al final.

---

## f0-project-skeleton — Project skeleton & configuration system

- **Fecha de cierre:** 2026-06-03
- **Estado final:** `done`
- **Tasks cubiertas:** T1–T13 (todas marcadas `[x]` en `specs/f0-project-skeleton/tasks.md`).
  Esqueleto de subpaquetes, Settings (pydantic-settings), Persona + loader,
  YAMLs simple/orc/troll, default_persona + exports, requirements.txt pineado,
  .gitignore/.env.example, suites de tests (T8–T12) y verificación final (T13).
- **Trazabilidad:** R1–R14 verificadas, cada requirement cubierto por al menos
  un test concreto (ver `progress/review_f0-project-skeleton.md` para el mapa
  R<n> → test).
- **Tests:** 26 passed, `./init.sh` exit 0 (pytest verde, Python 3.14.4).
- **Veredicto del reviewer:** APROBADO, sin cambios requeridos
  (`progress/review_f0-project-skeleton.md`).

---

## f3-embeddings-provider — Embeddings provider (abstraction + bge-m3)

- **Fecha de cierre:** 2026-06-15
- **Estado final:** `done`
- **Flujo:** spec aprobado por humano → `implementer` → `reviewer`
  CHANGES_REQUESTED (R10: los nuevos campos de `Settings`
  `embedding_batch_size`/`embedding_device` no tenían cobertura de tests) →
  `implementer` corrigió (añadió
  `test_embedding_batch_size_and_device_overridable_from_env` y extendió
  `EXPECTED_DEFAULTS`) → `reviewer` APROBADO.
- **Construido:** `EmbeddingProvider` (Protocol) + `EmbeddingError`
  (`src/wowrag/embeddings/base.py`), `FakeEmbeddingProvider` solo-stdlib
  (`fake.py`), `BgeM3Embeddings` con import perezoso de FlagEmbedding
  (`bge_m3.py`), re-exports del paquete (`__init__.py`), 2 nuevos campos de
  `Settings` (`config.py`), `requirements-ml.txt` (deps de ML aisladas de
  init.sh).
- **Tests:** `./init.sh` exit 0, 86 passed + 1 skipped (el fichero de
  integración de bge_m3 está marcado `@pytest.mark.integration`, se omite sin
  FlagEmbedding).
- **Reports:** `progress/impl_f3-embeddings-provider.md`,
  `progress/review_f3-embeddings-provider.md`.

---

## f4-vector-store-pgvector — Vector store (abstraction + pgvector) and indexing

- **Fecha de cierre:** 2026-06-16
- **Estado final:** `done`
- **Entrega:** 3 slices apilados (el humano eligió PRs encadenados):
  - **Slice A** (commit `1d84d2c`): `VectorStore` (Protocol) + `VectorStoreError`
    (`src/wowrag/store/base.py`), `FakeVectorStore` en memoria con coseno
    solo-stdlib (`fake.py`), re-exports del paquete (`__init__.py`),
    `Settings.vector_table`/`distance_metric` con tests de default y
    override por env. Reviewer APROBADO.
  - **Slice B** (commit `cbf9ac1`): `PgVectorStore` con import perezoso de
    psycopg/pgvector (`pgvector_store.py`), `migrations.sql` idempotente,
    `requirements-pg.txt` (driver aislado de init.sh), tests de integración
    `@pytest.mark.integration`, tests unitarios R13/R14 de aislamiento de
    import. Reviewer APROBADO.
  - **Slice C** (este commit): `IndexingPipeline` en nuevo módulo `index/`
    (`pipeline.py`, corpus→load→chunk→embed→upsert, DI vía Protocols),
    4 tests unitarios end-to-end con fakes. Reviewer APROBADO (puerta final
    de toda la feature).
- **Decisiones de diseño en la puerta de aprobación:** `RetrievedChunk`
  diferido a f5 → `similarity_search` devuelve `list[tuple[Chunk, float]]`;
  nuevo módulo `index/` para indexado offline (separado del path de consulta
  online `rag/`).
- **Trazabilidad:** R1–R33 cubiertos por ≥1 test entre los slices A+B+C.
- **Tests:** `./init.sh` exit 0, 105 passed + 2 skipped (ficheros de
  integración pgvector + bge_m3, sin driver / sin FlagEmbedding).
- **Nota:** el subagente `implementer` de Slice C murió (stream timeout) tras
  escribir código+tests pero antes de su report; el leader reconstruyó
  `progress/impl_f4-slice-c.md` desde el estado verificado en disco. El
  reviewer verificó el código directamente.
- **Reports:** `progress/impl_f4-slice-{a,b,c}.md`,
  `progress/review_f4-slice-{a,b,c}.md`.

---