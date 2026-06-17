# Design — f9-http-api

> CÓMO se construye la capa HTTP que expone f8 sobre FastAPI. Respeta el layout de
> `docs/architecture.md` §6 (`src/wowrag/api/`), §8 (diseño pensando en el frontend:
> respuestas estructuradas, persona por petición, CORS configurable) y las
> convenciones del proyecto (type hints, `from __future__ import annotations`,
> `logging` por módulo, config por `pydantic-settings`, sin secretos en el repo).
> f9 **solo expone f8**: depende de la interfaz `RagOrchestrator`, nunca de
> `DefaultRagOrchestrator` dentro de la ruta.

## 0. Decisión de entrega: PR único (~≤ 360 líneas)

f9 es una capa fina: una factoría de app, un módulo de rutas, modelos pydantic de
request/response, una dependencia DI, un par de campos nuevos en `Settings`, dos
líneas nuevas en `requirements.txt`, un ajuste a un test heredado de f0 y los tests
unitarios con `TestClient`. **No hay servicios reales en el camino de test** (el
orquestador se sustituye por un fake vía `dependency_overrides`). Cabe en un PR
único dentro del presupuesto de ~400 líneas.

Estimación de líneas cambiadas (apply):

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `api/schemas.py` (request/response pydantic) | ~45 |
| `api/dependencies.py` (`get_orchestrator` + `build_orchestrator`) | ~40 |
| `api/routes.py` (`/ask`, `/health`, mapeo de errores) | ~70 |
| `api/app.py` (`create_app`, CORS, registro de rutas) | ~45 |
| `api/__init__.py` (re-exports; reemplaza el placeholder) | ~8 |
| `config.py` (campos CORS) | ~6 |
| `requirements.txt` (fastapi, uvicorn, httpx) | ~3 |
| `tests/test_requirements_pinned.py` (mover fastapi/uvicorn/httpx a requeridos) | ~10 (editar) |
| `tests/test_api.py` (TestClient + fake orchestrator: feliz, abstención, persona, errores, CORS, health) | ~140 |
| **Total estimado** | **~360 líneas** — por debajo de 400. |

**Recomendación: PR único.** No se necesitan slices encadenados. La numeración
`R<n>` es estable independientemente de esta decisión. Si el revisor exigiera
recortar, el corte natural sería Slice A = app + `/health` + CORS + deps
(R1, R3, R13, R14, R23, R24) y Slice B = `/ask` + schemas + mapeo de errores +
persona (R2, R4–R12, R15–R22), pero **no se recomienda**.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    config.py                  # EDITAR — añadir cors_allow_origins (+ flags CORS mínimos)
    api/
      __init__.py              # EDITAR — reemplazar placeholder; re-exportar create_app
      app.py                   # NUEVO — create_app(): FastAPI + CORS + registro de rutas
      routes.py                # NUEVO — router con POST /ask y GET /health + mapeo de errores
      schemas.py               # NUEVO — AskRequest / AskResponse (pydantic de transporte)
      dependencies.py          # NUEVO — get_orchestrator (Depends) + build_orchestrator (composición real)
requirements.txt               # EDITAR — añadir fastapi==, uvicorn==, httpx== (pineados)
tests/
  test_requirements_pinned.py  # EDITAR — fastapi/uvicorn/httpx pasan de "deferred" a "pinned"
  test_api.py                  # NUEVO — TestClient + fake RagOrchestrator vía dependency_overrides
```

Notas de layout:
- `src/wowrag/api/` ya existe como placeholder de f0 (`__init__.py` con docstring
  "The FastAPI app lands in f9"). f9 lo materializa.
- Separación de responsabilidades dentro de `api/`: **transporte** (schemas),
  **composición/DI** (dependencies), **rutas** (routes), **ensamblado** (app).
  Esto mantiene `create_app` pequeño y deja la ruta dependiente solo de la interfaz
  `RagOrchestrator` (testable con override). El revisor rechaza mezcla de capas:
  aquí NO hay SQL, ni HTTP a Ollama, ni lógica de retrieval/prompt — solo transporte.

## 2. Reutilización de los modelos de f8 (R7) y modelos de transporte (R2, R5, R6, R15)

f9 **no** redefine `Answer`/`Source`/`AnswerMetadata`: son modelos pydantic
(`BaseModel`) y FastAPI los serializa a JSON directamente. Se reutilizan tal cual.

### Request: `api/schemas.py`

```python
from __future__ import annotations
from pydantic import BaseModel, field_validator

class AskRequest(BaseModel):
    query: str
    persona: str | None = None      # nombre de persona; None -> default por config (R10, R11)

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be a non-empty string")  # -> 422 (R15)
        return v
