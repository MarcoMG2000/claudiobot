# Impl report — f4 Slice C (indexing pipeline)

> Nota: el subagente implementer murió por "Stream idle timeout" justo tras
> escribir el código y los tests (42 tool uses) pero antes de generar este
> informe. El leader lo reconstruyó a partir del estado en disco verificado:
> `./init.sh` exit 0, 105 passed, 2 skipped.

## Archivos creados
- `src/wowrag/index/__init__.py` — re-exporta `IndexingPipeline` (R20).
- `src/wowrag/index/pipeline.py` — `IndexingPipeline` (DI por interfaces
  `CorpusLoader`/`Chunker`/`EmbeddingProvider`/`VectorStore`; flujo
  corpus→load→chunk→embed→upsert; `ensure_schema` antes de `upsert`;
  edge de corpus vacío → 0).
- `tests/test_index_pipeline.py` — 4 tests unitarios end-to-end (solo fakes/stubs,
  sin DB, sin torch, sin `@pytest.mark.integration`).

## Trazabilidad R↔test (Slice C)
| R | Test | 
|---|------|
| R20 (flujo corpus→load→chunk→embed→upsert, store poblado y consultable) | `test_index_ingests_corpus_end_to_end` |
| R21 (`ensure_schema` antes de `upsert`; `index` devuelve el conteo) | `test_index_calls_ensure_schema_before_upsert` (spy de orden) |
| R22 (M docs → C chunks → C upserts; edge corpus vacío → 0) | `test_index_ingests_corpus_end_to_end`, `test_index_empty_corpus_returns_zero` |
| R23 (depende solo de interfaces) | `test_pipeline_depends_only_on_interfaces` (stubs Protocol puros) |

## Checklist
- [x] C1 — `IndexingPipeline` en módulo `index/`.
- [x] C2 — `tests/test_index_pipeline.py` end-to-end con fakes.
- [x] Z1 — Verificación final.

## Verificación final
- `./init.sh` → exit 0, **105 passed, 2 skipped** (101 previos + 4 nuevos de C2).
- 2 skipped = ficheros de integración `test_store_pgvector.py` + `test_embeddings_bge_m3.py` (sin driver/sin FlagEmbedding).
- `from wowrag.index import IndexingPipeline` funciona.
- Sin cambios en `store/`, `embeddings/`, `ingest/`, `models.py`, `config.py`.
- `feature-list.json` NO marcado `done` (pendiente de review final del leader/reviewer).

## Desviaciones
- Informe reconstruido por el leader (ver nota superior). Código y tests intactos
  tal como los dejó el implementer; verificados verdes.
