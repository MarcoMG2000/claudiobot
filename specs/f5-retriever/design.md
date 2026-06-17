# Design — f5-retriever

> CÓMO se construye la capa de recuperación (online query path). Respeta el layout
> de `docs/architecture.md` §6 (`src/wowrag/retrieval/`) y las convenciones del
> proyecto: interfaz en `base.py`, implementación concreta aparte, excepción de
> dominio, `from __future__ import annotations`, dependencia solo de interfaces.
> Sigue el patrón establecido en f3 (`EmbeddingProvider`) y f4 (`VectorStore`).

## 0. Decisión de entrega: PR único (~≤ 250 líneas)

f5 es **más pequeña que f4**: 2 modelos pydantic (`RetrievedChunk`,
`RetrievalResult`), 1 interfaz + excepción, 1 implementación que solo compone dos
dependencias inyectadas, exports y sus tests unitarios. **No hay driver pesado, ni
migración SQL, ni servicios reales** (los tests usan los fakes de f3/f4). La fase de
apply **cabe holgadamente en un PR único dentro del presupuesto de ~400 líneas**.

**Recomendación: PR único.** No se necesitan slices encadenados.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py                  # EDITAR — añadir RetrievedChunk y RetrievalResult
    retrieval/
      __init__.py              # EDITAR — re-exportar Retriever, RetrieverError, DefaultRetriever
      base.py                  # NUEVO — Retriever (Protocol) + RetrieverError
      retriever.py             # NUEVO — DefaultRetriever (compone Embedding + Store)
tests/
  test_models_retrieval.py     # NUEVO — RetrievedChunk + RetrievalResult (modelos)
  test_retriever.py            # NUEVO — DefaultRetriever con fakes (flujo + abstención)
  test_config.py               # EDITAR — añadir env-override test de score_threshold
```

Notas:
- `src/wowrag/retrieval/__init__.py` ya existe como placeholder (f0); se reemplaza
  con los re-exports reales (R23).
- `retrieval/retriever.py` ya está previsto en `docs/architecture.md` §6
  (`retrieval/retriever.py`). Aquí se le añade `base.py` para la interfaz (mismo
  patrón `base.py` que `embeddings/` y `store/`).
- `models.py` SÍ se edita en f5 (a diferencia de f4): añade `RetrievedChunk` y
  `RetrievalResult`. El docstring de `models.py` ya anticipa `RetrievedChunk`.
- **`config.py` NO se edita.** `top_k` y `score_threshold` YA existen en `Settings`
  (ver §6). f5 solo los **reutiliza** (R16, R19).

## 2. Ubicación del módulo: `src/wowrag/retrieval/` (nuevo paquete, online)

Decisión: el recuperador vive en **`src/wowrag/retrieval/`**, NO en `rag/`.

Justificación según `docs/architecture.md` §3 y §6:
- El diagrama de flujo §3 sitúa el **retriever** como un paso propio del camino
  **online** (`pregunta → embeddings → retriever (top-k + score) → prompt builder`),
  separado de la **orquestación** (`rag/orchestrator.py`, f8) que une retrieve →
  prompt → LLM → abstención/respuesta.
- §6 reserva `retrieval/retriever.py` para esta capa y `rag/orchestrator.py` para la
  orquestación. Meter el recuperador en `rag/` mezclaría la capa de recuperación con
  la de orquestación; el revisor rechaza mezcla de capas.
- **Espacio para f12 (reranking):** el reranker se intercalará entre `retrieve` y la
  generación. Un módulo `retrieval/` dedicado deja sitio limpio para un futuro
  `retrieval/reranker.py` sin tocar `rag/`. (f5 NO implementa reranking.)

## 3. Modelos: `RetrievedChunk` (nested) y `RetrievalResult` (R1–R7, R15)

### Decisión: `RetrievedChunk` ANIDADO (`chunk: Chunk` + `score`), no plano

Se elige el modelo **anidado** (`chunk: Chunk` + `score: float` + propiedades de
cita que delegan en `chunk`) frente al **plano** (duplicar `chunk_id`, `text`,
`source_url`, `title`, `section` + `score`).

Razones:
- **Una sola fuente de verdad.** El plano duplicaría los 5 campos de `Chunk`; un
  cambio futuro en `Chunk` exigiría mantener dos lugares y arriesga divergencia. El
  anidado deriva del `Chunk` que f4 ya transporta intacto.
- **Sin pérdida de información.** El `Chunk` recuperado ya trae `chunk_id`, `text`,
  `source_url`, `title`, `section` (f4 R18). Anidarlo conserva todo, incluido el
  `chunk_id` (útil para reranking f12 y dedup).
- **Mapeo trivial del contrato de f4.** `similarity_search` devuelve
  `tuple[Chunk, float]`; `RetrievedChunk(chunk=chunk, score=score)` es el envoltorio
  directo del par, sin desempaquetar campos.
- **Citas cómodas.** Las propiedades `source_url`, `title`, `section` delegan en
  `chunk`, así f6/f8 acceden a la metadata de cita sin tocar el `Chunk` interno
  (cumple el formato de cita de `docs/conventions.md`).

```python
class RetrievedChunk(BaseModel):
    """Un hit de recuperación citable: el Chunk recuperado + su score de coseno.

    Wrapper de nivel superior sobre el par (Chunk, float) de
    VectorStore.similarity_search. Expone la metadata de cita delegando en chunk.
    """

    chunk: Chunk
    score: float

    @property
    def source_url(self) -> str:  # R2
        return self.chunk.source_url

    @property
    def title(self) -> str:  # R2
        return self.chunk.title

    @property
    def section(self) -> str:  # R2
        return self.chunk.section