```

> El validador de `query` cubre R15 (vacío/solo espacios → 422 de pydantic) en la
> capa de transporte, **antes** de invocar al orquestador. Esto duplica
> intencionadamente la guarda que f8 ya hace con `OrchestratorError`, pero a nivel
> HTTP devuelve un 422 limpio sin entrar en la ruta. R16 cubre el caso defensivo en
> que `OrchestratorError` aún así se lance (p. ej. otra ruta interna).

### Response: reutilizar `Answer` de f8 (R7)

La respuesta de `POST /ask` es directamente `Answer` (de `wowrag.models`). Se
declara como `response_model=Answer` en la ruta para que el esquema OpenAPI exponga
`{answer, sources: [{n,title,url}], abstained, metadata: {model,persona,max_score,scores}}`
sin reescribir nada (R2, R5, R6, R7). No se crea un `AskResponse` espejo: añadiría
duplicación y riesgo de divergencia con f8.

## 3. Inyección de dependencias y testabilidad (R19, R20, R21)

### `api/dependencies.py`

```python
from __future__ import annotations
from wowrag.rag import RagOrchestrator   # la INTERFAZ (Protocol), no la impl

def get_orchestrator() -> RagOrchestrator:
    """Dependencia FastAPI: provee el RagOrchestrator. Sobreescribible en tests."""
    return build_orchestrator()

def build_orchestrator() -> RagOrchestrator:
    """Punto de composición REAL: arma DefaultRagOrchestrator con impls reales.

    Construye Retriever(bge-m3 + pgvector) + PromptBuilder + OllamaLLM. SOLO se
    invoca en runtime real; los tests unitarios NUNCA llegan aquí porque
    dependency_overrides[get_orchestrator] inyecta un fake.
    """
    ...  # importa BgeM3Embeddings, PgVectorStore, OllamaLLM, DefaultRetriever, etc.
```

- La ruta declara `orchestrator: RagOrchestrator = Depends(get_orchestrator)`
  (R19). Depende del **Protocol**, no del concreto.
- `build_orchestrator` es el ÚNICO sitio que importa impls reales (pgvector, bge-m3,
  Ollama). Importa **dentro de la función** (import perezoso) para que importar
  `api.app` / `api.routes` en tests NO arrastre torch/psycopg/httpx-a-Ollama. Mismo
  patrón de import perezoso que `OllamaLLM` (f7).
- **Tests (R20, R21):** `app.dependency_overrides[get_orchestrator] = lambda: fake`
  donde `fake` implementa `RagOrchestrator.answer`. El `TestClient` ejercita las
  rutas sin Postgres/bge-m3/Ollama/red. Cero `@pytest.mark.integration`.

### Estrategia de test con `dependency_overrides`

```python
from fastapi.testclient import TestClient
from wowrag.api import create_app
from wowrag.api.dependencies import get_orchestrator

class FakeOrchestrator:
    def __init__(self, answer: Answer | Exception): ...
    def answer(self, query, persona=None) -> Answer:
        if isinstance(self._a, Exception): raise self._a
        return self._a

def client_with(fake) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_orchestrator] = lambda: fake
    return TestClient(app)
```

El fake devuelve un `Answer` fijo (camino feliz / abstención) o lanza
(`OrchestratorError`, `RetrieverError`, `PersonaNotFoundError`) para cubrir el mapeo
de errores. `TestClient` requiere `httpx` (ver §7).

## 4. Configuración de CORS (R13, R14)

CORS vía `fastapi.middleware.cors.CORSMiddleware`, con orígenes **desde
`Settings`**, no hardcodeados.

`config.py` — añadir:

```python
cors_allow_origins: list[str] = ["*"]   # CSV en env -> lista; "*" por defecto explícito y documentado
cors_allow_credentials: bool = False
cors_allow_methods: list[str] = ["*"]
cors_allow_headers: list[str] = ["*"]
```

- `create_app` lee `Settings().cors_allow_origins` y registra el middleware:
  `app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allow_origins, ...)`.
- **Decisión sobre `*`:** el default es `["*"]` para no bloquear el desarrollo del
  frontend in-game que aún no existe, pero es **configurable** a una lista cerrada
  por env (`WOWRAG_CORS_ALLOW_ORIGINS` o equivalente pydantic-settings). Esto
  satisface R14: el valor no está hardcodeado en el código de rutas; vive en
  `Settings` y se sobreescribe por entorno. `allow_credentials` por defecto `False`
  (compatible con `*`; activarlo con `*` lo prohíbe el estándar CORS).
- pydantic-settings parsea `list[str]` desde una variable de entorno; si el
  implementer encuentra fricción con el formato (JSON vs CSV), documenta el formato
  esperado en `.env.example`. No es bloqueante para el contrato.

## 5. Rutas y mapeo de errores (R2–R12, R15–R18, R22)

`api/routes.py` — un `APIRouter` con dos rutas. Handlers **síncronos (`def`)** para
que FastAPI los ejecute en su threadpool (ver §6).

```python
router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:          # R3: no toca orquestador/red
    return {"status": "ok"}

