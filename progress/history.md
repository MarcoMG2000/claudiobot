# Bitácora histórica (append-only)

> Cada vez que se cierra una sesión, su resumen se añade aquí.
> No edites entradas anteriores. Solo añades al final.

---

## f0-project-skeleton — Project skeleton & configuration system

- **Fecha de cierre:** 2026-06-03
- **Estado final:** `done`
- **Tasks cubiertas:** T1–T13 (todas marcadas `[x]` en `specs/f0-project-skeleton/tasks.md`).
  Esqueleto de subpaquetes, Settings (pydantic-settings), Persona + loader,
  YAMLs simple/orc/troll, default_persona + exports, requirements.txt pineado,
  .gitignore/.env.example, suites de tests (T8–T12) y verificación final (T13).
- **Trazabilidad:** R1–R14 verificadas, cada requirement cubierto por al menos
  un test concreto (ver `progress/review_f0-project-skeleton.md` para el mapa
  R<n> → test).
- **Tests:** 26 passed, `./init.sh` exit 0 (pytest verde, Python 3.14.4).
- **Veredicto del reviewer:** APROBADO, sin cambios requeridos
  (`progress/review_f0-project-skeleton.md`).

---

## f3-embeddings-provider — Embeddings provider (abstraction + bge-m3)

- **Fecha de cierre:** 2026-06-15
- **Estado final:** `done`
- **Flujo:** spec aprobado por humano → `implementer` → `reviewer`
  CHANGES_REQUESTED (R10: los nuevos campos de `Settings`
  `embedding_batch_size`/`embedding_device` no tenían cobertura de tests) →
  `implementer` corrigió (añadió
  `test_embedding_batch_size_and_device_overridable_from_env` y extendió
  `EXPECTED_DEFAULTS`) → `reviewer` APROBADO.
- **Construido:** `EmbeddingProvider` (Protocol) + `EmbeddingError`
  (`src/wowrag/embeddings/base.py`), `FakeEmbeddingProvider` solo-stdlib
  (`fake.py`), `BgeM3Embeddings` con import perezoso de FlagEmbedding
  (`bge_m3.py`), re-exports del paquete (`__init__.py`), 2 nuevos campos de
  `Settings` (`config.py`), `requirements-ml.txt` (deps de ML aisladas de
  init.sh).
- **Tests:** `./init.sh` exit 0, 86 passed + 1 skipped (el fichero de
  integración de bge_m3 está marcado `@pytest.mark.integration`, se omite sin
  FlagEmbedding).
- **Reports:** `progress/impl_f3-embeddings-provider.md`,
  `progress/review_f3-embeddings-provider.md`.

---

## f4-vector-store-pgvector — Vector store (abstraction + pgvector) and indexing

- **Fecha de cierre:** 2026-06-16
- **Estado final:** `done`
- **Entrega:** 3 slices apilados (el humano eligió PRs encadenados):
  - **Slice A** (commit `1d84d2c`): `VectorStore` (Protocol) + `VectorStoreError`
    (`src/wowrag/store/base.py`), `FakeVectorStore` en memoria con coseno
    solo-stdlib (`fake.py`), re-exports del paquete (`__init__.py`),
    `Settings.vector_table`/`distance_metric` con tests de default y
    override por env. Reviewer APROBADO.
  - **Slice B** (commit `cbf9ac1`): `PgVectorStore` con import perezoso de
    psycopg/pgvector (`pgvector_store.py`), `migrations.sql` idempotente,
    `requirements-pg.txt` (driver aislado de init.sh), tests de integración
    `@pytest.mark.integration`, tests unitarios R13/R14 de aislamiento de
    import. Reviewer APROBADO.
  - **Slice C** (este commit): `IndexingPipeline` en nuevo módulo `index/`
    (`pipeline.py`, corpus→load→chunk→embed→upsert, DI vía Protocols),
    4 tests unitarios end-to-end con fakes. Reviewer APROBADO (puerta final
    de toda la feature).
- **Decisiones de diseño en la puerta de aprobación:** `RetrievedChunk`
  diferido a f5 → `similarity_search` devuelve `list[tuple[Chunk, float]]`;
  nuevo módulo `index/` para indexado offline (separado del path de consulta
  online `rag/`).
- **Trazabilidad:** R1–R33 cubiertos por ≥1 test entre los slices A+B+C.
- **Tests:** `./init.sh` exit 0, 105 passed + 2 skipped (ficheros de
  integración pgvector + bge_m3, sin driver / sin FlagEmbedding).
