# Requirements — f9-http-api

> QUÉ debe cumplir la capa HTTP que expone el pipeline RAG (f8) sobre FastAPI.
> Notación **EARS** estricta (ver `docs/specs.md`). Cada `R<n>` es una frase
> verificable mapeable a al menos un test. f9 **solo expone f8 sobre HTTP**: no
> cambia retrieval, prompt, LLM ni la lógica de orquestación/abstención.

## Alcance (recordatorio, no es un requisito)

- f9 envuelve `RagOrchestrator.answer(query, persona=None) -> Answer` (f8) en una
  app FastAPI con `POST /ask` y `GET /health`, CORS configurable, persona por
  petición o por config, y DI testeable.
- f9 **NO** toca `retrieval/`, `generation/`, `llm/`, `rag/` ni `models.py`
  (reutiliza `Answer`/`Source`/`AnswerMetadata` tal cual). No hay frontend (luego),
  ni scraping (f11), ni reranking (f12), ni eval harness (f10).
- Streaming/SSE (f7 `generate_stream`) se **difiere**; f9 expone solo la respuesta
  síncrona completa.

---

## App y rutas

**R1** — El sistema DEBE proveer una factoría de aplicación (p. ej.
`create_app() -> FastAPI`) en `src/wowrag/api/` que construya y devuelva una
instancia de FastAPI con las rutas y el middleware de f9 registrados.

**R2** — El sistema DEBE exponer una ruta `POST /ask` que acepte un cuerpo JSON y
devuelva un cuerpo JSON con las claves `answer`, `sources`, `abstained` y
`metadata`.

**R3** — El sistema DEBE exponer una ruta `GET /health` que responda `200 OK` con
un cuerpo JSON de estado (p. ej. `{"status": "ok"}`) sin invocar al orquestador,
retriever, LLM, base de datos ni red.

## Contrato de `POST /ask` (camino feliz)

**R4** — CUANDO se recibe un `POST /ask` con una `query` no vacía, el sistema DEBE
invocar exactamente una vez `RagOrchestrator.answer(query, persona)` y devolver
`200` con el `Answer` resultante serializado a JSON.

**R5** — CUANDO `RagOrchestrator.answer` devuelve un `Answer` con `abstained=False`,
el sistema DEBE incluir en la respuesta el `answer` (texto del LLM) y la lista
`sources`, donde cada fuente se serializa como `{n, title, url}` (forma de cita
estable del proyecto, `docs/conventions.md`).

**R6** — El sistema DEBE incluir en la respuesta el objeto `metadata` con los
campos `model`, `persona`, `max_score` y `scores`, serializados desde
`AnswerMetadata` sin recalcularlos.

**R7** — El sistema DEBE serializar la respuesta a partir del `Answer` de f8 sin
alterar sus valores (mapeo 1:1 de `answer`, `sources`, `abstained`, `metadata`);
no DEBE reconstruir citas, scores ni el nombre de persona.

## Camino de abstención

**R8** — CUANDO `RagOrchestrator.answer` devuelve un `Answer` con `abstained=True`,
el sistema DEBE devolver `200` con `abstained` en `true`, el `answer` con el
mensaje de abstención de f8, y `sources` como lista vacía `[]`.

**R9** — MIENTRAS la respuesta es una abstención, el sistema DEBE seguir incluyendo
el objeto `metadata` (al menos `model`, `persona`, `max_score`, `scores`) para
diagnóstico.

## Persona por petición y fallback por config

**R10** — DONDE el cuerpo de `POST /ask` incluye un campo `persona` no nulo, el
sistema DEBE resolver esa persona por su nombre y pasarla a
`RagOrchestrator.answer(query, persona)`.

**R11** — SI el cuerpo de `POST /ask` no incluye `persona` (o es `null`), ENTONCES
el sistema DEBE invocar `RagOrchestrator.answer(query, persona=None)`, delegando la
resolución del default en f8/`Settings.default_persona` (sin duplicar esa lógica
en la capa HTTP).

