# Tasks — f9-http-api

> Checklist ordenada para implementar f9. Cada task referencia los `R<n>` de
> `requirements.md` que ayuda a cumplir. Sigue `design.md`. Todas las tasks
> empiezan sin marcar `[ ]`. Tests con `fakes` + `TestClient` (sin servicios
> reales); todo corre bajo `pytest -m "not integration"` en `./init.sh`.
> No marques una task `[x]` hasta que su parte de la suite esté verde.

## Dependencias e instalación (primero: desbloquea TestClient en init.sh)

- [x] **T1** — Añadir a `requirements.txt`, pineados con `==`: `fastapi`,
  `uvicorn`, `httpx` (versiones concretas compatibles: FastAPI reciente +
  Starlette + httpx ≥0.27). Quitar `httpx` de `requirements-llm.txt` para evitar
  duplicado (queda solo en `requirements.txt`). (R23)
- [x] **T2** — Actualizar `tests/test_requirements_pinned.py`: mover `fastapi`,
  `uvicorn`, `httpx` de `DEFERRED` a `PINNED`; dejar `torch`,
  `sentence-transformers`, `psycopg` en `DEFERRED`. Verificar que
  `test_required_dependencies_are_pinned` y `test_deferred_dependencies_absent`
  pasan. (R24, R25)
- [x] **T3** — Ejecutar `./init.sh` para que el venv instale fastapi/uvicorn/httpx
  y confirmar que la suite previa sigue verde antes de añadir código de f9. (R25)

## Configuración (CORS desde Settings)

- [x] **T4** — Añadir a `Settings` en `src/wowrag/config.py` los campos
  `cors_allow_origins: list[str] = ["*"]`, `cors_allow_credentials: bool = False`,
  `cors_allow_methods: list[str] = ["*"]`, `cors_allow_headers: list[str] = ["*"]`,
  configurables por entorno. Documentar el formato en `.env.example` si aplica. (R14)
- [x] **T5** — Añadir/actualizar test en `tests/test_config.py` que verifique que
  `Settings(cors_allow_origins=[...])` toma el valor (no hardcodeado). (R14)

## Modelos de transporte (request) y reutilización de Answer

- [x] **T6** — Crear `src/wowrag/api/schemas.py` con `AskRequest{query: str,
  persona: str | None = None}` y un `field_validator` que rechace `query`
  vacía/solo espacios con `ValueError` (→ 422). (R2, R10, R11, R15)
- [x] **T7** — Confirmar que la respuesta reutiliza `Answer` de `wowrag.models`
  (no crear `AskResponse` espejo): la ruta usará `response_model=Answer`. (R5, R6, R7)

## Inyección de dependencias (DI)

- [x] **T8** — Crear `src/wowrag/api/dependencies.py` con `get_orchestrator() ->
  RagOrchestrator` (devuelve `build_orchestrator()`) y `build_orchestrator()` que
  compone las impls reales (Retriever bge-m3+pgvector, PromptBuilder, OllamaLLM)
  con **import perezoso dentro de la función**, tipado como el Protocol
  `RagOrchestrator`. (R19, R20)

## Rutas y mapeo de errores

- [x] **T9** — Crear `src/wowrag/api/routes.py` con un `APIRouter`:
  `GET /health` (handler `def`, 200 `{"status":"ok"}`, sin tocar orquestador). (R3, R22)
- [x] **T10** — Añadir `POST /ask` (handler `def`, `response_model=Answer`) que
  reciba `AskRequest`, obtenga `orchestrator: RagOrchestrator =
  Depends(get_orchestrator)`, resuelva persona (`str|None -> Persona|None` con
  `load_persona`), e invoque `orchestrator.answer(query, persona)` exactamente una
  vez, devolviendo el `Answer`. (R2, R4, R5, R6, R7, R8, R9, R10, R11, R19, R22)
- [x] **T11** — Implementar el mapeo de errores en `/ask` según la tabla de
  `design.md` §5: `PersonaNotFoundError` → 400; `OrchestratorError` → 400; errores
  de infra (`RetrieverError`/`EmbeddingError`/`VectorStoreError`/`LLMError` y
  `except Exception` final) → 503 con cuerpo JSON `{"detail": ...}` y
  `logger.exception` (sin exponer trazas). (R12, R16, R17, R18)

## Ensamblado de la app + CORS

- [x] **T12** — Crear `src/wowrag/api/app.py` con `create_app() -> FastAPI` que
  instancie FastAPI, registre el router (T9–T11) y añada `CORSMiddleware` leyendo
  los orígenes/flags desde `Settings`. (R1, R13, R14)
- [x] **T13** — Reemplazar el placeholder `src/wowrag/api/__init__.py` para
  re-exportar `create_app` (`from wowrag.api.app import create_app`). (R1)

## Tests con TestClient + fake orchestrator (sin servicios reales)

- [x] **T14** — Crear `tests/test_api.py` con un `FakeOrchestrator` (devuelve un
  `Answer` fijo o lanza), un helper `client_with(fake)` que use
  `create_app()` + `app.dependency_overrides[get_orchestrator] = lambda: fake`, y
  el `TestClient`. (R19, R20, R21)
- [x] **T15** — Tests de app/rutas existentes: `create_app` devuelve FastAPI con
  `/ask` y `/health`; `GET /health` → 200 `{"status":"ok"}` sin invocar el
  orquestador (spy). (R1, R3)
- [x] **T16** — Tests camino feliz: `POST /ask` con `abstained=False` mapea
  `answer`, `sources` (`[{n,title,url}]`), `abstained`, `metadata`
  (`{model,persona,max_score,scores}`); `answer` invocado una vez con la `query`. (R2, R4, R5, R6, R7)
- [x] **T17** — Tests de abstención: `POST /ask` con `abstained=True` → 200,
  `abstained=true`, mensaje de abstención, `sources=[]`, `metadata` presente. (R8, R9)
- [x] **T18** — Tests de persona: `persona` explícita reenviada como `Persona`
  con ese `name` (R10); ausencia de `persona` → `persona is None` al orquestador
  (R11); `persona` inexistente → 400 JSON (R12).
- [x] **T19** — Tests de CORS: cabeceras CORS presentes para un `Origin` permitido
  (R13); orígenes provienen de `Settings` (override en `create_app`), no `*`
  hardcodeado (R14).
- [x] **T20** — Tests de validación y errores: `query` vacía/ausente → 422 sin
  invocar al orquestador (R15); `OrchestratorError` → 400 (R16); error de infra
  (`RetrieverError`/`LLMError`) → 503 sin traza en el body (R17); cuerpo de error
  es JSON, no HTML/stack trace (R18). (R15, R16, R17, R18)
- [x] **T21** — Test de DI: `dependency_overrides` reemplaza el orquestador real;
  `build_orchestrator` no se invoca en el camino de test (impls reales nunca se
  construyen). (R19, R20, R21)

## Auto-verificación final

- [x] **Z1** — Ejecutar `./init.sh` y confirmar: exit code 0; `pytest -m
  "not integration"` con todos los tests verdes (incluidos los nuevos de f9 y el
  `test_requirements_pinned.py` editado); sin `print()` de debug; trazabilidad
  `R1..R25` ↔ test completa; revisar que `src/wowrag/api/` no introduce SQL ni
  HTTP a Ollama (solo transporte). (R21, R23, R24, R25)