- **Nota:** el subagente `implementer` de Slice C murió (stream timeout) tras
  escribir código+tests pero antes de su report; el leader reconstruyó
  `progress/impl_f4-slice-c.md` desde el estado verificado en disco. El
  reviewer verificó el código directamente.
- **Reports:** `progress/impl_f4-slice-{a,b,c}.md`,
  `progress/review_f4-slice-{a,b,c}.md`.

---

## f5-retriever — Retriever

- **Fecha de cierre:** 2026-06-16
- **Estado final:** `done`
- **Entrega:** PR único (~≤250 líneas, por debajo del presupuesto de 400;
  el humano aprobó el spec y la entrega en un solo PR).
- **Flujo:** spec aprobado por humano → `in_progress` → `implementer` →
  `reviewer` APROBADO (sin rondas de cambios).
- **Construido:**
  - `RetrievedChunk` y `RetrievalResult` en `src/wowrag/models.py`
    (`RetrievedChunk` anidado: `chunk: Chunk` + `score`, con propiedades de
    cita `source_url`/`title`/`section` que delegan en `chunk`; sin duplicar
    campos). `RetrievalResult`: `chunks` (score desc) + `max_score` +
    `below_threshold`.
  - `Retriever` (Protocol) + `RetrieverError` (`src/wowrag/retrieval/base.py`).
  - `DefaultRetriever` (`src/wowrag/retrieval/retriever.py`): compone
    `EmbeddingProvider` + `VectorStore` por DI; query vacía / `k<=0` →
    `RetrieverError`; señal de abstención `max_score < score_threshold`
    (estricto); store vacío → `chunks=[]`, `max_score=0.0`,
    `below_threshold=True`; errores de infra propagan sin enmascarar.
  - Re-exports en `src/wowrag/retrieval/__init__.py`.
- **Frontera de alcance:** f5 SOLO expone la señal `below_threshold`. El
  mensaje de abstención, el prompt y la llamada al LLM son f6/f7/f8 (no se
  tocaron). `config.py` NO modificado — solo reutiliza `top_k` y
  `score_threshold`; se añadió el env-override test de `score_threshold` que
  faltaba (cierre de la lección f3 R10 / f4 Slice-A).
- **Trazabilidad:** R1–R23 cubiertos por ≥1 test (ver
  `progress/review_f5-retriever.md`).
- **Tests:** `./init.sh` exit 0, 135 passed + 2 skipped (30 tests nuevos;
  los 2 skipped son los ficheros de integración pgvector + bge_m3
  preexistentes).
- **Reports:** `progress/impl_f5-retriever.md`,
  `progress/review_f5-retriever.md`.

---

## f6-prompt-builder — Prompt builder: persona/style + grounding + citations

- **Fecha de cierre:** 2026-06-17
- **Estado final:** `done`
- **Entrega:** PR único (~286 líneas).
- **Flujo:** spec aprobado por humano → `in_progress` → `implementer` →
  `reviewer` APROBADO (sin rondas de cambios).
- **Construido:**
  - `Source` + `BuiltPrompt` (`system`, `user`, `sources: list[Source]`) en
    `src/wowrag/models.py`.
  - `PromptBuilder` (Protocol) + `PromptBuilderError` en
    `src/wowrag/generation/prompt_builder_base.py` (NO `generation/base.py`,
    reservado al `LLMProvider` de f7).
  - `DefaultPromptBuilder` (`src/wowrag/generation/prompt_builder.py`):
    inyecta persona/style reutilizando `load_persona`/`default_persona` de f0
    (sin redefinir), instrucciones de grounding independientes de la persona,
    formatea el contexto con marcadores de cita secuenciales y alinea
    `sources` a esos marcadores; query vacía → `PromptBuilderError`; persona
    inexistente → `PersonaNotFoundError` propagada.
  - Re-exports en `src/wowrag/generation/__init__.py`.
- **Frontera de alcance:** f6 NO llama al LLM/Ollama, NO orquesta ni emite el
  mensaje de abstención (frontera f8), NO lee `below_threshold`.
  `_NO_CONTEXT_NOTICE` es solo una indicación de ausencia de contexto para el
  LLM, no el mensaje de abstención de f8. `config.py` NO modificado.
- **Trazabilidad:** R1–R27 cubiertos por ≥1 test (ver
  `progress/review_f6-prompt-builder.md`).
