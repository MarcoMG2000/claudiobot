# Tasks — f12-reranking

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests unitarios usan stdlib + fakes/stubs (sin ML, sin Postgres,
> sin red): `FakeCrossEncoderReranker` + stubs de `Retriever`/`PromptBuilder` +
> `FakeLLMProvider` (f7). El test `@integration` usa `CrossEncoderReranker` real
> y se omite en CI (`-m "not integration"`). La trazabilidad `R<n>` ↔ test es
> obligatoria (`docs/verification.md`); nombra o comenta cada test con su `R<n>`.
>
> **Entrega: PR único** (ver `design.md` §0). f12 cabe en ~365 líneas, por debajo
> del presupuesto de 400. No se necesitan slices.
>
> `Reranker.rerank(query, chunks, top_n) -> RerankResult`. f12 añade una capa
> opcional entre f5 y f6/f8. NO reimplementes el retriever, el prompt builder ni el
> orquestador desde cero — edita solo lo necesario. NO escribas el endpoint HTTP.

---

## Implementación

- [ ] **T1 — Modelo `RerankResult` en `models.py`.**
  Editar `src/wowrag/models.py` para añadir (ver `design.md` §3):
  - `RerankResult(BaseModel)` con `chunks: list[RetrievedChunk]`, `top_n: int`
    y `reranker_model: str | None`.
  - Añadir `RerankResult` al `__all__` de `models.py`.
  - Actualizar el docstring del módulo para reflejar que f12 introduce `RerankResult`.
  _(Cubre R3, R4, R5)_

- [ ] **T2 — Interfaz `Reranker` y tres implementaciones en `retrieval/reranker.py`.**
  Crear `src/wowrag/retrieval/reranker.py` con (ver `design.md` §4):
  - `from __future__ import annotations` en la cabecera.
  - `Reranker` Protocol con método
    `rerank(self, query: str, chunks: list[RetrievedChunk], top_n: int | None = None) -> RerankResult`.
    Docstring: empty chunks → devuelve `RerankResult(chunks=[], top_n=0, ...)`; top_n > len → devuelve todos; infra errors propagan.
  - `PassthroughReranker`: devuelve chunks en el orden original, truncando a
    `min(top_n, len(chunks))` si `top_n` no es `None`; `reranker_model=None`.
  - `CrossEncoderReranker(model_name: str)`: lazy-load del `CrossEncoder` de
    `sentence_transformers` en el primer `rerank`; puntúa pares `(query, chunk.chunk.text)`;
    ordena por score descendente; trunca a `top_n` efectivo; `reranker_model=model_name`;
    empty chunks → `RerankResult(chunks=[], top_n=0, reranker_model=model_name)`.
  - `FakeCrossEncoderReranker`: invierte el orden, trunca a `top_n` efectivo;
    `reranker_model="fake"`; cero imports ML.
  _(Cubre R1, R2, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R26, R27)_

- [ ] **T3 — Re-exportar desde `retrieval/__init__.py`.**
  Editar `src/wowrag/retrieval/__init__.py` para añadir imports y actualizar
  `__all__` con: `Reranker`, `PassthroughReranker`, `CrossEncoderReranker`,
  `FakeCrossEncoderReranker`.
  _(Cubre R28)_

- [ ] **T4 — Tres campos de configuración en `config.py`.**
  Editar `src/wowrag/config.py` para añadir en `Settings` (ver `design.md` §6):
  - `reranker_enabled: bool = False`
  - `reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"`
  - `reranker_top_n: int = 3`
  Con comentario que identifica estos campos como pertenecientes a f12.
  _(Cubre R16, R17, R18)_

- [ ] **T5 — Integrar el reranker en `DefaultRagOrchestrator`.**
  Editar `src/wowrag/rag/orchestrator.py` (ver `design.md` §5):
  - Añadir `reranker: Reranker | None = None` como último parámetro de
    `__init__` (después de `settings`). Guardar en `self._reranker`.
  - En `answer()`, justo después de obtener el `RetrievalResult` y comprobar
    `below_threshold`, cuando `below_threshold=False` y `self._reranker is not None`:
    1. Llamar a `self._reranker.rerank(query, result.chunks, top_n=self._settings.reranker_top_n)`.
    2. Construir un `RetrievalResult` temporal con `chunks=rerank_result.chunks`,
       `max_score=result.max_score`, `below_threshold=result.below_threshold`.
    3. Pasar ese resultado al `PromptBuilder` en lugar del resultado original.
  - Cuando `below_threshold=True` o `self._reranker is None`, el flujo es idéntico
    al actual (sin tocar nada más).
  - Los tests existentes de f8 deben seguir pasando sin modificación.
  _(Cubre R19, R20, R21, R22, R23)_

---

## Tests

