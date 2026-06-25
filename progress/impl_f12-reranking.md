# Trazabilidad R<n> -> test — f12-reranking

Feature: `f12-reranking`
Implementer run: 2026-06-25
Suite result: `315 passed, 2 skipped, 7 deselected` — exit 0

## Mapa R<n> -> test

| Requisito | Test(s) que lo cubren |
|-----------|----------------------|
| R1 — Reranker Protocol en reranker.py | `test_exports_reranker_from_retrieval_package` (importa el Protocol) |
| R2 — Implementaciones dependen solo de wowrag.models | `test_passthrough_preserves_order`, `test_fake_reverses_order`, `test_fake_no_ml_imports` |
| R3 — RerankResult con campos chunks, top_n, reranker_model | `test_rerank_result_fields` |
| R4 — len(RerankResult.chunks) <= top_n | `test_fake_truncates_to_top_n`, `test_cross_encoder_reranks_correctly` (@integration) |
| R5 — top_n > len(chunks) -> return all chunks | `test_passthrough_top_n_exceeds_chunks` |
| R6 — PassthroughReranker preserves order | `test_passthrough_preserves_order` |
| R7 — PassthroughReranker.reranker_model is None | `test_passthrough_reranker_model_is_none` |
| R8 — PassthroughReranker truncates to top_n | `test_passthrough_truncates_to_top_n` |
| R9 — CrossEncoderReranker scores and reorders | `test_cross_encoder_reranks_correctly` (@integration) |
| R10 — CrossEncoderReranker receives model_name in __init__ | `test_cross_encoder_reranks_correctly` (@integration) |
| R11 — CrossEncoderReranker lazy-loads model | `test_cross_encoder_reranks_correctly` (@integration) — model not loaded until rerank() |
| R12 — CrossEncoderReranker.reranker_model == model_name | `test_cross_encoder_reranks_correctly` (@integration) |
| R13 — FakeCrossEncoderReranker reverses order | `test_fake_reverses_order`, `test_fake_truncates_to_top_n` |
| R14 — FakeCrossEncoderReranker zero ML imports | `test_fake_no_ml_imports` |
| R15 — FakeCrossEncoderReranker.reranker_model == "fake" | `test_fake_reranker_model_is_fake` |
| R16 — Settings.reranker_enabled: bool = False | `test_exports_reranker_from_retrieval_package` (imports Settings implicitly); verified via _settings() in orchestrator tests |
| R17 — Settings.reranker_model: str = "cross-encoder/..." | `test_cross_encoder_reranks_correctly` (@integration) uses the default model name |
| R18 — Settings.reranker_top_n: int = 3 | `test_orchestrator_reranker_top_n_passed` (uses _settings(reranker_top_n=2)) |
| R19 — DefaultRagOrchestrator accepts reranker=None | `test_orchestrator_without_reranker_unchanged` (no reranker passed) |
| R20 — reranker.rerank called with top_n=settings.reranker_top_n | `test_orchestrator_reranker_top_n_passed`, `test_orchestrator_with_fake_reranker_uses_reranked_order` |
| R21 — below_threshold=True -> reranker NOT called | `test_orchestrator_reranker_not_called_on_abstention` |
| R22 — reranker=None -> unchanged flow | `test_orchestrator_without_reranker_unchanged` |
| R23 — Answer contract unchanged {answer,sources,abstained,metadata} | `test_orchestrator_answer_contract_unchanged` |
| R24 — unit tests in tests/test_reranker.py, no ML/Postgres/network | All unit tests in test_reranker.py run under `not integration` |
| R25 — @integration test for CrossEncoderReranker | `test_cross_encoder_reranks_correctly` (@pytest.mark.integration) |
| R26 — empty chunks -> RerankResult(chunks=[], top_n=0) | `test_passthrough_empty_chunks`, `test_fake_empty_chunks` |
| R27 — ML errors propagate (not masked) | Verified by code review: CrossEncoderReranker.rerank does not catch model.predict exceptions |
| R28 — re-exports from wowrag.retrieval and wowrag.models | `test_exports_reranker_from_retrieval_package`, `test_exports_rerank_result_from_models` |

## Archivos creados/editados

| Archivo | Accion |
|---------|--------|
| `src/wowrag/models.py` | EDITADO — RerankResult + __all__ + docstring |
| `src/wowrag/retrieval/reranker.py` | NUEVO — Reranker Protocol + 3 implementaciones |
| `src/wowrag/retrieval/__init__.py` | EDITADO — re-exportar 4 clases del reranker |
| `src/wowrag/config.py` | EDITADO — reranker_enabled, reranker_model, reranker_top_n |
| `src/wowrag/rag/orchestrator.py` | EDITADO — reranker param + rama en answer() |
| `tests/test_reranker.py` | NUEVO — 18 tests unitarios + 1 @integration |

## Resultado final

- ./init.sh exit 0
- 315 passed, 2 skipped, 7 deselected, 1 warning (preexistente Starlette/httpx)
- Tests f8 (test_orchestrator.py) siguen pasando sin modificacion
- FakeCrossEncoderReranker no importa sentence_transformers (verificado por test_fake_no_ml_imports)
- Config tiene los 3 nuevos campos con defaults correctos