**R12** — SI el cuerpo de `POST /ask` incluye un `persona` cuyo nombre no
corresponde a ninguna persona cargable, ENTONCES el sistema DEBE responder con un
error HTTP `4xx` y un cuerpo JSON de error claro, sin un stack trace crudo.

## CORS (frontend futuro)

**R13** — El sistema DEBE registrar middleware CORS en la app, de modo que las
respuestas a peticiones cross-origin permitidas incluyan las cabeceras CORS
correspondientes (p. ej. `Access-Control-Allow-Origin`).

**R14** — El sistema DEBE leer los orígenes CORS permitidos desde la configuración
(`Settings`), no hardcodeados; el comodín `*` solo es admisible como valor por
defecto explícito y documentado, configurable a una lista cerrada de orígenes.

## Validación y mapeo de errores

**R15** — SI el cuerpo de `POST /ask` es inválido (falta `query`, `query` no es
string, o `query` es vacía/solo espacios), ENTONCES el sistema DEBE responder con
un código `4xx` (422 de validación pydantic, o 400) y un cuerpo JSON de error, sin
invocar al orquestador.

**R16** — SI `RagOrchestrator.answer` lanza `OrchestratorError` (entrada inválida a
nivel de orquestador), ENTONCES el sistema DEBE responder con un código `4xx`
(p. ej. 400) y un cuerpo JSON de error claro.

**R17** — SI `RagOrchestrator.answer` lanza un error de infraestructura
(p. ej. `RetrieverError`, `EmbeddingError`, `VectorStoreError`, `LLMError`),
ENTONCES el sistema DEBE responder con un código `5xx` (p. ej. 503) y un cuerpo
JSON de error claro, sin exponer trazas internas.

**R18** — El sistema DEBE devolver los cuerpos de error como JSON estructurado
(p. ej. `{"detail": "..."}` o `{"error": "..."}`), nunca como HTML ni como un
stack trace en texto plano.

## Inyección de dependencias y testabilidad

**R19** — El sistema DEBE obtener su `RagOrchestrator` a través de una dependencia
de FastAPI (p. ej. `Depends(get_orchestrator)`), de modo que la ruta dependa de la
interfaz `RagOrchestrator` y no construya el orquestador concreto inline.

**R20** — El sistema DEBE permitir sustituir el `RagOrchestrator` en tests vía
`app.dependency_overrides`, de modo que `POST /ask` pueda ejercitarse con un
orquestador falso **sin** Postgres, bge-m3, Ollama ni red.

**R21** — Los tests unitarios de f9 DEBEN ejercitar la app mediante el `TestClient`
de Starlette/FastAPI con un orquestador falso inyectado, sin tocar servicios
reales, y DEBEN ejecutarse dentro de la suite por defecto de `./init.sh`
(`pytest -m "not integration"`), no bajo la marca `@pytest.mark.integration`.

## Decisión síncrono / async

**R22** — DADO que `RagOrchestrator.answer` es síncrono y potencialmente
bloqueante, el sistema DEBE invocarlo de forma que no bloquee el event loop de
FastAPI (handler `def` síncrono ejecutado en el threadpool de FastAPI, o
equivalente documentado en `design.md`).

## Dependencias e instalación (init.sh)

**R23** — El sistema DEBE declarar `fastapi`, `uvicorn` y el cliente HTTP que
necesita el `TestClient` (`httpx`) como dependencias **pineadas con `==`** en
`requirements.txt`, de modo que `./init.sh` las instale y los tests de f9 corran en
la suite por defecto.

**R24** — El sistema DEBE actualizar la prueba de pinning heredada de f0
(`tests/test_requirements_pinned.py`) para reflejar que `fastapi`, `uvicorn` y
`httpx` ahora son dependencias requeridas y pineadas (y dejan de ser
"deferred"/prohibidas), manteniendo verde toda la suite tras el cambio.

**R25** — El sistema DEBE mantener `./init.sh` terminando en exit code 0 con todos
los tests `-m "not integration"` en verde tras añadir f9.