```

### `RetrievalResult`: lista + señal de abstención (decisión sobre el shape de retorno)

`retrieve()` devuelve un **`RetrievalResult`** (objeto), no `list[RetrievedChunk]`
suelto. Razón: la señal de abstención (`below_threshold`) y el `max_score` tienen
que viajar JUNTO a los chunks como un valor de retorno cohesionado para que f8 los
consuma sin recalcular; modelarlo como objeto (no como tupla suelta) es coherente
con `docs/conventions.md` ("la abstención es una respuesta válida, modélala en el
tipo de retorno, no con `raise`"). f8 leerá `below_threshold` para hacer el
short-circuit del LLM y producir el mensaje de abstención.

```python
class RetrievalResult(BaseModel):
    """Resultado de una recuperación: chunks (score desc) + señal de abstención.

    f5 SOLO computa y EXPONE below_threshold. El mensaje de abstención, el prompt
    y la llamada al LLM viven en f6/f7/f8, que CONSUMEN esta señal.
    """

    chunks: list[RetrievedChunk]   # ordenados por score desc (R4, R13)
    max_score: float               # score del mejor chunk, o 0.0 si vacío (R5, R20)
    below_threshold: bool          # True si max_score < score_threshold (R6, R7, R20)
```

> **Señal vs mensaje (frontera de alcance, crítica).** `below_threshold` es la
> **señal**. f5 NO produce el mensaje "No hay evidencia suficiente…" (eso es f8),
> NO construye prompt (f6), NO llama al LLM (f7). f5 se detiene en exponer el bool.

## 4. Interfaz `Retriever` y excepción (R8, R9, R21)

`src/wowrag/retrieval/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from wowrag.models import RetrievalResult


class RetrieverError(Exception):
    """Domain exception for retriever input failures.

    Raised for an empty/whitespace query or a non-positive explicit k.
    Infrastructure errors from the embedding/store layers are NOT wrapped:
    they propagate as EmbeddingError / VectorStoreError (R22).
    """


class Retriever(Protocol):
    """Swap point: query -> embedding -> top-k -> RetrievalResult con señal.

    Implementación concreta: DefaultRetriever (compone EmbeddingProvider +
    VectorStore). Callers depend on this Protocol, never on a concrete impl.
    """

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        """Recupera los top-k chunks para una query y computa la señal de abstención.

        k=None -> usa Settings.top_k. Query vacía o k<=0 -> RetrieverError.
        """
        ...
```

## 5. Implementación `DefaultRetriever` (R9–R20, R22)

`src/wowrag/retrieval/retriever.py` — compone por inyección de dependencias; sin
imports de DB/ML/red. Resolución de `k` y del umbral desde `Settings`.

```python
from __future__ import annotations

from wowrag.config import Settings
from wowrag.embeddings.base import EmbeddingProvider
from wowrag.models import RetrievalResult, RetrievedChunk
from wowrag.retrieval.base import RetrieverError
from wowrag.store.base import VectorStore


