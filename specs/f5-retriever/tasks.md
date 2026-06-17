# Tasks — f5-retriever

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests son unitarios con stdlib + fakes (`FakeEmbeddingProvider`
> de f3, `FakeVectorStore` de f4); sin Postgres, sin GPU, sin red. La trazabilidad
> `R<n>` ↔ test es obligatoria (`docs/verification.md`); nombra o comenta cada test
> con su `R<n>`.
>
> **Entrega: PR único** (ver `design.md` §0 y §10). f5 es más pequeña que f4; cabe
> en ≤ ~250 líneas, por debajo del presupuesto de 400. No se necesitan slices.
>
> `retrieve(query, k=None) -> RetrievalResult`. f5 SOLO computa y EXPONE la señal de
> abstención (`below_threshold`). El mensaje de abstención, el prompt y la llamada
> al LLM son f6/f7/f8 — NO los implementes aquí.

---

## Implementación

- [x] **T1 — Modelos `RetrievedChunk` y `RetrievalResult` en `models.py`.**
  Editar `src/wowrag/models.py` para añadir:
  - `RetrievedChunk(BaseModel)` con `chunk: Chunk` y `score: float`, más
    propiedades de solo lectura `source_url`, `title`, `section` que delegan en
    `self.chunk`. NO duplicar los campos de `Chunk` (modelo anidado, ver
    `design.md` §3).
  - `RetrievalResult(BaseModel)` con `chunks: list[RetrievedChunk]`,
    `max_score: float` y `below_threshold: bool`.
  - Si `models.py` gana/usa `__all__`, incluir ambos modelos.
  _(Cubre R1, R2, R3, R4, R5, R15)_

- [x] **T2 — Interfaz `Retriever` y excepción `RetrieverError`.**
  Crear `src/wowrag/retrieval/base.py` con:
  - `RetrieverError(Exception)` — excepción de dominio (query vacía, k no positivo).
  - `Retriever` Protocol con
    `retrieve(self, query: str, k: int | None = None) -> RetrievalResult`.
    Docstring con el contrato: k=None → `Settings.top_k`; query vacía o k≤0 →
    `RetrieverError`; errores de infra (Embedding/Store) NO se envuelven.
  Importa `RetrievalResult` de `wowrag.models`. `from __future__ import annotations`.
  _(Cubre R8, R21)_

- [x] **T3 — Implementación `DefaultRetriever`.**
  Crear `src/wowrag/retrieval/retriever.py` con `DefaultRetriever` (ver `design.md`
  §5):
  - Constructor `__init__(self, embedder: EmbeddingProvider, store: VectorStore,
    settings: Settings | None = None)` — depende solo de interfaces (R9).
  - `retrieve(query, k=None) -> RetrievalResult`:
    - query vacía/solo-espacios → `RetrieverError` ANTES de tocar embed/store (R10).
    - resolver `k`: `Settings.top_k` si `k is None`, si no el `k` dado (R16, R17);
      `k <= 0` → `RetrieverError` sin tocar el store (R18).
    - embeber la query en 1 vector: `embedder.embed([query])[0]` (R11).
    - `store.similarity_search(vector, resolved_k)` → pares `(Chunk, float)` (R12);
      dejar propagar `EmbeddingError`/`VectorStoreError` (R22).
    - envolver cada par en `RetrievedChunk(chunk=c, score=s)` preservando el orden
      score-desc (R12, R13, R15); `len(chunks) <= k` (R14).
    - `max_score = chunks[0].score if chunks else 0.0` (R5, R20).
    - `below_threshold = max_score < settings.score_threshold` (R6, R7, R19); store
      vacío → `chunks=[]`, `max_score=0.0`, `below_threshold=True` (R20).
  - Cero imports de DB/ML/red.
  _(Cubre R9, R10, R11, R12, R13, R14, R16, R17, R18, R19, R20, R22)_

- [x] **T4 — Re-exportar desde `retrieval/__init__.py`.**
  Reemplazar el placeholder de `src/wowrag/retrieval/__init__.py` con imports y
  `__all__` que exporten `Retriever`, `RetrieverError`, `DefaultRetriever`.
  _(Cubre R23)_

---

## Tests

