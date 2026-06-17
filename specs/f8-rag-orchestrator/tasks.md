# Tasks — f8-rag-orchestrator

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests son unitarios con stdlib + fakes/stubs: `FakeLLMProvider`
> (f7) + stubs/spies de `Retriever`/`PromptBuilder`, o las impls reales de f5/f6
> alimentadas con `FakeEmbeddingProvider`/`FakeVectorStore` y personas YAML reales
> de f0. Sin Postgres, sin GPU, sin Ollama, sin red. La trazabilidad `R<n>` ↔ test
> es obligatoria (`docs/verification.md`); nombra o comenta cada test con su `R<n>`.
>
> **Entrega: PR único** (ver `design.md` §0). f8 es comparable a f6/f7; cabe en
> ≤ ~340 líneas, por debajo del presupuesto de 400. No se necesitan slices.
>
> `answer(query, persona=None) -> Answer`. f8 OWNS el mensaje de abstención (f5
> solo expuso la señal `below_threshold`). f8 es **síncrono** (usa `generate`, no
> `generate_stream`); streaming/async y el HTTP API son f9 — NO los implementes
> aquí. f8 CONSUME f5/f6/f7 por interfaz; NO los reimplementes.

---

## Implementación

- [x] **T1 — Modelos `Answer` y `AnswerMetadata` en `models.py`.**
  Editar `src/wowrag/models.py` para añadir (ver `design.md` §3):
  - `AnswerMetadata(BaseModel)` con `model: str`, `persona: str`,
    `max_score: float` y `scores: list[float]`.
  - `Answer(BaseModel)` con `answer: str`, `sources: list[Source]` (reutiliza el
    `Source` de f6), `abstained: bool` y `metadata: AnswerMetadata`.
  - Añadir `Answer` y `AnswerMetadata` al `__all__` de `models.py`.
  - Actualizar el docstring del módulo (que ya anticipa `Answer`) para reflejar que
    f8 lo introduce.
  _(Cubre R1, R3, R4, R5, R6, R7)_

- [x] **T2 — Interfaz `RagOrchestrator` y excepción `OrchestratorError`.**
  Crear `src/wowrag/rag/base.py` con:
  - `OrchestratorError(Exception)` — excepción de dominio (query vacía). Docstring:
    los errores de infra de capas inferiores (`RetrieverError`, `EmbeddingError`,
    `VectorStoreError`, `LLMError`, `PersonaNotFoundError`) NO se envuelven; la
    abstención es respuesta válida, no excepción.
  - `RagOrchestrator` Protocol con
    `answer(self, query: str, persona: Persona | None = None) -> Answer`.
    Docstring con el contrato: query vacía → `OrchestratorError`;
    `below_threshold=True` → abstención sin llamar a build/generate;
    `below_threshold=False` → build + generate; infra propaga.
  Importa `Answer` de `wowrag.models` y `Persona` de `wowrag.personas`.
  `from __future__ import annotations`. (Si el paquete `rag/` no existe aún, crearlo.)
  _(Cubre R8, R24)_

- [x] **T3 — Implementación `DefaultRagOrchestrator`.**
  Crear `src/wowrag/rag/orchestrator.py` con `DefaultRagOrchestrator` (ver
  `design.md` §5, §6, §7):
  - Constructor `__init__(self, retriever: Retriever, prompt_builder:
    PromptBuilder, llm: LLMProvider, settings: Settings | None = None)` — depende
    solo de interfaces (R9, R22).
  - Constante de módulo `_ABSTENTION_MESSAGE = "No hay evidencia suficiente en los
    documentos para responder con seguridad."` — propiedad de f8 (R15, R18).
  - `answer(query, persona=None) -> Answer`:
    - query vacía/solo-espacios → `OrchestratorError` ANTES de tocar
      retrieve/build/generate (R25).
    - resolver `effective_persona = persona or default_persona(self._settings)` una
      sola vez (delegando en el helper de f0); usarlo en metadata y pasarlo a
      `build` para que nombre reportado y persona usada coincidan (R5, R23).
      `PersonaNotFoundError` propaga (R26).
    - `result = retriever.retrieve(query)` (R10); dejar propagar errores de infra
      (R26).
    - `scores = [rc.score for rc in result.chunks]` (R21).
    - **Si `result.below_threshold`** → return `Answer(answer=_ABSTENTION_MESSAGE,
      sources=[], abstained=True, metadata=AnswerMetadata(model=llm.model,
      persona=effective_persona.name, max_score=result.max_score, scores=scores))`
      SIN llamar a build ni generate (R14, R15, R16, R17).
    - **Si no** → `built = prompt_builder.build(query, result, effective_persona)`
      (R11); `prompt = f"{built.system}\n\n{built.user}"` (R12);
      `text = llm.generate(prompt)` exactamente una vez (R12); `LLMError` propaga
      (R26).
    - return `Answer(answer=text, sources=built.sources, abstained=False,
      metadata=AnswerMetadata(model=llm.model, persona=effective_persona.name,
      max_score=result.max_score, scores=scores))` (R2, R3, R13, R19, R20, R4-R7).
  - Cero imports de DB/ML/red; no recalcular el umbral (consumir `below_threshold`).
  _(Cubre R2, R4, R5, R6, R7, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19,
  R20, R21, R22, R23, R25, R26)_

