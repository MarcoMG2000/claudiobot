# Implementación — f9-http-api

- **Feature:** `f9-http-api` — HTTP API (FastAPI) que expone f8 sobre HTTP.
- **Estado:** implementación completa; esperando review (NO marcada `done`).
- **Entrega:** PR único (~360 líneas previstas en design §0).
- **Agente:** implementer

## Plan ejecutado

Tasks T1..T21 + Z1 de `specs/f9-http-api/tasks.md`, en orden. Todas marcadas `[x]`.

## Tasks completadas

| Task | Qué | Estado |
|------|-----|--------|
| T1 | `fastapi==0.137.1`, `uvicorn==0.49.0`, `httpx==0.28.1` pineados en `requirements.txt`; `httpx` retirado de `requirements-llm.txt` | [x] |
| T2 | `test_requirements_pinned.py`: fastapi/uvicorn/httpx movidos de `DEFERRED` a `PINNED`; torch/sentence-transformers/psycopg siguen `DEFERRED` | [x] |
| T3 | `./init.sh` instaló las nuevas deps; suite previa verde antes de añadir código f9 | [x] |
| T4 | `Settings`: `cors_allow_origins=["*"]`, `cors_allow_credentials=False`, `cors_allow_methods=["*"]`, `cors_allow_headers=["*"]`; formato JSON env documentado en `.env.example` | [x] |
| T5 | `test_config.py`: defaults CORS + override por constructor + override por env (JSON) | [x] |
| T6 | `api/schemas.py` con `AskRequest{query, persona?}` + `field_validator` que rechaza query vacía/espacios (→422) | [x] |
| T7 | Respuesta reutiliza `Answer` de f8 (`response_model=Answer`); sin schema espejo | [x] |
| T8 | `api/dependencies.py`: `get_orchestrator()` (tipado al Protocol) + `build_orchestrator()` con imports perezosos | [x] |
| T9 | `api/routes.py`: `GET /health` (`def`, 200 `{"status":"ok"}`, sin orquestador) | [x] |
| T10 | `POST /ask` (`def`, `response_model=Answer`), `Depends(get_orchestrator)`, resolución persona, `answer()` exactamente una vez | [x] |
| T11 | Mapeo errores: PersonaNotFoundError→400, OrchestratorError→400, infra (Retriever/Embedding/VectorStore/LLM + catch-all)→503, JSON, `logger.exception`, sin trazas | [x] |
| T12 | `api/app.py`: `create_app()` (FastAPI + CORSMiddleware desde Settings + router) | [x] |
| T13 | `api/__init__.py`: re-exporta `create_app` (placeholder reemplazado) | [x] |
| T14 | `tests/test_api.py`: `FakeOrchestrator`, helper `client_with()`, `TestClient` + `dependency_overrides` | [x] |
| T15 | Tests app/rutas: `create_app` con `/ask` + `/health`; `/health` sin orquestador (spy) | [x] |
| T16 | Tests camino feliz: mapeo answer/sources/abstained/metadata; `answer` una vez con la query | [x] |
| T17 | Tests abstención: 200, `abstained=true`, mensaje f8, `sources=[]`, metadata presente | [x] |
| T18 | Tests persona: explícita→`Persona(name)`; ausente→`None`; inexistente→400 JSON | [x] |
| T19 | Tests CORS: cabeceras presentes; orígenes desde Settings (override), no `*` hardcodeado | [x] |
| T20 | Tests validación/errores: query vacía/ausente→422 sin orquestador; OrchestratorError→400; infra→503 sin traza; body JSON no HTML | [x] |
| T21 | Test DI: override sustituye al orquestador real; `build_orchestrator` nunca se invoca; import de `wowrag.api` no arrastra torch/psycopg | [x] |
| Z1 | `./init.sh` exit 0, todo verde, trazabilidad R1..R25, api/ sin SQL ni HTTP a Ollama | [x] |

## Ficheros creados

- `src/wowrag/api/schemas.py` — `AskRequest`.
- `src/wowrag/api/dependencies.py` — `get_orchestrator` + `build_orchestrator` (perezoso).
- `src/wowrag/api/routes.py` — `APIRouter` con `/ask` y `/health` + mapeo errores.
- `src/wowrag/api/app.py` — `create_app()` (FastAPI + CORS + router).
- `tests/test_api.py` — 21 tests (TestClient + FakeOrchestrator).

## Ficheros editados

- `requirements.txt` — añadidos `fastapi==0.137.1`, `uvicorn==0.49.0`, `httpx==0.28.1`.
- `requirements-llm.txt` — `httpx` retirado (promovido a `requirements.txt`); ahora solo comentario explicativo.
- `tests/test_requirements_pinned.py` — fastapi/uvicorn/httpx a `PINNED`; deferred = torch/sentence-transformers/psycopg.
- `src/wowrag/config.py` — 4 campos CORS en `Settings`.
- `src/wowrag/api/__init__.py` — placeholder reemplazado por re-export de `create_app`.
- `tests/test_config.py` — defaults CORS + 2 tests de override (constructor + env).
- `.env.example` — bloque CORS documentado (formato JSON para listas).
- `specs/f9-http-api/tasks.md` — 22 tasks marcadas `[x]`.