- [ ] **T6 — `tests/test_reranker.py`** (unitarios — sin ML).

  ### PassthroughReranker
  - `test_passthrough_preserves_order`: dado `[c1, c2, c3]`, `rerank` devuelve los
    tres en el mismo orden. _(R6)_
  - `test_passthrough_reranker_model_is_none`: `RerankResult.reranker_model == None`.
    _(R7)_
  - `test_passthrough_truncates_to_top_n`: con `top_n=2` y 3 chunks, devuelve los 2
    primeros en orden original. _(R8)_
  - `test_passthrough_top_n_exceeds_chunks`: con `top_n=10` y 3 chunks, devuelve los
    3 chunks (no hay padding). _(R5)_
  - `test_passthrough_empty_chunks`: `chunks=[]` → `RerankResult(chunks=[], top_n=0)`.
    _(R26)_

  ### FakeCrossEncoderReranker
  - `test_fake_reverses_order`: dado `[c1, c2, c3]`, `rerank` devuelve
    `[c3, c2, c1]`. _(R13)_
  - `test_fake_reranker_model_is_fake`: `RerankResult.reranker_model == "fake"`. _(R15)_
  - `test_fake_truncates_to_top_n`: con `top_n=2` y 3 chunks, devuelve los 2
    primeros del orden invertido. _(R4, R13)_
  - `test_fake_no_ml_imports`: importar `FakeCrossEncoderReranker` no importa
    `sentence_transformers` (verificar que `sys.modules` no contiene el paquete
    tras el import). _(R14)_
  - `test_fake_empty_chunks`: `chunks=[]` → `RerankResult(chunks=[], top_n=0)`.
    _(R26)_

  ### Integración del reranker en DefaultRagOrchestrator
  - `test_orchestrator_without_reranker_unchanged`: construir
    `DefaultRagOrchestrator(retriever, prompt_builder, llm)` sin `reranker`,
    llamar a `answer()` con `below_threshold=False`, verificar que el prompt builder
    recibe `result.chunks` en el orden original del retriever. _(R22)_
  - `test_orchestrator_with_fake_reranker_uses_reranked_order`:
    `FakeCrossEncoderReranker` + 3 chunks, verificar que el prompt builder recibe
    los chunks en orden invertido. _(R20)_
  - `test_orchestrator_reranker_not_called_on_abstention`: con
    `below_threshold=True`, verificar mediante spy que `reranker.rerank` NO fue
    llamado. _(R21)_
  - `test_orchestrator_answer_contract_unchanged`: con reranker activo, el `Answer`
    devuelto sigue teniendo exactamente los campos `{answer, sources, abstained,
    metadata}` sin campos nuevos. _(R23)_
  - `test_orchestrator_reranker_top_n_passed`: verificar que `reranker.rerank` se
    llama con `top_n=settings.reranker_top_n`. _(R20)_

  ### Modelos
  - `test_rerank_result_fields`: `RerankResult(chunks=[...], top_n=2,
    reranker_model="test")` se construye y expone los tres campos. _(R3)_
  - `test_exports_reranker_from_retrieval_package`: `from wowrag.retrieval import
    Reranker, PassthroughReranker, CrossEncoderReranker, FakeCrossEncoderReranker`
    funciona sin instanciar nada. _(R28)_
  - `test_exports_rerank_result_from_models`: `from wowrag.models import RerankResult`
    funciona. _(R28)_

- [ ] **T7 — Test de integración en `tests/test_reranker.py`** (con ML real).
  - `test_cross_encoder_reranks_correctly` marcado con `@pytest.mark.integration`:
    - Construir `CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")`.
    - Crear 3 `RetrievedChunk` con textos relevantes e irrelevantes para una query
      conocida.
    - Llamar a `rerank(query, chunks, top_n=2)`.
    - Verificar que el chunk más relevante queda primero y `len(result.chunks) == 2`.
    - Verificar `result.reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"`.
    _(R9, R10, R11, R12, R25)_

---

## Cierre

- [ ] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R28) tienen al menos un test.
  - `from wowrag.retrieval import Reranker, PassthroughReranker, CrossEncoderReranker,
    FakeCrossEncoderReranker` funciona.
  - `from wowrag.models import RerankResult` funciona.
  - Los tests existentes de f8 (`test_orchestrator.py`) siguen pasando sin modificación.
  - `DefaultRagOrchestrator` construido sin `reranker` se comporta exactamente igual
    que antes (retrocompatibilidad R19).
  - `FakeCrossEncoderReranker` no importa `sentence_transformers`.
  - `config.py` tiene los tres nuevos campos con defaults correctos.
  - No quedan imports de ML en paths que se ejecuten en la suite unitaria.
  _(Verificación integral; no añade requirements nuevos)_

- [ ] **Z2 — Actualizar `feature-list.json`.**
  Cambiar `"status": "in_progress"` → `"status": "done"` para `f12-reranking`.
  _(Cierre de la feature; solo lo hace el implementer tras pasar la revisión)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni ejecutes Z2
> hasta que el reviewer confirme que todas las tasks `[x]` están verificadas y
> `./init.sh` pasa en verde. El cambio a `in_progress` requiere aprobación humana
> (el spec-author ya hizo `pending` → `spec_ready`); el cierre (`done`) lo hacen el
> leader / reviewer tras validar la trazabilidad `R<n>` ↔ test. Tu trabajo termina
> cuando todas las tasks `[x]` y `./init.sh` pasan en verde.