- **Tests:** `./init.sh` exit 0, 165 passed + 3 skipped (20 tests nuevos:
  4 en `test_models_prompt.py` + 16 en `test_prompt_builder.py`).
- **Reports:** `progress/impl_f6-prompt-builder.md`,
  `progress/review_f6-prompt-builder.md`.

---

## f7-llm-provider-ollama — LLM provider abstraction + Ollama

- **Fecha de cierre:** 2026-06-17
- **Estado final:** `done`
- **Entrega:** PR único (~360 líneas).
- **Flujo:** spec aprobado por humano → `in_progress` → `implementer` →
  `reviewer` CHANGES_REQUESTED (R19 sin test unitario ejecutable: la rama
  `data["response"]` ausente → `LLMError` solo se cubría con un test que
  requería `pytest_localserver`, siempre skipped) → `implementer` añadió un
  test network-free con `monkeypatch` de `sys.modules["httpx"]` → `reviewer`
  APROBADO.
- **Construido:**
  - `LLMProvider` (Protocol) + `LLMError` en `src/wowrag/llm/base.py`.
  - `FakeLLMProvider` (determinista, solo-stdlib) en `src/wowrag/llm/fake.py`.
  - `OllamaLLM` con import perezoso de `httpx` (`src/wowrag/llm/ollama.py`):
    `generate(prompt) -> str` (POST `/api/generate`, `stream=false`) +
    `generate_stream() -> Iterator[str]` (NDJSON); SÍNCRONO (async diferido a
    f9); `response` ausente → `LLMError`; servidor inalcanzable → `LLMError`.
  - Re-exports en `src/wowrag/llm/__init__.py`.
  - `requirements-llm.txt` (`httpx>=0.27.0`, aislado de `init.sh`).
- **Frontera de alcance:** capa de abstracción pura; abstención/citas/
  orquestación son f8. `config.py` NO modificado (`ollama_url`/`llm_model` ya
  existían desde f0; se añadió env-override test). `models.py` NO modificado
  (`generate` devuelve `str`).
- **Trazabilidad:** R1–R21 cubiertos por ≥1 test; R19 ahora con test unitario
  ejecutable `test_generate_invalid_schema_raises_llm_error`
  (`tests/test_llm_interface.py`).
- **Tests:** `./init.sh` exit 0, 166 passed + 3 skipped. Tests de integración
  real-Ollama marcados `@pytest.mark.integration` (skipped sin Ollama vivo /
  sin `httpx`).
- **Reports:** `progress/impl_f7-llm-provider-ollama.md`,
  `progress/review_f7-llm-provider-ollama.md`.

---

## f8-rag-orchestrator — RAG orchestrator + abstention logic

- **Fecha de cierre:** 2026-06-17
- **Estado final:** `done`
- **Entrega:** PR único (~340 líneas, bajo presupuesto de 400).
- **Flujo:** spec aprobado por humano ("aprobado") → `in_progress` →
  `implementer` → `reviewer` APROBADO (sin rondas de cambios).
- **Construido:**
  - `Answer{answer, sources: list[Source], abstained, metadata}` +
    `AnswerMetadata{model, persona, max_score, scores}` en
    `src/wowrag/models.py` (consistente con `RetrievalResult` de f5 y
    `BuiltPrompt` de f6; metadata como submodelo tipado, no dict opaco).
  - `RagOrchestrator` (Protocol) + `OrchestratorError` en
    `src/wowrag/rag/base.py`; `DefaultRagOrchestrator` en
    `src/wowrag/rag/orchestrator.py`; re-exports en `src/wowrag/rag/__init__.py`.
    Método `answer(query, persona=None) -> Answer`.
  - Compone por DI `Retriever` (f5) + `PromptBuilder` (f6) + `LLMProvider`
    (f7); cero imports DB/ML/red; unit tests con fakes.
- **Lógica de abstención (f8 ES dueña del mensaje):** consume la señal
  `below_threshold` de f5 (NO recomputa el umbral), hace short-circuit ANTES
  de PromptBuilder/LLM, y devuelve `Answer(abstained=True, ...)` — nunca
  lanza. Mensaje constante:
  `"No hay evidencia suficiente en los documentos para responder con seguridad."`
  Flatten del prompt para f7: `f"{built.system}\n\n{built.user}"`.
- **Frontera de alcance:** síncrono (async/streaming → f9); sin HTTP API (f9),
  sin reranking (f12), sin scraping (f11). `config.py` NO modificado.
- **Trazabilidad:** R1–R27 cubiertos por ≥1 test ejecutable (ver
  `progress/review_f8-rag-orchestrator.md`).