## Trazabilidad R<n> → test

| Req | Test(s) |
|-----|---------|
| R1  | `test_api.py::test_create_app_returns_fastapi_with_routes` |
| R2  | `test_ask_happy_path_maps_answer` (claves top-level) |
| R3  | `test_health_ok_without_orchestrator` |
| R4  | `test_ask_calls_orchestrator_once_with_query`, `test_ask_happy_path_maps_answer` |
| R5  | `test_ask_happy_path_maps_answer` (sources `{n,title,url}`) |
| R6  | `test_ask_happy_path_maps_answer` (metadata 1:1) |
| R7  | `test_ask_happy_path_maps_answer` (metadata sin recálculo) |
| R8  | `test_ask_abstention_path` (`abstained=true`, mensaje f8, `sources=[]`) |
| R9  | `test_ask_abstention_path` (metadata presente en abstención) |
| R10 | `test_ask_persona_explicit_forwarded` |
| R11 | `test_ask_persona_default_when_absent` |
| R12 | `test_ask_unknown_persona_returns_400` |
| R13 | `test_cors_headers_present` |
| R14 | `test_cors_origins_from_settings_not_hardcoded`; `test_config.py::test_cors_allow_origins_override_constructor`, `::test_cors_allow_origins_override_from_env` |
| R15 | `test_ask_empty_or_missing_query_422` (parametrizado: `"   "`, `""`, sin query) |
| R16 | `test_ask_orchestrator_error_400` |
| R17 | `test_ask_infra_error_503` (RetrieverError/EmbeddingError/VectorStoreError/LLMError) |
| R18 | `test_ask_infra_error_503`, `test_error_body_is_json_not_html`, `test_ask_unknown_persona_returns_400` |
| R19 | `test_dependency_override_used_real_orchestrator_never_built` (ruta vía `Depends`) |
| R20 | `test_dependency_override_used_...`, `test_importing_api_does_not_pull_heavy_deps` |
| R21 | toda la suite `test_api.py` corre bajo `pytest -m "not integration"` en `init.sh`; `test_dependency_override_used_...` |
| R22 | handlers `def` (cubierto implícitamente: todos los tests pasan por el threadpool del TestClient) |
| R23 | `test_requirements_pinned.py::test_required_dependencies_are_pinned` |
| R24 | `test_requirements_pinned.py::test_required_dependencies_are_pinned` + `::test_deferred_dependencies_absent` |
| R25 | `./init.sh` exit 0 con toda la suite verde |

## Cambio de dependencias (confirmación)

- `requirements.txt`: `fastapi==0.137.1`, `uvicorn==0.49.0`, `httpx==0.28.1` (pineados con `==`).
- `requirements-llm.txt`: `httpx` retirado (sin duplicado).
- `tests/test_requirements_pinned.py`: `PINNED` ahora incluye fastapi/uvicorn/httpx; `DEFERRED` = torch/sentence-transformers/psycopg.
- `./init.sh` reinstala desde `requirements.txt` → las deps de f9 quedan disponibles para `TestClient` en la suite por defecto.

## Resultado `./init.sh`

- **Exit code 0.**
- **210 passed, 2 skipped, 5 deselected, 1 warning.**
- Baseline previo: 187 passed, 3 skipped. +23 tests (21 `test_api.py` + 2 CORS en `test_config.py`).
- El reparto skipped/deselected cambió respecto a la baseline porque instalar `httpx`
  permite *colectar* los tests `@integration` de real-Ollama (antes uno se saltaba por
  `httpx` ausente; ahora se deselecciona por la marca `integration`). La suite sigue
  100% verde y exit 0.

## Desviaciones del spec

- **Ninguna desviación funcional.** Un único ajuste menor de test (no de contrato):
  el spec sugería verificar las rutas iterando `app.routes`; en FastAPI 0.137 esa
  colección envuelve el router en `_IncludedRouter` (sin `.path`), así que la
  verificación de R1 lee las rutas desde `app.openapi()["paths"]` (más robusto entre
  versiones). Mismo objetivo (`/ask` y `/health` registradas).
- **Warning no bloqueante:** Starlette emite `StarletteDeprecationWarning` sugiriendo
  `httpx2` para el `TestClient`. No afecta a los tests (todos verdes); el spec fija
  `httpx` (≥0.27) y no menciona `httpx2`. Sin acción.
- **Versiones de deps:** spec dejó las versiones concretas "al implementer" (FastAPI
  reciente + Starlette + httpx ≥0.27). Elegidas las últimas disponibles: fastapi
  0.137.1, uvicorn 0.49.0, httpx 0.28.1.