- [x] **T4 — Re-exportar desde `rag/__init__.py`.**
  Crear/reemplazar `src/wowrag/rag/__init__.py` con imports y `__all__` que
  exporten `RagOrchestrator`, `OrchestratorError`, `DefaultRagOrchestrator`.
  _(Cubre R27)_

---

## Tests

- [x] **T5 — `tests/test_models_answer.py`** (modelos).
  - `test_answer_fields`: `Answer(answer=.., sources=.., abstained=.., metadata=..)`
    se construye y expone los cuatro campos. _(R1)_
  - `test_answer_sources_are_source_type`: `Answer.sources` acepta y conserva una
    `list[Source]` de f6 (`{n, title, url}`). _(R3)_
  - `test_answer_metadata_fields`: `AnswerMetadata` con `model`/`persona`/
    `max_score`/`scores` se construye y expone los cuatro. _(R4, R5, R6, R7)_
  - `test_exports_models`: `from wowrag.models import Answer, AnswerMetadata`
    funciona. _(R27, parcial)_

- [x] **T6 — `tests/test_orchestrator.py`** (`DefaultRagOrchestrator`).
  Usar stubs/spies de `Retriever`/`PromptBuilder` + `FakeLLMProvider` (f7) para
  aislar; y/o las impls reales de f5/f6 con `FakeEmbeddingProvider`/`FakeVectorStore`
  + personas YAML reales para la composición. Construir `Settings(_env_file=None)`
  con overrides explícitos donde haga falta.
  - `test_empty_query_raises`: query `""`/`"   "` → `OrchestratorError`; spies
    confirman que NO se llamó a retrieve/build/generate. _(R25)_
  - `test_happy_path_returns_answer_with_citations`: `below_threshold=False` →
    `abstained is False`, `answer` == texto del LLM, `sources` ==
    `BuiltPrompt.sources`. _(R2, R13, R19, R20)_
  - `test_generate_called_once_with_combined_prompt`: `generate` recibe UN string
    que contiene tanto `built.system` como `built.user`, llamado exactamente una
    vez. _(R12)_
  - `test_metadata_model_persona_scores`: `metadata.model == llm.model` (R4),
    `metadata.persona` == persona efectiva (R5), `metadata.max_score ==
    result.max_score` (R6), `metadata.scores == [rc.score for rc in result.chunks]`
    (R7, R21). _(R4, R5, R6, R7, R21)_
  - `test_abstains_when_below_threshold`: `below_threshold=True` → `abstained is
    True`, `answer` == mensaje de abstención claro, `sources == []`; spies
    confirman que NO se llamó a build/generate. _(R14, R15, R16, R18)_
  - `test_abstention_metadata_present`: al abstener, `metadata.max_score` y
    `metadata.persona` siguen presentes (y `model`). _(R17)_
  - `test_empty_store_abstains`: con f5 real sobre store vacío
    (`below_threshold=True`, `max_score=0.0`) → f8 abstiene con `sources == []` y
    `max_score == 0.0`. _(R14, R16, R17)_
  - `test_persona_none_resolves_default`: `answer(q)` sin persona → `metadata.persona
    == Settings.default_persona` y el `PromptBuilder` recibe esa persona resuelta
    (verificable con un builder spy que registre el `persona` recibido). _(R23)_
  - `test_persona_explicit_reported`: `answer(q, persona=<orc>)` →
    `metadata.persona == "orc"`. _(R5)_
  - `test_infra_errors_propagate`: un `Retriever` stub que lanza `RetrieverError`
    (y, en otro caso, un `LLMProvider` que lanza `LLMError`) hace que `answer`
    propague la excepción, no devuelva un `Answer` vacío. _(R26)_
  - `test_depends_only_on_interfaces`: construir `DefaultRagOrchestrator` con stubs
    que solo implementan los Protocols `Retriever`/`PromptBuilder`/`LLMProvider` y
    ejecutar `answer`. _(R9, R22)_
  - `test_exports_from_package`: `from wowrag.rag import RagOrchestrator,
    OrchestratorError, DefaultRagOrchestrator` funciona. _(R27)_

---

## Cierre

- [x] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R27) tienen al menos un test.
  - `from wowrag.rag import RagOrchestrator, OrchestratorError,
    DefaultRagOrchestrator` funciona.
  - `from wowrag.models import Answer, AnswerMetadata` funciona.
  - `answer` devuelve `Answer` y, en abstención, NO llama al `PromptBuilder` ni al
    `LLMProvider` (short-circuit verificado por spy); el mensaje de abstención es
    el de f8.
  - f8 NO implementa HTTP API, NI streaming/async, NI reranking, NI scraping
    (fronteras de alcance f9/f12/f11 respetadas).
  - `config.py` NO fue modificado (f8 reutiliza f5/f6/f7, que ya consumen config).
  - No quedan imports de DB/ML/red en `rag/`; el orquestador depende solo de los
    Protocols `Retriever`/`PromptBuilder`/`LLMProvider`.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json` (salvo lo que ya hizo el spec-author: `pending` →
> `spec_ready`). El cambio a `in_progress` requiere aprobación humana; el cierre
> (`done`) lo hacen el leader / reviewer tras validar la trazabilidad `R<n>` ↔
> test. Tu trabajo termina cuando todas las tasks `[x]` y `./init.sh` pasa en verde.