@router.post("/ask", response_model=Answer)
def ask(
    body: AskRequest,                                        # R15 (validación)
    orchestrator: RagOrchestrator = Depends(get_orchestrator),  # R19
) -> Answer:
    persona = _resolve_persona(body.persona)   # str|None -> Persona|None (R10, R11, R12)
    try:
        return orchestrator.answer(body.query, persona)     # R4, R22
    except OrchestratorError as e:
        raise HTTPException(status_code=400, detail=str(e))  # R16
    except PersonaNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))  # R12
    except Exception as e:                                   # infra (Retriever/LLM/Store)
        logger.exception("orchestrator failure")
        raise HTTPException(status_code=503, detail="upstream RAG component failed")  # R17, R18
```

Resolución de persona (R10, R11, R12):

```python
def _resolve_persona(name: str | None) -> Persona | None:
    if name is None:
        return None                       # R11: f8 resuelve Settings.default_persona
    return load_persona(name)             # R10; PersonaNotFoundError -> 400 (R12)
```

> Decisión: f9 resuelve `str -> Persona` con `load_persona` (f0) para validar el
> nombre **antes** de llamar a f8 y devolver un 400 limpio (R12). El default
> (`None`) se delega íntegro a f8 (R11), sin duplicar `Settings.default_persona`.

### Tabla de mapeo de errores

| Situación | Origen | HTTP | Cuerpo | Req |
|-----------|--------|------|--------|-----|
| `query` ausente / no string / vacía | validación pydantic `AskRequest` | **422** | `{"detail": [...]}` (pydantic) | R15 |
| `OrchestratorError` (query inválida a nivel f8) | f8 | **400** | `{"detail": "..."}` | R16 |
| `PersonaNotFoundError` (persona desconocida) | f0/`load_persona` | **400** | `{"detail": "..."}` | R12 |
| `RetrieverError` / `EmbeddingError` / `VectorStoreError` / `LLMError` | f3/f4/f5/f7 | **503** | `{"detail": "upstream RAG component failed"}` | R17, R18 |
| Camino feliz (`abstained=False`) | f8 | **200** | `Answer` JSON con `sources` | R4–R7 |
| Abstención (`abstained=True`) | f8 | **200** | `Answer` JSON, `sources=[]` | R8, R9 |
| `GET /health` | f9 | **200** | `{"status": "ok"}` | R3 |

> Las excepciones de infra concretas (`RetrieverError`, `LLMError`, etc.) se capturan
> por su tipo si están disponibles; el `except Exception` final garantiza que ningún
> fallo de infra escape como 500 con stack trace HTML (R18). Se registra con
> `logger.exception` (un logger por módulo, `docs/conventions.md`), nunca `print`.
> Las trazas internas no se exponen en el cuerpo (R17, R18).

## 6. Decisión síncrono / threadpool (R22)

**Decisión: handlers `def` (síncronos), NO `async def`.**

- `RagOrchestrator.answer` es **síncrono** y bloqueante (embeddings GPU, consulta
  pgvector, HTTP a Ollama). FastAPI ejecuta los handlers declarados con `def`
  (no `async`) en un **threadpool**, evitando bloquear el event loop. Es el patrón
  recomendado por FastAPI/Starlette para trabajo síncrono bloqueante.
- Alternativa descartada: `async def` envolviendo `answer` en
  `run_in_threadpool`/`asyncio.to_thread`. Añade ceremonia sin beneficio: FastAPI ya
  hace exactamente eso para handlers `def`. Mantener `def` es más simple y directo.
- Esto deja a f8 totalmente agnóstico de async (su contrato es síncrono). Si más
  adelante f8 ofreciera una API async nativa, solo cambiaría este punto.

## 7. Decisión de dependencias y `init.sh` (R23, R24, R25) — punto crítico

Estado actual verificado:
- `requirements.txt` contiene SOLO `pydantic-settings`, `pyyaml`, `pytest`.
  `fastapi`, `uvicorn`, `torch`, `sentence-transformers`, `psycopg` están
  explícitamente **diferidos** (comentario en `requirements.txt`).
- `httpx` vive AISLADO en `requirements-llm.txt` (NO lo instala `init.sh`).
- `init.sh` instala `requirements.txt` y corre `pytest -m "not integration"`.
- **CONFLICTO HEREDADO:** `tests/test_requirements_pinned.py` (test de f0, R13)
  tiene `DEFERRED = ["fastapi", "uvicorn", "torch", "sentence-transformers", "psycopg"]`
  y `test_deferred_dependencies_absent` **falla** si `fastapi`/`uvicorn` aparecen en
  `requirements.txt`. Por tanto, añadir f9 a `requirements.txt` rompe un test
  existente si no se actualiza ese test en el MISMO PR.

**Decisión (resuelve el conflicto explícitamente):**

1. Añadir a `requirements.txt`, **pineados con `==`** (R23):
   - `fastapi==<versión>`
   - `uvicorn==<versión>`  (servidor ASGI para runtime; no usado por los tests)
   - `httpx==<versión>`  (lo necesita `fastapi.testclient.TestClient`/Starlette)
   El implementer fija versiones concretas y compatibles (FastAPI reciente +
   Starlette + httpx ≥0.27). `httpx` **se promueve** desde `requirements-llm.txt`
   al `requirements.txt` principal porque ahora la suite por defecto lo necesita
   (el `TestClient`); puede dejarse también en `requirements-llm.txt` o eliminarse
   de ahí para evitar duplicado (decisión menor del implementer; preferible quitarlo
   de `requirements-llm.txt` y dejarlo solo en `requirements.txt`).
2. **Actualizar `tests/test_requirements_pinned.py` (R24):** mover `fastapi`,
   `uvicorn` y `httpx` de la lista `DEFERRED` a la lista `PINNED` (que ya verifica
   presencia + `==`). Dejar `torch`, `sentence-transformers`, `psycopg` en
   `DEFERRED` (siguen sin instalarse por `init.sh`; f3/f4 usan import perezoso).
   Tras el cambio, `test_required_dependencies_are_pinned` cubre los tres nuevos y
   `test_deferred_dependencies_absent` ya no los exige ausentes. La suite sigue
   verde (R25).
3. **Camino de test sin servicios reales:** `torch`/`sentence-transformers`/`psycopg`
   siguen fuera de `requirements.txt`. Los tests de f9 NUNCA invocan
   `build_orchestrator` (import perezoso de impls reales), así que importar
   `wowrag.api.create_app` no arrastra esas libs. Solo se necesitan
   `fastapi`+`httpx` (TestClient) para los tests unitarios de f9, ambos en
   `requirements.txt` → corren bajo `pytest -m "not integration"` en `init.sh` (R21).

> Por qué `httpx` al `requirements.txt` principal y no dejarlo en
> `requirements-llm.txt`: el `TestClient` que ejercita la app (R21) lo importa, y
> esos tests son de la suite por defecto, no `@integration`. Mantenerlo aislado haría
> que `init.sh` no pudiera correr los tests de f9 → violaría R21/R25.

## 8. Estrategia de tests (todos DB-free / GPU-free / network-free; corren con `init.sh`)

Trazabilidad `R<n>` ↔ test obligatoria (comentar cada test con su `R<n>`).
`tests/test_api.py` usa `TestClient(create_app())` con
`app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator(...)`.

- `test_create_app_returns_fastapi` — `create_app()` devuelve una instancia FastAPI
  con `/ask` y `/health` registradas (R1).
- `test_health_ok` — `GET /health` → 200 `{"status":"ok"}`, sin tocar el orquestador
  (fake con spy que registra si fue llamado) (R3).
- `test_ask_happy_path_maps_answer` — fake devuelve `Answer(abstained=False, sources=[...])`;
  `POST /ask` → 200 con `answer`, `sources` como `[{n,title,url}]`, `abstained=false`,
  `metadata{model,persona,max_score,scores}` (R2, R4, R5, R6, R7).
- `test_ask_calls_orchestrator_once_with_query` — el fake registra (query, persona);
  se invoca exactamente una vez con la `query` del body (R4).
- `test_ask_abstention_path` — fake devuelve `Answer(abstained=True, sources=[])`;
  respuesta 200 con `abstained=true`, mensaje de abstención y `sources=[]` (R8); con
  `metadata` presente (R9).
- `test_ask_persona_explicit_forwarded` — body `{"query":"q","persona":"orc"}`; el
  fake recibe un `Persona` con `name=="orc"` (R10).
- `test_ask_persona_default_when_absent` — body sin `persona`; el fake recibe
  `persona is None` (R11).
- `test_ask_unknown_persona_returns_4xx` — body con `persona` inexistente →
  `PersonaNotFoundError` → 400 con cuerpo JSON de error (R12, R18).
- `test_cors_headers_present` — `TestClient` con `Origin` permitido en `Settings`;
  la respuesta incluye `access-control-allow-origin` (R13).
- `test_cors_origins_from_settings` — `create_app` con `Settings(cors_allow_origins=
  ["https://game.example"])` (override) refleja ese origen, no `*` hardcodeado (R14).
- `test_ask_empty_query_422` — body `{"query":"   "}` o sin `query` → 422; el fake
  spy confirma que NO se llamó al orquestador (R15).
- `test_ask_orchestrator_error_400` — fake lanza `OrchestratorError` → 400 con cuerpo
  JSON (R16).
- `test_ask_infra_error_503` — fake lanza `RetrieverError`/`LLMError` → 503 con cuerpo
  JSON, sin traza interna en el body (R17, R18).
- `test_error_body_is_json` — un caso de error devuelve `application/json`, no HTML
  ni stack trace (R18).
- `test_dependency_override_used` — confirma que `dependency_overrides` reemplaza el
  orquestador real (el real nunca se construye; `build_orchestrator` no se invoca)
  (R19, R20, R21).
- `tests/test_requirements_pinned.py` (editado) — `fastapi`/`uvicorn`/`httpx` en
  `PINNED`, pineados con `==`; ya no exigidos ausentes (R23, R24).
- `test_sync_handler_does_not_block` (opcional/ligero) — handler es `def`; cubierto
  implícitamente porque todos los tests pasan por el threadpool del TestClient (R22).

## 9. Decisión: streaming/SSE diferido

f9 **NO** incluye streaming (SSE) de la respuesta. Razones:
- f7 expone `generate_stream`, pero f8 (`RagOrchestrator.answer`) devuelve un
  `Answer` completo síncrono; no hay API de orquestación en streaming. Exponer SSE
  requeriría una nueva ruta de orquestación de streaming → fuera del alcance de f9
  (que "solo expone f8 sobre HTTP").
- El frontend in-game aún no existe; el contrato de aceptación pide
  `{answer, sources, abstained, metadata}` (respuesta completa), no streaming.
- Se difiere a una feature posterior (cuando exista una API de orquestación en
  streaming y un cliente que la consuma). f9 deja el camino libre: una ruta
  `POST /ask/stream` futura no rompería `POST /ask`.

## 10. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| `AskResponse` espejo de `Answer` en `schemas.py` | Duplica `Answer`/`Source`/`AnswerMetadata` (f8) y arriesga divergencia; FastAPI serializa `Answer` directamente con `response_model=Answer` (R7) |
| Construir `DefaultRagOrchestrator` inline en la ruta | Imposibilita el override en tests y acopla HTTP a las impls reales (pgvector/bge-m3/Ollama). Se usa `Depends(get_orchestrator)` (R19, R20) |
| `async def` + `run_in_threadpool` manual | FastAPI ya ejecuta handlers `def` en threadpool; el wrapper añade ceremonia sin beneficio (R22) |
| Orígenes CORS hardcodeados en `app.py` (o `*` fijo) | Viola §8 de architecture y R14; deben venir de `Settings`, configurables por entorno |
| Dejar `httpx` solo en `requirements-llm.txt` | El `TestClient` lo necesita y los tests de f9 son de la suite por defecto; quedaría sin instalar por `init.sh` → R21/R25 rotos |
| No actualizar `test_requirements_pinned.py` | El test de f0 fallaría al añadir fastapi/uvicorn → suite roja; R24 lo resuelve moviéndolos a `PINNED` |
| Incluir streaming/SSE en f9 | f8 no expone orquestación en streaming y no hay cliente; se difiere (§9) |
| Manejar abstención como error HTTP (4xx/5xx) | La abstención es una respuesta válida (`docs/conventions.md`): 200 con `abstained=true` (R8) |
| Validar `query` solo en f8 (sin validador en `AskRequest`) | Perdería el 422 limpio de pydantic antes de entrar a la ruta; el validador de transporte da mejor contrato HTTP (R15) |
| `Depends` que devuelve la impl concreta tipada como `DefaultRagOrchestrator` | Acopla la ruta al concreto; debe tiparse como el Protocol `RagOrchestrator` (R19) |
| Cuerpos de error como texto/HTML | FastAPI `HTTPException` ya devuelve JSON `{"detail": ...}`; nunca exponer stack traces (R18) |