- **Tests:** `./init.sh` exit 0, 187 passed + 3 skipped (21 tests nuevos de
  f8; los 3 skipped son los ficheros de integración pgvector + bge_m3 +
  real-Ollama, todos `@pytest.mark.integration`).
- **Reports:** `progress/impl_f8-rag-orchestrator.md`,
  `progress/review_f8-rag-orchestrator.md`.

---

## f9-http-api — HTTP API (FastAPI)

- **Fecha de cierre:** 2026-06-17
- **Estado final:** `done`
- **Entrega:** PR único (~360 líneas).
- **Flujo:** spec aprobado por humano ("aprobado f9") → `in_progress` →
  `implementer` → `reviewer` APROBADO (sin rondas de cambios).
- **Construido:**
  - `src/wowrag/api/`: `app.py` (`create_app()`), `routes.py` (`/ask`,
    `/health`), `schemas.py` (`AskRequest{query, persona?}`),
    `dependencies.py` (`get_orchestrator` + `build_orchestrator` perezoso),
    `__init__.py` materializado.
  - `POST /ask` reutiliza `Answer` de f8 como `response_model`; handlers
    **sync `def`** (FastAPI los corre en su threadpool; `answer` es síncrono);
    persona por request o default de config. `GET /health`.
  - CORS desde `Settings.cors_allow_origins` (campo nuevo, default `["*"]`,
    configurable por env).
  - Mapa de errores: 422 (pydantic) · 400 (`OrchestratorError`/
    `PersonaNotFoundError`) · 503 (infra: retriever/embedding/store/LLM),
    cuerpos JSON, `logger.exception`, sin stack traces filtrados.
  - DI vía `Depends(get_orchestrator)`; tests con `app.dependency_overrides` +
    fake orchestrator + `TestClient`; cero DB/ML/Ollama/red; importar la app
    no carga torch/psycopg/httpx (`build_orchestrator` perezoso).
- **Cambio de dependencias:** `fastapi`/`uvicorn`/`httpx` añadidos pineados
  (`==`) a `requirements.txt` y movidos de `DEFERRED` a `PINNED` en
  `tests/test_requirements_pinned.py` (así `TestClient` funciona en el
  `./init.sh` por defecto). `torch`/`sentence-transformers`/`psycopg` siguen
  diferidos (import perezoso).
- **Frontera de alcance:** solo expone f8 por HTTP; streaming/SSE diferido;
  sin frontend real, sin f10/f11/f12; lógica de f5–f8 intacta.
- **Trazabilidad:** R1–R25 cubiertos por ≥1 test ejecutable (ver
  `progress/review_f9-http-api.md`).
- **Tests:** `./init.sh` exit 0, **210 passed + 2 skipped + 5 deselected**.
  Los 5 deselected son los tests `@integration` de `test_llm_ollama.py` (ahora
  colectables porque `httpx` está instalado, pero excluidos por
  `-m "not integration"`; no llaman a un Ollama vivo). Los 2 skipped son los
  ficheros de integración pgvector + bge_m3.
- **Reports:** `progress/impl_f9-http-api.md`,
  `progress/review_f9-http-api.md`.

---

## f10-evaluation-harness — Evaluation harness (golden Q&A, faithfulness, abstention)

- **Fecha de cierre:** 2026-06-17
- **Estado final:** `done`
- **Entrega:** 2 slices encadenados (el humano eligió chained PRs por presupuesto):
  - **Slice A** (commit `53130c4`): paquete `src/wowrag/eval/` — `GoldenItem` +
    loader JSONL (nombra la línea ofensora en error) + fixture
    `data/golden.jsonl`; métricas hit-rate (intersección de URLs) /
    faithfulness-proxy (`0.5·citado + 0.5·overlap léxico` vs `reference_answer`,
    solo-stdlib, sin LLM) / abstención (precision/recall sobre out-of-corpus);
    runner con orquestador inyectable. Reviewer APROBADO. Reqs R1–R21/R27/R29 +
    R30 parcial.
  - **Slice B** (este commit): CLI `python -m wowrag.eval` (`--dataset`/`--out`),
    modelo `EvalReport` + artefacto JSON, composición perezosa del orquestador
    real (reutiliza `build_orchestrator` de f9), `main(argv, orchestrator=...)`
    inyectable. Reviewer APROBADO (puerta final de feature). Reqs R22–R26/R28 +
    R30 final.
