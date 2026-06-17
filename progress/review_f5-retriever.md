# Review — feature f5-retriever

**Veredicto:** APPROVED

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `test_models_retrieval.py::test_retrievedchunk_wraps_chunk_and_score`
- R2: [x] cubierto por `test_retrievedchunk_exposes_citation_metadata` + `test_retrievedchunk_properties_are_readonly`
- R3: [x] cubierto por `test_retrievedchunk_preserves_score` (itera 4 valores incl. 0.0, negativo, fraccionario, 1.0)
- R4: [x] cubierto por `test_retrievalresult_fields` + `test_retrievalresult_empty_chunks`
- R5: [x] cubierto por `test_max_score_equals_best_chunk_score`
- R6: [x] cubierto por `test_retriever.py::test_below_threshold_true_when_max_score_low`
- R7: [x] cubierto por `test_below_threshold_false_when_max_score_high` + `test_below_threshold_equal_does_not_abstain` (boundary == no abstiene, strict <)
- R8: [x] cubierto por `test_exports_from_package` — verifica importación del Protocol, `hasattr(DefaultRetriever, "retrieve")`, y el contrato de tipos
- R9: [x] cubierto por `test_retriever_depends_only_on_interfaces` — `DefaultRetriever` construido con `_SpyEmbedder`/`_SpyStore` duck-type only
- R10: [x] cubierto por `test_empty_query_raises` (parametrizado: `""`, `"   "`, `"\t"`, `"\n"`); spy confirma que embed/store NO son llamados
- R11: [x] cubierto por `test_embeds_query_as_single_vector` — `_RecordingEmbedder` verifica `len(last_texts)==1`
- R12: [x] cubierto por `test_wraps_pairs_into_retrieved_chunks`
- R13: [x] cubierto por `test_wraps_pairs_into_retrieved_chunks` — assert `scores == sorted(scores, reverse=True)`
- R14: [x] cubierto por `test_respects_k_limit` — 5 chunks en store, `retrieve(q, k=2)` devuelve `<=2`
- R15: [x] cubierto por `test_result_chunks_carry_metadata` (models) + `test_results_carry_metadata` (retriever)
- R16: [x] cubierto por `test_k_none_uses_top_k` — 6 chunks, `top_k=3`, sin k explícito → `<=3`
- R17: [x] cubierto por `test_explicit_k_overrides_top_k` — `top_k=10`, `k=2` explícito → `<=2`
- R18: [x] cubierto por `test_non_positive_k_raises` (parametrizado: 0, -1, -100); spy confirma store NO llamado
- R19: [x] cubierto por `test_below_threshold_true_when_max_score_low` (usa `score_threshold=0.9999`) + `test_config.py::test_score_threshold_overridable_from_env`
- R20: [x] cubierto por `test_empty_store_signals_abstention` — `chunks==[]`, `max_score==0.0`, `below_threshold is True`, sin excepción
- R21: [x] cubierto por `test_exports_from_package` — `issubclass(RetrieverError, Exception)`
- R22: [x] cubierto por `test_infra_errors_propagate_embedder` + `test_infra_errors_propagate_store` — fakes que lanzan `EmbeddingError`/`VectorStoreError`
- R23: [x] cubierto por `test_exports_from_package` — importaciones del paquete verificadas; módulo-level imports en todos los test files

## Tasks completas

- T1: [x]
- T2: [x]
- T3: [x]
- T4: [x]
- T5: [x]
- T6: [x]
- T7: [x]
- Z1: [x]

## Checkpoints

- C1: [x] `init.sh` termina exit 0 — 135 passed, 2 skipped
- C2: [x] Solo f5-retriever en `in_progress`; features `done` tienen tests verdes; coherencia de estado confirmada
- C3: [x] Separación de capas respetada: `retrieval/` solo importa `wowrag.*` interfaces (embeddings/base, store/base, models, config); cero imports DB/ML/red; `retriever.py` no está en `rag/`
- C4: [x] Tests con fakes (FakeEmbeddingProvider + FakeVectorStore); sin Postgres/GPU/red; 135 passed; los 2 skipped son integration pre-existentes
- C5: [x] Señal de abstención (`below_threshold`) computada y testeada; f5 no produce el mensaje (frontera f6/f7/f8 respetada)
- C6: [x] `specs/f5-retriever/` tiene `requirements.md`, `design.md`, `tasks.md`; todos los R1–R23 cubiertos; todas las tasks `[x]`

## Notas de revisión

1. **Scope boundary**: Confirmado. `DefaultRetriever.retrieve` devuelve `RetrievalResult` con `below_threshold: bool`. No hay mensaje de abstención, no hay construcción de prompt, no hay llamada a LLM. La frontera con f6/f7/f8 está limpia.

2. **`config.py` no modificado**: Confirmado. El implementador solo reutilizó `top_k` y `score_threshold`. El test `test_score_threshold_overridable_from_env` cierra el hueco de env-override identificado en `design.md §6`.

3. **Semántica `<` estricto (R7)**: `test_below_threshold_equal_does_not_abstain` en `retriever.py:87` usa `max_score < threshold` (estricto), y el test verifica el caso límite `score==1.0`, `threshold==1.0` → `below_threshold is False`. Correcto.

4. **R5 no es un invariante del modelo**: `RetrievalResult` es un `BaseModel` pydantic sin validador que fuerce `max_score == chunks[0].score`. Esto es correcto por diseño (el invariante lo garantiza `DefaultRetriever`, no el modelo), y el test de modelos lo verifica construyendo el resultado con el valor correcto. No es un defecto.

5. **R8 (Protocol)**: El test no hace `isinstance(DefaultRetriever(...), Retriever)` estructuralmente, pero el import-level test + `hasattr(DefaultRetriever, "retrieve")` es suficiente cobertura para el requisito "definir la interfaz como punto de intercambio". El uso real del Protocol se prueba implícitamente en todos los tests de `DefaultRetriever`.
