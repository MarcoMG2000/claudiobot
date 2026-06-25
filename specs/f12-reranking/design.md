# Design — f12-reranking

> CÓMO se construye la capa de reranking. Respeta el layout de
> `docs/architecture.md` §6 (`src/wowrag/retrieval/`) y las convenciones del
> proyecto: interfaz en su propio módulo, implementaciones concretas en el mismo
> archivo, excepción de dominio, `from __future__ import annotations`, dependencia
> SOLO de interfaces (Protocols). Sigue el patrón ya establecido en f3
> (`EmbeddingProvider`), f4 (`VectorStore`), f5 (`Retriever`) y f8
> (`RagOrchestrator`). Se integra en f8 por inyección de dependencias sin romper
> ningún contrato existente.

## 0. Decisión de entrega: PR único (~≤ 380 líneas)

f12 es comparable en tamaño a f5/f6: 1 interfaz Protocol, 3 implementaciones
(passtrthrough, real, fake), 1 modelo pydantic, 2 campos nuevos de config, 1 edición
en `DefaultRagOrchestrator` (añadir parámetro opcional + una rama en `answer`), y
los tests unitarios + 1 test de integración marcado. No hay migración SQL ni servicio
vivo en CI. La fase de apply **cabe holgadamente en un PR único dentro del presupuesto
de ~400 líneas**.

Estimación de líneas cambiadas (apply):

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `models.py` (`RerankResult` + `__all__`) | ~25 |
| `retrieval/reranker.py` (interfaz + 3 impls) | ~105 |
| `retrieval/__init__.py` (re-exports) | ~10 |
| `config.py` (3 campos nuevos) | ~15 |
| `rag/orchestrator.py` (parámetro + 1 rama) | ~20 |
| `tests/test_reranker.py` (unitarios + integration) | ~190 |
| **Total estimado** | **~365 líneas** — por debajo de 400. |

**Recomendación: PR único.** No se necesitan slices encadenados.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py                      # EDITAR — añadir RerankResult (+ __all__)
    config.py                      # EDITAR — añadir reranker_enabled, reranker_model, reranker_top_n
    retrieval/
      reranker.py                  # NUEVO — Reranker (Protocol) + PassthroughReranker
                                   #         + CrossEncoderReranker + FakeCrossEncoderReranker
      __init__.py                  # EDITAR — re-exportar Reranker, PassthroughReranker,
                                   #         CrossEncoderReranker, FakeCrossEncoderReranker
    rag/
      orchestrator.py              # EDITAR — añadir reranker: Reranker | None = None
                                   #         + integración en answer()
tests/
  test_reranker.py                 # NUEVO — unitarios (sin ML) + @integration (con ML)
```

Notas:
- `reranker.py` vive en `src/wowrag/retrieval/` porque el reranking es parte de la
  **capa de recuperación** (actúa sobre `RetrievedChunk`s antes de la generación), no
  de la capa de generación. Mantiene los módulos de recuperación cohesivos.
- `models.py` SÍ se edita en f12: añade `RerankResult`. Sigue el patrón de f5
  (`RetrievalResult`) y f8 (`Answer`).
- `config.py` SÍ se edita: 3 campos opcionales con defaults sensatos. No rompe
  nada — todos tienen defaults.
- `rag/orchestrator.py` SÍ se edita: un parámetro opcional `reranker` en
  `__init__` y ~10 líneas en `answer()`. No se toca `rag/base.py` (el Protocol
  `RagOrchestrator` no cambia de firma: `answer(query, persona) -> Answer`).

## 2. Ubicación del módulo: `src/wowrag/retrieval/reranker.py`

Decisión: el reranker vive en **`src/wowrag/retrieval/`**, no en `generation/` ni en
un paquete propio.

Justificación:
- El reranker opera sobre `RetrievedChunk`s (el tipo de salida del `Retriever`):
  es parte de la capa de recuperación extendida, no de la generación.
- `docs/architecture.md` §3 sitúa el reranking entre `retriever (top-k + score)` y
  `prompt builder`. Estar en `retrieval/` lo alinea con esa capa.
- Añadir un paquete propio (`reranking/`) para 1 interfaz + 3 implementaciones es
  sobre-ingeniería; sigue el patrón de `retrieval/base.py` + `retrieval/retriever.py`.
- Los consumidores (`DefaultRagOrchestrator` en `rag/`) importan desde
  `wowrag.retrieval.reranker` o desde `wowrag.retrieval` (re-export), coherente con
  cómo ya importa el `Retriever`.

## 3. Modelo `RerankResult` (R3–R5)

`RerankResult` vive en `src/wowrag/models.py`, junto a `RetrievalResult`,
`RetrievedChunk`, `Answer`, etc.

```python
class RerankResult(BaseModel):
    """Resultado de una operación de reranking (f12).

    chunks: lista de RetrievedChunk en el orden producido por el reranker
            (puede diferir del orden de score-desc del retriever).
    top_n: número efectivo de chunks devueltos (len(chunks)).
    reranker_model: identificador del modelo usado; None para PassthroughReranker.
    """

    chunks: list[RetrievedChunk]
    top_n: int
    reranker_model: str | None