- **Decisiones de diseño:** faithfulness default = proxy determinista (LLM-judge
  opcional inyectable, solo la variante real-Ollama es `@integration`); modelos
  de f10 viven en `src/wowrag/eval/` (NO en `models.py` global); sin deps nuevas
  en el path por defecto; importar `wowrag.eval`/`wowrag.eval.cli` NO carga
  torch/psycopg/httpx/Ollama (invariante de aislamiento verificado por test en
  subproceso; la composición real falla en runtime por ML ausente, no en import).
- **Frontera de alcance:** evalúa el servicio f8 con dataset golden + fakes; no
  scrapea (f11) ni reordena (f12); no cambia la lógica de f5–f9 (solo importa).
  `config.py` solo recibe un campo aditivo (`eval_dataset_path`).
- **Trazabilidad:** R1–R30 cubiertos por ≥1 test ejecutable (45 tests de f10 en
  el suite por defecto, ninguno skipped/deselected).
- **Tests:** `./init.sh` exit 0, **256 passed + 2 skipped + 5 deselected**.
- **Reports:** `progress/impl_f10-slice-{a,b}.md`,
  `progress/review_f10-slice-{a,b}.md`.

---

## f11-wowhead-ingestion — [LATER] Wowhead ingestion / scraper

- **Fecha de cierre:** 2026-06-18
- **Estado final:** `done`
- **Entrega:** 2 slices encadenados:
  - **Slice A** (commit `016148a`): `Fetcher` Protocol + `HttpxFetcher` (lazy
    httpx) + `FakeFetcher` (registra URLs pedidas); `RobotsGate` (stdlib
    `urllib.robotparser`, consultado ANTES de fetch, cache por host);
    `RateLimiter` (clock inyectable); 5 campos `scrape_*` en `config.py`.
    Reviewer APROBADO. Compliance probada: una URL disallowed por robots NUNCA
    se pide; el rate-limit se aplica con fake clock.
  - **Slice B** (este commit): `normalizer.py` (HTML→`Document` con
    `selectolax` lazy → `ScrapeError`), `pipeline.py` (fetch robots+rate-limited
    → normaliza → escribe corpus `wowhead.jsonl`, honra host allowlist +
    page cap), `cli.py`/`__main__.py` (`python -m wowrag.ingest.wowhead`,
    `main(argv, fetcher=None)` inyectable). Round-trip por `JsonlCorpusLoader`
    (R20). Reviewer CHANGES_REQUESTED → (fix) → APROBADO.
- **Change-round (decisión a destacar):** `selectolax` movido de
  `requirements-scrape.txt` a `requirements.txt` (pineado `==`,
  `DEFERRED`→`PINNED` en `test_requirements_pinned.py`), `requirements-scrape.txt`
  eliminado, guards `importorskip` removidos. **Razón:** `selectolax` es un
  parser ligero (wheels binarios, sin GPU/DB/servicio externo); aislarlo dejaba
  la lógica core de f11 (normalizer/pipeline/CLI, R12/R14/R15/R16/R29) SIN
  ejecutar en CI. Sigue el precedente de f9 (httpx/fastapi). **Es una DESVIACIÓN
  del spec aprobado** (que pedía aislarlo); documentada en `design.md`. El
  import sigue siendo perezoso (estilo defensivo, R25).
- **Handoff:** escribe corpus JSONL consumido SIN cambios por el loader de f1 +
  indexer de f4. **Desbloquea la validación end-to-end con corpus real.**
- **Frontera de alcance:** produce `Document`s en el schema de f1; no cambia
  f1–f10; no reordena (f12). Compliance (robots/rate-limit/UA identificable) es
  requisito, no opcional.
- **Trazabilidad:** R1–R31 cubiertos por ≥1 test ejecutable (R30 = live-fetch,
  `@pytest.mark.integration`).
- **Tests:** `./init.sh` exit 0, **297 passed + 2 skipped + 6 deselected**
  (1 warning preexistente de f9, third-party).
- **Seguimiento menor (no bloqueante):** `fetcher.py:40` +
  `tests/test_wowhead_fetcher.py:121` aún citan `requirements-scrape.txt`
  (eliminado) en el error-path de httpx-ausente — defensivo e inalcanzable
  (httpx está en `requirements.txt` desde f9). Alinear el hint con
  `requirements.txt` en una limpieza futura.
- **Reports:** `progress/impl_f11-slice-{a,b}.md`,
  `progress/review_f11-slice-{a,b}.md`.

---