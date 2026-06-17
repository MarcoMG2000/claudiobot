# Implementación — f8-rag-orchestrator

- **Feature:** `f8-rag-orchestrator` — RAG orchestrator + abstención.
- **Estado:** implementación completa, esperando review. **NO** marcada `done`.
- **Entrega:** PR único (según `design.md` §0).
- **Verificación final `./init.sh`:** exit 0 — **187 passed + 3 skipped**
  (baseline previo: 166 passed + 3 skipped; +21 tests nuevos, 0 skips nuevos).
  Los 3 skips son los tests `@pytest.mark.integration` preexistentes (pgvector +
  bge_m3 + real-Ollama).

## Tasks completadas

- [x] **T1** — `AnswerMetadata` + `Answer` en `src/wowrag/models.py` + `__all__` +
  docstring del módulo actualizado.
- [x] **T2** — `OrchestratorError` + `RagOrchestrator` (Protocol) en
  `src/wowrag/rag/base.py`.
- [x] **T3** — `DefaultRagOrchestrator` en `src/wowrag/rag/orchestrator.py`
  (compone Retriever + PromptBuilder + LLMProvider por DI; constante
  `_ABSTENTION_MESSAGE`; short-circuit por `below_threshold`; flatten
  `f"{built.system}\n\n{built.user}"`; persona resuelta una sola vez).
- [x] **T4** — re-exports en `src/wowrag/rag/__init__.py` (reemplaza el placeholder).
- [x] **T5** — `tests/test_models_answer.py` (modelos).
- [x] **T6** — `tests/test_orchestrator.py` (orquestador: flujo feliz, abstención,
  errores, exports).
- [x] **Z1** — verificación final (`./init.sh` exit 0; trazabilidad R1–R27;
  `config.py` NO modificado; cero imports DB/ML/red en `rag/`).

## Archivos creados / editados

Editados:
- `src/wowrag/models.py` — añadidos `AnswerMetadata` y `Answer`; `__all__` y
  docstring actualizados. (No se tocó ningún modelo existente.)

Creados:
- `src/wowrag/rag/base.py` — `OrchestratorError` + `RagOrchestrator` (Protocol).
- `src/wowrag/rag/orchestrator.py` — `DefaultRagOrchestrator` + `_ABSTENTION_MESSAGE`.
- `src/wowrag/rag/__init__.py` — re-exports (sobrescribe el placeholder f0).
- `tests/test_models_answer.py` — tests de modelos.
- `tests/test_orchestrator.py` — tests del orquestador.

`config.py` **NO** fue modificado (confirmado con `git diff --stat`). `feature-list.json`,
`progress/current.md` y `progress/history.md` **NO** fueron tocados (territorio del leader).
f5/f6/f7 source y tests **NO** fueron tocados (solo se importan sus interfaces públicas).

## Trazabilidad R<n> → test

Cada requisito R1–R27 está cubierto por al menos un test concreto:

| R    | Requisito (resumen)                                          | Test(s) que lo cubren |
|------|-------------------------------------------------------------|-----------------------|
| R1   | `Answer` con answer/sources/abstained/metadata               | `test_models_answer.py::test_answer_fields` |
| R2   | answer == texto del LLM (sin recortar)                        | `test_orchestrator.py::test_happy_path_returns_answer_with_citations` |
| R3   | `Answer.sources` reutiliza `Source` de f6                    | `test_models_answer.py::test_answer_sources_are_source_type`; `test_orchestrator.py::test_happy_path_returns_answer_with_citations` |
| R4   | metadata incluye modelo LLM                                  | `test_models_answer.py::test_answer_metadata_fields`; `test_orchestrator.py::test_metadata_model_persona_scores` |
| R5   | metadata incluye persona usada                               | `test_models_answer.py::test_answer_metadata_fields`; `test_orchestrator.py::test_metadata_model_persona_scores`, `test_persona_explicit_reported` |
| R6   | metadata incluye `max_score`                                 | `test_models_answer.py::test_answer_metadata_fields`; `test_orchestrator.py::test_metadata_model_persona_scores` |
| R7   | metadata incluye scores por fuente                          | `test_models_answer.py::test_answer_metadata_fields`; `test_orchestrator.py::test_metadata_model_persona_scores` |
| R8   | Protocol `RagOrchestrator` con `answer(query, persona)`      | `test_orchestrator.py::test_exports_from_package`, `test_depends_only_on_interfaces` |
| R9   | depende solo de interfaces (fakeable, sin DB/ML/red)         | `test_orchestrator.py::test_depends_only_on_interfaces` |
| R10  | primero llama a `Retriever.retrieve(query)`                  | `test_orchestrator.py::test_happy_path_returns_answer_with_citations` (stub registra `retrieve_called`/`last_query`); `test_empty_query_raises` (no se llama si query vacía) |
| R11  | si no abstiene, llama a `PromptBuilder.build(...)`           | `test_orchestrator.py::test_happy_path_returns_answer_with_citations`, `test_persona_none_resolves_default` |
| R12  | compone system+user y llama a `generate` una vez             | `test_orchestrator.py::test_generate_called_once_with_combined_prompt` |
| R13  | construye `Answer(abstained=False, ...)`                     | `test_orchestrator.py::test_happy_path_returns_answer_with_citations` |
| R14  | `below_threshold=True` → abstiene sin build/generate         | `test_orchestrator.py::test_abstains_when_below_threshold`, `test_empty_store_abstains` |
| R15  | mensaje de abstención claro                                  | `test_orchestrator.py::test_abstains_when_below_threshold` (string exacto) |
| R16  | abstención → `sources == []`                                | `test_orchestrator.py::test_abstains_when_below_threshold`, `test_empty_store_abstains`; `test_models_answer.py::test_abstained_answer_empty_sources` |
| R17  | abstención → metadata con `max_score` y persona              | `test_orchestrator.py::test_abstention_metadata_present`, `test_empty_store_abstains` |
| R18  | mensaje propio de f8; no recalcula umbral (usa señal)        | `test_orchestrator.py::test_abstains_when_below_threshold` (consume `below_threshold` del stub, sin tocar `score_threshold`) |
| R19  | respuesta fundamentada → ≥1 `Source`                        | `test_orchestrator.py::test_happy_path_returns_answer_with_citations` |
| R20  | `sources` == `BuiltPrompt.sources` (mismo n/title/url)       | `test_orchestrator.py::test_happy_path_returns_answer_with_citations` (`answer.sources == built.sources`) |
| R21  | scores derivados de `RetrievalResult` (sin recalcular)       | `test_orchestrator.py::test_metadata_model_persona_scores` (`== [rc.score for rc in result.chunks]`) |
| R22  | tres deps por DI; sin instanciar red/DB/ML                  | `test_orchestrator.py::test_depends_only_on_interfaces` |
| R23  | `persona=None` → default de `Settings`, pasado a `build`     | `test_orchestrator.py::test_persona_none_resolves_default` |
| R24  | `OrchestratorError(Exception)` en `rag/base.py`             | `test_orchestrator.py::test_exports_from_package` (`issubclass(OrchestratorError, Exception)`); ejercitada por `test_empty_query_raises` |
| R25  | query vacía → `OrchestratorError` sin tocar deps            | `test_orchestrator.py::test_empty_query_raises` (parametrizado `""/spaces/\t/\n`) |
| R26  | errores de infra propagan tal cual                          | `test_orchestrator.py::test_infra_errors_propagate_retriever`, `test_infra_errors_propagate_llm` |
| R27  | re-exports desde `rag/__init__.py` y `models.py`            | `test_orchestrator.py::test_exports_from_package`; `test_models_answer.py::test_exports_models` |

## Notas de diseño / decisiones de implementación

- **Resolución de persona unificada (simplificación recomendada en design §5):**
  `effective_persona = persona or default_persona(self._settings)` se resuelve una
  sola vez tras validar la query, y se usa tanto en la metadata (`.name`) como en
  `PromptBuilder.build(...)`. Así el nombre reportado y la persona realmente usada
  coinciden (R5, R23), sin duplicar la lógica de default (`default_persona` de f0
  sigue siendo la única fuente de verdad). `PersonaNotFoundError` propaga (R26).
- **Señal, no recálculo (R18, R21):** f8 lee `result.below_threshold` (computado
  por f5) y deriva `scores`/`max_score` del `RetrievalResult`; nunca compara contra
  `Settings.score_threshold` ni re-embebe.
- **Flatten del prompt (R12, design §6):** `f"{built.system}\n\n{built.user}"`,
  un único string a `LLMProvider.generate` (f7 toma un string, no un par chat).
- **Abstención como respuesta válida, no excepción** (`docs/conventions.md`):
  modelada en `Answer.abstained`; f8 solo lanza por entrada inválida
  (`OrchestratorError`) o deja propagar infra.

## Fronteras respetadas

- f8 es librería pura: **sin** HTTP/FastAPI (f9), **sin** streaming/async (f9, usa
  solo `generate`), **sin** reranking (f12), **sin** scraping (f11).
- f5/f6/f7 consumidos solo por sus interfaces públicas
  (`wowrag.retrieval.base.Retriever`, `wowrag.generation.prompt_builder_base.PromptBuilder`,
  `wowrag.llm.base.LLMProvider`); su source y tests no fueron modificados.
- Cero imports de DB/ML/red en `src/wowrag/rag/`.

## Desviaciones del spec

Ninguna.