```

Decisión: `RerankResult` es un modelo de datos independiente (no subclase de
`RetrievalResult`) porque su semántica es diferente: `RetrievalResult` incluye
la señal `below_threshold` (decisión de abstención); `RerankResult` es solo una
lista reordenada. Combinarlos confundiría las responsabilidades.

## 4. Interfaz `Reranker` y sus tres implementaciones

Todas en `src/wowrag/retrieval/reranker.py`.

### 4.1 Interfaz `Reranker` (R1, R2)

```python
from __future__ import annotations
from typing import Protocol
from wowrag.models import RerankResult, RetrievedChunk


class Reranker(Protocol):
    """Swap point: (query, chunks, top_n) -> RerankResult.

    PassthroughReranker: no-op, default when reranking is disabled.
    CrossEncoderReranker: reorders using a cross-encoder model (sentence-transformers).
    FakeCrossEncoderReranker: deterministic inversion for unit tests.

    Contract:
    - Empty chunks -> RerankResult(chunks=[], top_n=0, reranker_model=...).
    - top_n=None -> return all chunks (or a sensible default).
    - top_n > len(chunks) -> return all chunks (no padding).
    - Infrastructure errors from the ML model propagate as-is.
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        ...
```

### 4.2 `PassthroughReranker` (R6, R7, R8)

```python
class PassthroughReranker:
    """No-op reranker: returns chunks in their original order at zero cost.

    Used as the default when reranker_enabled=False (R6). Satisfies the
    Reranker Protocol (duck-typing). reranker_model=None signals that no
    scoring was performed (R7).
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        effective = chunks[:top_n] if top_n is not None else chunks  # R8
        return RerankResult(
            chunks=effective,
            top_n=len(effective),
            reranker_model=None,
        )
