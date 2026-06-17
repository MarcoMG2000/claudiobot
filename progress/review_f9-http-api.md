# Review — feature f9-http-api

**Veredicto:** APPROVED

Revision del gate final de f9 (HTTP API FastAPI que expone f8). Todas las
afirmaciones del informe del implementer se verificaron contra el codigo y los
tests reales; no se confio en el informe.

## Resultado ./init.sh

- Exit code 0.
- 210 passed, 2 skipped, 5 deselected, 1 warning (coincide con lo esperado).
- Warning unico: StarletteDeprecationWarning (httpx vs httpx2) del TestClient. No
  bloqueante; el spec fija httpx>=0.27 y no menciona httpx2.

## Trazabilidad requirements <-> tests (todos EJECUTAN; ninguno skipped/deselected)

- R1: [x] test_create_app_returns_fastapi_with_routes (rutas via openapi paths).
- R2: [x] test_ask_happy_path_maps_answer (claves answer/sources/abstained/metadata).
- R3: [x] test_health_ok_without_orchestrator (200, status ok, spy fake.calls vacio).
- R4: [x] test_ask_calls_orchestrator_once_with_query (len 1, query del body) + happy.
- R5: [x] test_ask_happy_path_maps_answer (sources n/title/url, abstained false).
- R6: [x] test_ask_happy_path_maps_answer (metadata 1:1 model/persona/max_score/scores).
- R7: [x] test_ask_happy_path_maps_answer (igualdad estricta del dict, sin recalculo;
  response_model=Answer reutiliza el modelo de f8 sin schema espejo).
- R8: [x] test_ask_abstention_path (200, abstained true, mensaje de f8, sources vacio).
- R9: [x] test_ask_abstention_path (metadata presente en abstencion).
- R10: [x] test_ask_persona_explicit_forwarded (persona orc -> Persona(name=orc)).
- R11: [x] test_ask_persona_default_when_absent (sin persona -> persona is None).
- R12: [x] test_ask_unknown_persona_returns_400 (persona inexistente -> 400 JSON;
  orquestador nunca alcanzado).
- R13: [x] test_cors_headers_present (access-control-allow-origin presente).
- R14: [x] test_cors_origins_from_settings_not_hardcoded +
  test_config.py::test_cors_allow_origins_override_constructor +
  ::test_cors_allow_origins_override_from_env (origenes desde Settings, no hardcoded).
- R15: [x] test_ask_empty_or_missing_query_422 (param. espacios/vacio/sin query; fake.calls vacio).
- R16: [x] test_ask_orchestrator_error_400 (OrchestratorError -> 400 JSON).
- R17: [x] test_ask_infra_error_503 (Retriever/Embedding/VectorStore/LLMError -> 503).
- R18: [x] test_ask_infra_error_503, test_error_body_is_json_not_html,
  test_ask_unknown_persona_returns_400 (body JSON, sin HTML/traza/secreto).
- R19: [x] test_dependency_override_used_real_orchestrator_never_built (Depends Protocol).
- R20: [x] test_dependency_override_used_... + test_importing_api_does_not_pull_heavy_deps.
- R21: [x] toda test_api.py corre bajo pytest -m 'not integration' (21 tests, sin marca;
  verificado standalone: 21 passed, 0 network).
- R22: [x] handlers def en routes.py (health, ask); cubierto por el threadpool del
  TestClient. Decision documentada en design.
- R23: [x] test_required_dependencies_are_pinned (fastapi==0.137.1, uvicorn==0.49.0,
  httpx==0.28.1 pineados con ==).
- R24: [x] test_required_dependencies_are_pinned + test_deferred_dependencies_absent
  (fastapi/uvicorn/httpx en PINNED; torch/sentence-transformers/psycopg en DEFERRED).
- R25: [x] ./init.sh exit 0, suite 100% verde.

Conclusion: los 25 requirements (R1-R25) tienen al menos un test que EJECUTA
realmente bajo la suite por defecto. Ningun Rn queda sin cobertura.

## Tasks completas (T1-T21 + Z1)

Todas [x] en specs/f9-http-api/tasks.md y verificadas como genuinamente hechas:

- T1: [x] fastapi/uvicorn/httpx pineados en requirements.txt; httpx retirado de requirements-llm.txt.
- T2: [x] test_requirements_pinned.py PINNED += fastapi/uvicorn/httpx; DEFERRED = torch/sentence-transformers/psycopg.
- T3: [x] init.sh instalo deps; suite verde.
- T4: [x] 4 campos CORS en Settings (config.py 41-44), configurables por env.
- T5: [x] test_config.py defaults + 2 overrides (constructor/env).
- T6: [x] schemas.py AskRequest con field_validator que rechaza query vacia/espacios.
- T7: [x] sin AskResponse espejo; response_model=Answer (routes.py 59).
- T8: [x] dependencies.py: get_orchestrator (Protocol) + build_orchestrator con imports perezosos dentro de la funcion.
- T9: [x] GET /health (def, 200 status ok, sin orquestador).
- T10: [x] POST /ask (def, response_model=Answer, Depends, resolucion persona, answer una vez).
- T11: [x] Mapeo errores PersonaNotFound 400, Orchestrator 400, infra+catch-all 503, JSON, logger.exception, sin trazas.
- T12: [x] app.py create_app (FastAPI + CORSMiddleware desde Settings + router).
- T13: [x] api/__init__.py re-exporta create_app.
- T14: [x] tests/test_api.py: FakeOrchestrator, helper client_with, TestClient + overrides.
- T15-T21: [x] tests presentes y verdes (app/rutas, feliz, abstencion, persona, CORS, validacion/errores, DI).
- Z1: [x] init.sh exit 0; trazabilidad R1-R25; api/ sin SQL ni HTTP a Ollama.

