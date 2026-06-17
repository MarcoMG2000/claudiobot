# Review — feature f8-rag-orchestrator

**Veredicto:** APPROVED

> Revision de cierre (gate final). Verificado contra el spec aprobado
> (specs/f8-rag-orchestrator: requirements/design/tasks, R1-R27, T1-T6 + Z1),
> el codigo real (src/wowrag/rag/, src/wowrag/models.py) y los tests f8.
> ./init.sh exit 0 = 187 passed + 3 skipped. Suite f8 (21 passed, 0 skipped).
> Todos los R<n> tienen al menos un test que CORRE (sin el gap tipo f7/R19).

## Trazabilidad requirements vs tests

| R   | Test concreto (ejecutado, no skipped) | Estado |
|-----|--------------------------------------|--------|
| R1  | test_models_answer::test_answer_fields (los 4 campos) | [x] |
| R2  | test_orchestrator::test_happy_path_returns_answer_with_citations (answer == texto del LLM sin recortar) | [x] |
| R3  | test_answer_sources_are_source_type + test_happy_path (isinstance Source) | [x] |
| R4  | test_answer_metadata_fields + test_metadata_model_persona_scores | [x] |
| R5  | test_metadata_model_persona_scores + test_persona_explicit_reported (persona == orc) | [x] |
| R6  | test_answer_metadata_fields + test_metadata_model_persona_scores (max_score == result.max_score == 0.95) | [x] |
| R7  | test_metadata_model_persona_scores (scores == [0.95, 0.72, 0.55]) | [x] |
| R8  | test_exports_from_package + test_depends_only_on_interfaces (firma answer(query, persona)) | [x] |
| R9  | test_depends_only_on_interfaces (stubs duck-typed, sin DB/ML/red) | [x] |
| R10 | test_happy_path (retrieve_called) + test_empty_query_raises (no se llama si vacia) | [x] |
| R11 | test_happy_path + test_persona_none_resolves_default (build_called) | [x] |
| R12 | test_generate_called_once_with_combined_prompt (len(prompts)==1; system + 2 newlines + user) | [x] |
| R13 | test_happy_path (abstained is False) | [x] |
| R14 | test_abstains_when_below_threshold + test_empty_store_abstains (spies: build/generate NO llamados) | [x] |
| R15 | test_abstains_when_below_threshold (string EXACTO, ver abajo) | [x] |
| R16 | test_abstains_when_below_threshold + test_empty_store_abstains + test_abstained_answer_empty_sources (sources == []) | [x] |
| R17 | test_abstention_metadata_present + test_empty_store_abstains (max_score, persona, model) | [x] |
| R18 | test_abstains_when_below_threshold (consume below_threshold; nunca compara score_threshold) | [x] |
| R19 | test_happy_path (len(answer.sources) >= 1) | [x] |
| R20 | test_happy_path (answer.sources == built.sources) | [x] |
| R21 | test_metadata_model_persona_scores (scores == [rc.score for rc in result.chunks]) | [x] |
| R22 | test_depends_only_on_interfaces (DI por constructor) | [x] |
| R23 | test_persona_none_resolves_default (persona default y received_persona.name) | [x] |
| R24 | test_exports_from_package (issubclass); ejercitada por test_empty_query_raises | [x] |
| R25 | test_empty_query_raises (parametrizado vacio/spaces/tab/newline; spies NO llamados) | [x] |
| R26 | test_infra_errors_propagate_retriever + test_infra_errors_propagate_llm | [x] |
| R27 | test_exports_from_package + test_models_answer::test_exports_models | [x] |

Sin gaps. Los 27 requirements tienen cobertura ejecutable. Contraste con la
regresion f7/R19 (requirement sin test que corre): aqui NO ocurre. Los 21 tests
se colectaron y pasaron (21 passed in 0.15s), ninguno marcado skip ni integration.

## Tasks completas

- T1: [x] AnswerMetadata + Answer en models.py (lineas 135-159); __all__ (13-22);
  docstring del modulo actualizado (1-7, nombra f8). Ningun modelo previo tocado.
- T2: [x] OrchestratorError + RagOrchestrator Protocol en rag/base.py (18-53),
  from __future__ import annotations, firma answer(query, persona=None) -> Answer.
- T3: [x] DefaultRagOrchestrator en rag/orchestrator.py (28-128): DI por
  constructor, _ABSTENTION_MESSAGE (23-25), short-circuit por below_threshold (96),
  flatten system + 2 newlines + user (114), persona resuelta una vez (84-87).