- [x] **T5 — `tests/test_models_retrieval.py`** (modelos).
  - `test_retrievedchunk_wraps_chunk_and_score`: `RetrievedChunk(chunk=c, score=s)`
    guarda `chunk` y `score`. _(R1)_
  - `test_retrievedchunk_exposes_citation_metadata`: `.source_url`, `.title`,
    `.section` devuelven los del `chunk`. _(R2)_
  - `test_retrievedchunk_preserves_score`: `score` se conserva sin recalcular
    (mismo float que se pasó). _(R3)_
  - `test_retrievalresult_fields`: `RetrievalResult` con `chunks`, `max_score`,
    `below_threshold` se construye y expone los tres. _(R4)_
  - `test_max_score_equals_best_chunk_score`: con ≥1 chunk, `max_score` == score del
    primer (mejor) `RetrievedChunk`. _(R5)_
  - `test_result_chunks_carry_metadata`: cada `RetrievedChunk` de `chunks` conserva
    `source_url`/`title`/`section`. _(R15)_

- [x] **T6 — `tests/test_retriever.py`** (`DefaultRetriever` con fakes).
  Usar `FakeEmbeddingProvider` (f3) + `FakeVectorStore` (f4); poblar el store con
  chunks + vectores conocidos vía `upsert`. Construir `DefaultRetriever` con un
  `Settings(_env_file=None)` o `Settings` con overrides explícitos.
  - `test_empty_query_raises`: query `""`/`"   "` → `RetrieverError`; verificar que
    NO se llamó a embed/store (spy o fake que registre llamadas). _(R10)_
  - `test_embeds_query_as_single_vector`: `embed` recibe una lista de longitud 1.
    _(R11)_
  - `test_wraps_pairs_into_retrieved_chunks`: el resultado envuelve cada par
    `(Chunk, float)` en `RetrievedChunk` con orden score-desc. _(R12, R13)_
  - `test_results_carry_metadata`: cada `RetrievedChunk` conserva
    `source_url`/`title`/`section`. _(R15)_
  - `test_respects_k_limit`: con M > k filas, `retrieve(q, k)` devuelve ≤ k chunks.
    _(R14)_
  - `test_k_none_uses_top_k`: `retrieve(q)` (sin k) usa `Settings.top_k`. _(R16)_
  - `test_explicit_k_overrides_top_k`: `retrieve(q, k=2)` usa 2, no `top_k`. _(R17)_
  - `test_non_positive_k_raises`: `retrieve(q, k=0)` y `k=-1` → `RetrieverError` sin
    tocar el store. _(R18)_
  - `test_below_threshold_true_when_max_score_low`: con `score_threshold` alto (p. ej.
    0.99) y hits de score menor, `below_threshold is True`. _(R6, R19)_
  - `test_below_threshold_false_when_max_score_high`: con `score_threshold` bajo y
    al menos un hit por encima, `below_threshold is False`; el límite `==` no
    abstiene. _(R7)_
  - `test_empty_store_signals_abstention`: store vacío → `chunks == []`,
    `max_score == 0.0`, `below_threshold is True`, sin excepción. _(R20)_
  - `test_infra_errors_propagate`: un fake de store que lanza `VectorStoreError`
    (y/o un embedder que lanza `EmbeddingError`) hace que `retrieve` propague la
    excepción, no devuelva un resultado vacío. _(R22)_
  - `test_retriever_depends_only_on_interfaces`: construir `DefaultRetriever` con
    stubs que solo implementan los Protocols `EmbeddingProvider`/`VectorStore` y
    ejecutar `retrieve`. _(R9)_
  - `test_exports_from_package`:
    `from wowrag.retrieval import Retriever, RetrieverError, DefaultRetriever`
    funciona. _(R23)_

- [x] **T7 — `tests/test_config.py`** (editar — cerrar el hueco f3/f4).
  Añadir `test_score_threshold_overridable_from_env`: `monkeypatch.setenv`
  `SCORE_THRESHOLD` (p. ej. `"0.5"`) → `Settings(_env_file=None).score_threshold ==
  0.5`. (El default-assert de `score_threshold` ya existe en `EXPECTED_DEFAULTS`;
  solo falta el env-override — ver `design.md` §6.)
  _(Cubre R19, cierre de la lección f3 R10 / f4 Slice-A)_

---

## Cierre

- [x] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R23) tienen al menos un test.
  - `from wowrag.retrieval import Retriever, RetrieverError, DefaultRetriever`
    funciona.
  - `from wowrag.models import RetrievedChunk, RetrievalResult` funciona.
  - `retrieve` devuelve `RetrievalResult` y NO produce mensaje de abstención, ni
    prompt, ni llamada al LLM (frontera de alcance f6/f7/f8 respetada).
  - `config.py` NO fue modificado (solo se reutilizan `top_k` y `score_threshold`);
    el env-override test de `score_threshold` está presente y verde.
  - No quedan imports de DB/ML/red en `retrieval/`.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json`. El cambio de estado y el cierre los hacen el leader /
> reviewer tras validar la trazabilidad `R<n>` ↔ test. Tu trabajo termina cuando
> todas las tasks `[x]` y `./init.sh` pasa en verde.
