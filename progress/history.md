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