- T4: [x] re-exports en rag/__init__.py (10-13), sobreescribe el placeholder.
- T5: [x] tests/test_models_answer.py (5 tests, todos verdes).
- T6: [x] tests/test_orchestrator.py (16 tests, todos verdes).
- Z1: [x] ./init.sh exit 0 (187 passed + 3 skipped); R1-R27 con test; config.py NO
  modificado (git diff --stat no lo incluye); cero imports DB/ML/red en rag/ (grep);
  short-circuit verificado por spy.

Ninguna task en [ ]. Sin desviaciones del spec.

## Abstencion (nucleo de f8) - verificacion detallada

- Consume la senal de f5, no recalcula umbral: orchestrator.py:96
  if result.below_threshold:. El codigo nunca lee ni compara Settings.score_threshold
  (grep confirma). R18/R21 OK.
- Short-circuit ANTES de PromptBuilder/LLM: el return de abstencion (97-107) precede
  a prompt_builder.build (111) y llm.generate (115). test_abstains_when_below_threshold
  afirma not build_called y prompts == []. R14 OK.
- Abstencion devuelta como Answer(abstained=True, ...), NUNCA lanzada: no hay raise
  por abstencion; solo OrchestratorError por query vacia (79) y propagacion de infra. OK.
- Mensaje EXACTO (comparacion de string): las tres fuentes coinciden byte a byte
  (requirements.md R15; orchestrator.py:23-25 _ABSTENTION_MESSAGE; test_orchestrator.py:249-251):
  No hay evidencia suficiente en los documentos para responder con seguridad. R15 OK.

## Citas siempre presentes (principio 3)

- No-abstenida: answer.sources == built.sources y len(sources) >= 1
  (test_happy_path_returns_answer_with_citations). Devueltas tal cual de f6 (mismo
  n/title/url), sin reordenar (R19, R20). OK.
- Abstenida: sources == [] (R16) en test_abstains_when_below_threshold,
  test_empty_store_abstains y test_abstained_answer_empty_sources; metadata sigue
  poblada con max_score + persona + model (R17). OK.

## Fronteras de alcance

- Sin HTTP API / FastAPI: grep en rag/ no encuentra fastapi/requests/httpx. OK (f9).
- Sin streaming/async: no hay generate_stream/async/await en rag/; solo
  LLMProvider.generate (sincrono). OK (f9).
- Sin reranking/scraping: no hay rerank ni scraping. OK (f12/f11).
- f5/f6/f7 source + tests intactos: git diff --stat HEAD muestra solo models.py,
  rag/__init__.py, generation/__init__.py, retrieval/__init__.py, tests/test_config.py;
  los modulos f5/f6/f7 son untracked sin cambios. f8 importa solo interfaces publicas
  (retrieval.base.Retriever, generation.prompt_builder_base.PromptBuilder, llm.base.LLMProvider). OK.
- config.py NO modificado: no aparece en git diff --stat. f8 reutiliza Settings +
  default_persona (f0) sin tocarlos. OK.

## Unit-testability

- DI por constructor (__init__(retriever, prompt_builder, llm, settings=None)).
- Tests usan stubs/spies (_StubRetriever, _SpyPromptBuilder, _SpyLLM) y
  FakeEmbeddingProvider/FakeVectorStore/FakeLLMProvider.
- Cero imports de DB/ML/red en rag/ (grep) y en los tests f8. R9/R22 OK.

## Checkpoints

- C1: [x] arnes completo; ./init.sh exit 0 (187 passed + 3 skipped).
- C2: [x] una sola feature in_progress (f8-rag-orchestrator); las done con tests verdes.
- C3: [x] rag/ respeta la capa de orquestacion de architecture.md seccion 6;
  servicios tras interfaz; sin SQL/HTTP en rag/; sin print/secretos/TODOs.
- C4: [x] un fichero de test por modulo; logica con fakes; pytest -m not-integration > 0 tests, todos verdes.
- C5: [x] abstencion por debajo del umbral testeada; no-abstenidas con citas (URLs);
  prompt = solo contexto recuperado (f6, via spy en test_generate_called_once).
- C6: [x] specs/f8-rag-orchestrator/ con los 3 docs; EARS estricto; todas las tasks
  [x]; cada R<n> con test.

## Cambios requeridos

Ninguno. La feature cumple el spec, la trazabilidad es completa y ejecutable,
./init.sh esta en verde y las fronteras de alcance se respetan. APPROVED.