```

### 4.3 `CrossEncoderReranker` (R9–R12, R26, R27)

```python
class CrossEncoderReranker:
    """Reranker using a sentence-transformers CrossEncoder.

    Lazy-loads the model on first call (R11) so the module can be imported
    without triggering ML weight loading. Requires sentence-transformers
    (requirements-ml.txt). Infrastructure errors from the model propagate (R27).
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # lazy load (R11)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder  # lazy import (R11)
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        if not chunks:  # R26
            return RerankResult(chunks=[], top_n=0, reranker_model=self._model_name)
        model = self._get_model()
        pairs = [(query, c.chunk.text) for c in chunks]
        scores = model.predict(pairs)  # may raise — propagates (R27)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        effective_n = min(top_n, len(chunks)) if top_n is not None else len(chunks)
        top_chunks = [c for _, c in ranked[:effective_n]]
        return RerankResult(
            chunks=top_chunks,
            top_n=len(top_chunks),
            reranker_model=self._model_name,  # R12
        )
```

### 4.4 `FakeCrossEncoderReranker` (R13–R15)

```python
class FakeCrossEncoderReranker:
    """Deterministic test double: reverses the chunk order.

    Inverts the retriever's score-desc order so tests can assert that the
    orchestrator respects the reranker's output, not the retriever's (R13).
    Zero ML dependencies (R14). reranker_model="fake" (R15).
    """

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> RerankResult:
        reversed_chunks = list(reversed(chunks))
        effective_n = min(top_n, len(chunks)) if top_n is not None else len(chunks)
        result_chunks = reversed_chunks[:effective_n]
        return RerankResult(
            chunks=result_chunks,
            top_n=len(result_chunks),
            reranker_model="fake",  # R15
        )
```

## 5. Integración en `DefaultRagOrchestrator` (R19–R23)

### Decisión: parámetro opcional `reranker` en el constructor

El orquestador existente recibe sus dependencias por inyección en `__init__`. Se
añade un cuarto parámetro opcional:

```python
def __init__(
    self,
    retriever: Retriever,
    prompt_builder: PromptBuilder,
    llm: LLMProvider,
    settings: Settings | None = None,
    reranker: Reranker | None = None,   # NUEVO (R19)
) -> None:
    ...
    self._reranker = reranker  # None -> sin reranking
```

Esto es retrocompatible: todos los tests y el código de f8/f9 que construyen
`DefaultRagOrchestrator` sin `reranker` siguen funcionando sin cambios (R19).

### Rama de reranking en `answer()` (R20–R22)

La inserción ocurre justo después de obtener el `RetrievalResult` y ANTES de llamar
al `PromptBuilder`. Pseudocódigo del flujo modificado:

```
answer(query, persona)
  │
  ├─ query vacía → OrchestratorError                          (existente)
  │
  ├─ result = retriever.retrieve(query)                       (existente, R10 f8)
  │
  ├─ ¿result.below_threshold?
  │     │
  │     ├─ SÍ → abstención (R21: NO se llama al reranker)    (existente + R21)
  │     │
  │     └─ NO → ¿self._reranker is not None?                 (R20, R22)
  │               │
  │               ├─ SÍ → rerank_result = reranker.rerank(
  │               │          query, result.chunks,
  │               │          top_n=settings.reranker_top_n)
  │               │        chunks_for_prompt = rerank_result.chunks
  │               │
  │               └─ NO → chunks_for_prompt = result.chunks
  │
  ├─ built = prompt_builder.build(query,
  │            result_with_reranked_chunks,    # ver nota abajo
  │            effective_persona)
  │
  └─ … (generate, Answer) sin cambios                        (existente)
```

**Nota sobre el tipo que recibe `PromptBuilder.build`:** `PromptBuilder.build`
toma un `RetrievalResult`. El `PromptBuilder` existente usa `result.chunks` para
construir el contexto. Para pasar los chunks rerankeados sin romper la firma de f6,
se construye un `RetrievalResult` temporal con los chunks sustituidos:

```python
from dataclasses import replace  # o construir un nuevo RetrievalResult
effective_result = RetrievalResult(
    chunks=rerank_result.chunks,
    max_score=result.max_score,         # preservar el max_score original
    below_threshold=result.below_threshold,
)
```

Esto mantiene la firma `build(query, result: RetrievalResult, persona)` intacta y
no introduce un nuevo tipo en la interfaz de `PromptBuilder` (contrato f6 sin
cambios).

### Contrato `Answer` sin cambios (R23)

El `Answer` devuelto sigue siendo `{answer, sources, abstained, metadata}`. La
metadata (`max_score`, `scores`) se sigue derivando del `RetrievalResult` original
de f5 (scores del embedding, no del cross-encoder), para no mezclar las dos métricas
de similaridad. Si en el futuro se quiere exponer los scores del reranker, eso es
una feature separada.

## 6. Configuración nueva en `Settings` (R16–R18)

Tres campos nuevos en `src/wowrag/config.py`, todos con defaults seguros que no
activan el reranker por defecto:

```python
# Reranking (f12). Campos opcionales con defaults desactivados:
reranker_enabled: bool = False                              # R16
reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # R17
reranker_top_n: int = 3                                    # R18
```

`reranker_enabled` en `False` por defecto garantiza que f8/f9 no se rompen aunque
`sentence-transformers` no esté instalado. La app solo construye un
`CrossEncoderReranker` si `reranker_enabled=True`; en caso contrario, el
`DefaultRagOrchestrator` se construye con `reranker=None`.

La factory de composición (a implementar en f9 / `api/dependencies.py` si aplica)
es la responsable de leer `settings.reranker_enabled` y pasar el reranker adecuado
al orquestador. f12 no impone dónde ocurre esa composición — el spec solo define las
piezas; la orquestación ocurre en el único punto de composición del proyecto.

## 7. Diagrama ASCII del flujo completo

```
               (online, query path)

 pregunta
    │
    ▼
 embeddings
    │
    ▼
 Retriever.retrieve(query, k)
    │  RetrievalResult(chunks=[...], max_score, below_threshold)
    ▼
 ¿below_threshold?
    ├─ SÍ ──────────────────────────────────────────► abstención (Answer)
    │
    └─ NO
         │
         ▼
      Reranker.rerank(query, chunks, top_n)      ← f12 (opcional)
         │  RerankResult(chunks=[reordenados], top_n, reranker_model)
         │  (si reranker=None → passtrthrough implícito)
         ▼
      PromptBuilder.build(query, result*, persona)
         │  * result con chunks sustituidos por reranked
         │  BuiltPrompt(system, user, sources)
         ▼
      LLMProvider.generate(prompt)
         │  texto
         ▼
      Answer(answer, sources, abstained=False, metadata)
```

## 8. Estrategia de tests

Todos los tests unitarios son DB-free / GPU-free / network-free; corren con `init.sh`
(`not integration`). El test `@integration` solo corre con `sentence-transformers`
instalado y el modelo descargado.

- `tests/test_reranker.py` — tests del módulo `reranker.py`:
  - **Unitarios** (`PassthroughReranker`, `FakeCrossEncoderReranker`):
    - Sin imports ML; sin Postgres; sin red.
    - Verifican contrato de la interfaz (R4, R5, R6, R7, R8, R13, R14, R15, R26).
  - **Unitarios** (integración del reranker en `DefaultRagOrchestrator`):
    - Usan `FakeCrossEncoderReranker` + stub de `Retriever` + stub de
      `PromptBuilder` + `FakeLLMProvider`.
    - Verifican R19, R20, R21, R22, R23.
  - **Integration** (`CrossEncoderReranker` real):
    - Marcado con `@pytest.mark.integration`.
    - Omitido por defecto en `init.sh` (`-m "not integration"`).
    - Verifica R9, R10, R11, R12, R25.

## 9. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| `reranker.py` en un paquete propio `reranking/` | Sobre-ingeniería para 1 interfaz + 3 impls; el patrón existente es un módulo en la capa de recuperación |
| Reranker como segundo Protocol en `retrieval/base.py` | `base.py` ya tiene `Retriever` + `RetrieverError`; mezclar dos interfaces diferentes en un solo archivo reduce la legibilidad y rompe el patrón "1 interfaz por archivo" |
| Pasar `RerankResult` directamente a `PromptBuilder` | `PromptBuilder.build` toma `RetrievalResult` (contrato f6 estable); crear un `RetrievalResult` temporal preserva la firma sin fork de f6 |
| Exponer `reranker_scores` en `Answer.metadata` | Las puntuaciones del cross-encoder tienen una escala diferente a los scores de embedding; mezclarlas en la misma metadata sin documentarlo bien confunde; se difiere a una feature posterior |
| Inicializar `CrossEncoder` en el constructor | Cargar pesos ML en el constructor de un objeto impide importar el módulo sin la dependencia; lazy load (R11) permite que el módulo exista aunque `sentence-transformers` no esté instalado |
| `ABC` en lugar de `Protocol` para `Reranker` | Inconsistente con `Retriever`/`PromptBuilder`/`LLMProvider` (todos Protocol); Protocol permite duck-typing y es el estándar del proyecto |
| `reranker_top_n` igual a `top_k` (vinculado dinámicamente) | Confunde dos configuraciones con propósito diferente; un campo separado con default razonable (3) da más control al operador |
| Modificar `RagOrchestrator` Protocol en `rag/base.py` | El contrato público `answer(query, persona) -> Answer` no cambia; solo cambia el constructor de la implementación concreta; modificar el Protocol sería un cambio de API innecesario |
