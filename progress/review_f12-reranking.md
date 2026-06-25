# Review — feature f12-reranking

**Veredicto:** APPROVED

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `test_exports_reranker_from_retrieval_package` (importa el Protocol desde `wowrag.retrieval`)
- R2: [x] cubierto por `test_passthrough_preserves_order`, `test_fake_reverses_order`, `test_fake_no_ml_imports`
- R3: [x] cubierto por `test_rerank_result_fields`
- R4: [x] cubierto por `test_fake_truncates_to_top_n`
- R5: [x] cubierto por `test_passthrough_top_n_exceeds_chunks`
- R6: [x] cubierto por `test_passthrough_preserves_order`
- R7: [x] cubierto por `test_passthrough_reranker_model_is_none`
- R8: [x] cubierto por `test_passthrough_truncates_to_top_n`
- R9: [x] cubierto por `test_cross_encoder_reranks_correctly` (@integration)
- R10: [x] cubierto por `test_cross_encoder_reranks_correctly` (@integration)
- R11: [x] cubierto por `test_cross_encoder_reranks_correctly` (@integration, model not loaded until rerank()) — también verificable por code review: `self._model = None` en `__init__`, import dentro de `_get_model`
- R12: [x] cubierto por `test_cross_encoder_reranks_correctly` (@integration)
- R13: [x] cubierto por `test_fake_reverses_order`, `test_fake_truncates_to_top_n`
- R14: [x] cubierto por `test_fake_no_ml_imports`
- R15: [x] cubierto por `test_fake_reranker_model_is_fake`
- R16: [x] cubierto por `test_orchestrator_without_reranker_unchanged` (Settings con `reranker_enabled` default=False, verificado en construcción del orquestador sin reranker)
- R17: [x] cubierto por `test_cross_encoder_reranks_correctly` (@integration, usa el modelo default)
- R18: [x] cubierto por `test_orchestrator_reranker_top_n_passed` (`reranker_top_n=2` propagado correctamente)
- R19: [x] cubierto por `test_orchestrator_without_reranker_unchanged`
- R20: [x] cubierto por `test_orchestrator_with_fake_reranker_uses_reranked_order`, `test_orchestrator_reranker_top_n_passed`
- R21: [x] cubierto por `test_orchestrator_reranker_not_called_on_abstention`
- R22: [x] cubierto por `test_orchestrator_without_reranker_unchanged`
- R23: [x] cubierto por `test_orchestrator_answer_contract_unchanged`
- R24: [x] todos los tests unitarios de `tests/test_reranker.py` corren bajo `not integration`; `./init.sh` termina verde
- R25: [x] cubierto por `test_cross_encoder_reranks_correctly` decorado con `@pytest.mark.integration`
- R26: [x] cubierto por `test_passthrough_empty_chunks`, `test_fake_empty_chunks`
- R27: [x] verificado por revisión de código: `CrossEncoderReranker.rerank` no envuelve `model.predict` en ningún bloque try/except (línea 116 de `reranker.py`); no existe test unitario dedicado (imposible sin la librería ML), pero el código no enmascara la excepción
- R28: [x] cubierto por `test_exports_reranker_from_retrieval_package`, `test_exports_rerank_result_from_models`

## Tasks completas

- T1: [x] `RerankResult` añadido a `models.py` con los tres campos y en `__all__`
- T2: [x] `reranker.py` creado con `Reranker` Protocol, `PassthroughReranker`, `CrossEncoderReranker`, `FakeCrossEncoderReranker`
- T3: [x] `retrieval/__init__.py` re-exporta las cuatro clases y las añade a `__all__`
- T4: [x] `config.py` tiene los tres campos con defaults exactos del spec
- T5: [x] `orchestrator.py` tiene el parámetro `reranker: Reranker | None = None` y la rama condicional correcta en `answer()`
- T6: [x] 18 tests unitarios en `tests/test_reranker.py`, sin ML/Postgres/red
- T7: [x] `test_cross_encoder_reranks_correctly` con `@pytest.mark.integration`
- Z1: [x] `./init.sh` termina exit 0; `315 passed, 2 skipped, 7 deselected`
- Z2: [ ] pendiente — el implementer no marca `done` en `feature-list.json` hasta que el reviewer apruebe (justificado explícitamente en `tasks.md`)

## Checkpoints

- C1: [x] `AGENTS.md`, `init.sh`, `feature-list.json`, `progress/current.md` presentes; 4 docs presentes; `./init.sh` exit 0
- C2: [x] solo `f12-reranking` en `in_progress`; todas las features `done` tienen tests; `progress/current.md` describe la sesión activa
- C3: [x] `reranker.py` vive en `retrieval/` (capa correcta); `orchestrator.py` solo importa interfaces; sin SQL ni HTTP fuera de su capa; sin `print()` de debug; sin secretos
- C4: [x] `tests/test_reranker.py` cubre el módulo nuevo; lógica testeada con fakes/stubs; `pytest -m "not integration"` verde
- C5: [x] abstención con reranker activo verificada por `test_orchestrator_reranker_not_called_on_abstention`; citas presentes en `Answer.sources`; prompt sin mezcla de scores
- C6: [x] `specs/f12-reranking/` tiene `requirements.md`, `design.md`, `tasks.md`; EARS estricto; todas las tasks relevantes `[x]` (Z2 pendiente por diseño)

## Notas sobre criterios específicos

**R27 (errores ML propagan):** no existe test unitario dedicado porque sin `sentence-transformers` instalado no es posible provocar una excepción de `model.predict`. El código no tiene ningún try/except alrededor de `model.predict(pairs)` (línea 116, `reranker.py`), lo que cumple el requisito. El test `@integration` podría extenderse en el futuro para verificar propagación con un mock del CrossEncoder, pero el spec solo requiere un test de integración con modelo real (R25), no un test de propagación de errores.

**Retrocompatibilidad f8 (R19):** `tests/test_orchestrator.py` no fue modificado y pasa sin cambios (`315 passed` incluye los tests de f8). El parámetro `reranker=None` es el último en el constructor, con valor por defecto, lo que garantiza que ningún código existente necesita actualizarse.

**R11 — lazy load verificable por código:** `_model = None` en `__init__`; `from sentence_transformers import CrossEncoder` dentro de `_get_model()`, que solo se llama desde `rerank()` tras verificar `if not chunks`. El módulo puede importarse sin `sentence-transformers` instalado.