class DefaultRetriever:
    """Retriever que compone un EmbeddingProvider y un VectorStore.

    Depende solo de las interfaces (R9): testeable con FakeEmbeddingProvider +
    FakeVectorStore, sin Postgres ni GPU.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._settings = settings or Settings()

    def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        if not query or not query.strip():
            raise RetrieverError("query must be a non-empty string")  # R10
        resolved_k = self._settings.top_k if k is None else k  # R16, R17
        if resolved_k <= 0:
            raise RetrieverError(f"k must be positive, got {resolved_k}")  # R18

        # R11: embed la query en exactamente un vector (lista de 1 elemento).
        query_vector = self._embedder.embed([query])[0]

        # R12: búsqueda cruda -> pares (Chunk, float). Errores de infra propagan (R22).
        hits = self._store.similarity_search(query_vector, resolved_k)

        # R12/R13/R15: envuelve cada par preservando orden score-desc y metadata.
        chunks = [RetrievedChunk(chunk=c, score=s) for c, s in hits]

        threshold = self._settings.score_threshold  # R19
        max_score = chunks[0].score if chunks else 0.0  # R5, R20
        below_threshold = max_score < threshold  # R6, R7, R20

        return RetrievalResult(
            chunks=chunks,
            max_score=max_score,
            below_threshold=below_threshold,
        )
```

Contrato de la implementación:
- Validación de entrada ANTES de tocar dependencias (R10, R18): query vacía y
  `k <= 0` lanzan `RetrieverError` sin llamar a `embed`/`similarity_search`.
- Resolución de `k`: explícito gana sobre `top_k` (R16, R17).
- Un solo vector embebido por query (R11).
- Wrapping fiel del par `(Chunk, float)`, orden preservado (R12, R13, R15).
- Señal de abstención: `max_score < score_threshold` (R6, R7, R19); store vacío ⇒
  `max_score = 0.0`, `below_threshold = True` (R20).
- Errores de infraestructura (`EmbeddingError`, `VectorStoreError`) se dejan
  propagar (R22), nunca se enmascaran como resultado vacío.

> **Por qué `score_threshold` por defecto = 0.30** (campo ya existente en
> `Settings`): con vectores coseno unit-normalizados (f3 produce norma unitaria, f4
> usa coseno), un score de 1.0 es coincidencia perfecta y 0.0 es ortogonalidad. Un
> umbral de 0.30 abstiene cuando ni siquiera el mejor hit guarda una similitud
> coseno moderada con la query — un punto de partida prudente y sintonizable por
> entorno (`SCORE_THRESHOLD`). f10 (eval harness) lo calibrará con datos dorados;
> f5 solo lo consume como default razonable.

## 6. Configuración: reutiliza `top_k` y `score_threshold` (R16, R19) — sin nuevos campos

`config.py` **NO se modifica en f5.** Ambos campos YA existen en `Settings`
(`src/wowrag/config.py`):

```python
top_k: int = 5
score_threshold: float = 0.30
```

- `top_k` → valor por defecto de `k` en `retrieve` (R16).
- `score_threshold` → umbral para `below_threshold` (R19).

> **Lección f3 R10 / f4 Slice-A (no repetir el hueco).** La regla del proyecto:
> todo campo de `Settings` usado por una feature debe tener test de **default-assert
> + env-override**. Estado actual de la cobertura:
> - `top_k`: default-assert ✅ (`EXPECTED_DEFAULTS`) + env-override ✅
>   (`test_env_var_overrides_default` usa `TOP_K`). Cubierto.
> - `score_threshold`: default-assert ✅ (`EXPECTED_DEFAULTS` tiene `0.30`) pero
>   **env-override ❌ falta**.
>
> Por eso f5 NO añade campos nuevos, pero SÍ añade el test de **env-override de
> `score_threshold`** (`SCORE_THRESHOLD`) que falta, cerrando el hueco para el campo
> que esta feature consume. Ver `tasks.md` (T7).

## 7. Semántica de score y comparación de umbral

- `VectorStore.similarity_search` ya devuelve pares ordenados por **score coseno
  descendente** (f4 R9, R10): el primer elemento es el mejor (mayor = más similar).
- f5 **no recalcula** scores; `RetrievedChunk.score` es el coseno tal cual (R3).
- `max_score` = score del primer chunk (mejor); 0.0 si no hay chunks (R5, R20).
- Comparación de abstención: **`max_score < score_threshold` ⇒ abstener
  (`below_threshold = True`)**. El caso límite `max_score == score_threshold` NO
  abstiene (`<` estricto, R7), comportamiento determinista y testeable.
- Consistente con f3 (vectores unit-norm) + f4 (coseno `<=>`): el rango efectivo de
  scores es coseno, así que el umbral 0.30 es interpretable directamente.

## 8. Exports del paquete `retrieval` y de `models` (R23)

`src/wowrag/retrieval/__init__.py` — reemplazar el placeholder:

```python
from wowrag.retrieval.base import Retriever, RetrieverError
from wowrag.retrieval.retriever import DefaultRetriever

__all__ = ["Retriever", "RetrieverError", "DefaultRetriever"]
```

`RetrievedChunk` y `RetrievalResult` se exponen desde `wowrag.models` (importables
como `from wowrag.models import RetrievedChunk, RetrievalResult`). Si `models.py`
gana un `__all__`, incluir ambos.

## 9. Estrategia de tests (todos DB-free / GPU-free; corren con `init.sh`)

Los tests usan `FakeEmbeddingProvider` (f3) + `FakeVectorStore` (f4); sin Postgres,
sin GPU, sin red. Trazabilidad `R<n>` ↔ test obligatoria (comenta cada test con su
`R<n>`).

- `tests/test_models_retrieval.py` (modelos):
  - `RetrievedChunk(chunk=.., score=..)` expone `source_url`/`title`/`section` desde
    el chunk (R1, R2); conserva `score` sin recalcular (R3).
  - `RetrievalResult` con campos `chunks`/`max_score`/`below_threshold` (R4);
    `max_score` == score del primer chunk (R5).
- `tests/test_retriever.py` (`DefaultRetriever` con fakes):
  - query vacía / solo-espacios → `RetrieverError`, sin llamar a embed/store (R10).
  - query no vacía → `embed` recibe lista de 1 elemento (R11) — verificable con un
    spy/fake que registre los argumentos.
  - resultado envuelve cada par en `RetrievedChunk` con orden score-desc y metadata
    (R12, R13, R15).
  - `len(chunks) <= k` (R14); `k=None` usa `top_k` (R16); `k` explícito gana (R17);
    `k <= 0` → `RetrieverError` sin tocar store (R18).
  - `below_threshold` True cuando `max_score < score_threshold` (R6, R19) y False
    cuando `>=` (R7); caso límite `==` no abstiene.
  - store vacío → `chunks == []`, `max_score == 0.0`, `below_threshold == True`,
    sin excepción (R20).
  - `VectorStoreError`/`EmbeddingError` de las capas inferiores se propagan, no se
    enmascaran (R22) — inyectar un fake que lance.
  - `DefaultRetriever` solo depende de los Protocols (R9): construible con
    fakes/stubs que solo implementan `EmbeddingProvider`/`VectorStore`.
  - `from wowrag.retrieval import Retriever, RetrieverError, DefaultRetriever`
    funciona (R23).
- `tests/test_config.py` (editar): `test_score_threshold_overridable_from_env`
  (`SCORE_THRESHOLD` → `Settings.score_threshold`) (R19, cierre del hueco f3/f4).

## 10. Estimación de carga de revisión (review-workload)

Apply estimado: 2 modelos pequeños + interfaz + excepción + 1 clase de composición
(~30 líneas de lógica) + exports + 2 ficheros de test. **Cabe en un PR único de
≤ ~250 líneas, por debajo del presupuesto de 400.** No se recomiendan slices.

## 11. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| `RetrievedChunk` **plano** (duplica los 5 campos de `Chunk` + score) | Duplica la fuente de verdad de `Chunk`; un cambio en `Chunk` exige mantener dos sitios y arriesga divergencia. El anidado conserva todo (incl. `chunk_id`) sin duplicar |
| `retrieve` devuelve `list[RetrievedChunk]` suelto + flag aparte | La señal de abstención y `max_score` quedarían desacoplados de los chunks; f8 tendría que recalcular o recibir varios valores. `RetrievalResult` los cohesiona en un retorno (convención: abstención modelada en el tipo de retorno) |
| f5 produce el mensaje de abstención / llama al LLM | Fuera de alcance: mensaje + short-circuit del LLM son f8; prompt es f6; LLM es f7. f5 solo EXPONE la señal `below_threshold` |
| Recuperador en `rag/` | `rag/` es la orquestación online (retrieve→prompt→LLM, f8); el recuperador es un paso previo. Mezclar capas; el revisor lo rechaza (`architecture.md` §3, §6) |
| Añadir un nuevo campo de config para el umbral | `score_threshold` ya existe en `Settings`; añadir otro duplicaría la fuente de verdad. Se reutiliza (R19) |
| Re-embeber/recalcular score en el retriever | `similarity_search` ya devuelve el coseno ordenado (f4 R9, R10); recalcular duplicaría lógica y arriesga inconsistencia con la real. El retriever solo envuelve (R3, R13) |
| Enmascarar `VectorStoreError`/`EmbeddingError` como `RetrievalResult` vacío | Oculta fallos de infraestructura como "sin evidencia"; `docs/conventions.md` exige que los errores de infra sean excepciones claras, no respuestas vacías (R22) |
| `ABC` en lugar de `Protocol` para `Retriever` | Inconsistente con `EmbeddingProvider`/`VectorStore` (Protocol); Protocol no exige herencia y permite duck-typing en tests |
| Reranking dentro de f5 | Diferido a f12; se intercalará entre retrieve y generación. El módulo `retrieval/` deja sitio para `reranker.py` sin acoplarlo ahora |