## Checkpoints (CHECKPOINTS.md) -- relevantes a f9

- C1: [x] archivos base y 4 docs presentes; ./init.sh exit 0.
- C2: [x] una sola feature in_progress (f9); features done con tests verdes.
- C3: [x] src/wowrag/api/ es transporte puro (sin SQL ni HTTP a Ollama; impls reales
  detras de import perezoso en build_orchestrator); requirements pineado; sin print().
- C4: [x] un fichero de test por modulo; fakes via dependency_overrides; integracion
  marcada; pytest -m 'not integration' con 210 verdes.
- C5: [x] f9 no toca grounding; propaga abstencion de f8 1:1 y citas en camino feliz.
- C6: [x] specs/f9-http-api/ con requirements/design/tasks; EARS estricto; tasks [x];
  cada R1-R25 cubierto por test.

## Verificacion de limites de alcance (scope)

- Sin streaming/SSE: confirmado (no /ask/stream ni generate_stream en routes.py).
- Sin frontend real: confirmado (solo CORS configurable).
- Sin f10/f11/f12: confirmado (no eval harness, scraper ni reranker).
- f5-f8 sin tocar: confirmado; routes.py/dependencies.py solo IMPORTAN simbolos
  publicos (RagOrchestrator, OrchestratorError, errores base, Answer, Persona,
  load_persona); no se modifica logica de esas capas.
- No se redefine Answer/Source/AnswerMetadata: response_model=Answer reutiliza el
  modelo de f8 (solo AskRequest de transporte nuevo).

## Analisis del cambio de dependencias y desplazamiento de conteo

El cambio 187 passed + 3 skipped -> 210 passed + 2 skipped + 5 deselected es LEGITIMO:

1. Heavy deps siguen DEFERRED y el test sigue siendo significativo:
   test_requirements_pinned.py mantiene DEFERRED = torch/sentence-transformers/psycopg.
   test_deferred_dependencies_absent sigue afirmando que esas 3 NO estan en
   requirements.txt. Solo se promovieron fastapi/uvicorn/httpx de DEFERRED a PINNED.

2. Por que un skip paso a 5 deselected (no a passed, no a red):
   - Baseline: 3 skips = FlagEmbedding + psycopg + el MODULO test_llm_ollama.py, que
     hace pytest.importorskip('httpx') a nivel de modulo (sin httpx, modulo saltado).
   - Tras f9: httpx en requirements.txt -> el importorskip ya no salta el modulo; sus
     5 tests se COLECTAN. Los 5 son @pytest.mark.integration, asi que bajo
     -m 'not integration' se DESELECCIONAN (no se ejecutan). De ahi 5 deselected.
   - Verificado con pytest --collect-only -m integration: exactamente esos 5
     (test_generate_roundtrip, test_generate_stream_roundtrip,
     test_model_property_no_network, test_unreachable_server_raises,
     test_empty_prompt_no_request). La suite por defecto los EXCLUYE; no hay Ollama
     vivo en el camino de init.sh. No hacen llamadas de red reales.
   - Los 2 skips restantes = FlagEmbedding + psycopg (razones confirmadas: could not
     import FlagEmbedding / could not import psycopg).

3. Aritmetica: 187 -> 210 passed = +23 = 21 (test_api.py) + 2 (CORS en test_config.py).
   215 colectados - 5 deselected = 210 ejecutados (2 de ellos skipped). Cuadra exacto.

4. Ningun test debilitado/desactivado. Unico ajuste de assertion: R1 lee rutas desde
   app.openapi paths en vez de iterar app.routes (mas robusto entre versiones); mismo
   objetivo. test_api.py standalone: 21 passed, sin red.

## API contract (verificado)

- POST /ask con response_model=Answer mapea Answer de f8 a JSON: OK.
- GET /health: 200, sin orquestador: OK.
- Abstencion: abstained true + mensaje + sources vacio, con metadata: OK.
- Persona override por peticion Y fallback por config (None -> f8): ambos OK.
- Errores 422/400/503 con cuerpos JSON limpios, sin trazas (catch-all evita 500+HTML): OK.
- CORS desde Settings.cors_allow_origins (no hardcoded), campo nuevo con test: OK.
- DI: Depends(get_orchestrator), override en tests, cero DB/ML/Ollama/red en unit tests,
  import de wowrag.api no arrastra torch/psycopg (lazy build_orchestrator): OK.

## Cambios requeridos

Ninguno. La feature cumple el spec aprobado en su totalidad.

## Nota (no bloqueante)

StarletteDeprecationWarning (httpx -> httpx2) del TestClient. No afecta a ningun test.
El spec fija httpx>=0.27, no httpx2. Sin accion hoy.

