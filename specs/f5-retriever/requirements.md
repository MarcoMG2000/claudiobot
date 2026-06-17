# Requirements — f5-retriever

> Feature: `f5-retriever` — Retriever (query → embedding → top-k retrieval con
> scores y metadata; `k` y umbral de score configurables; señal de abstención).
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. El modelo **`RetrievedChunk`** en `src/wowrag/models.py` — wrapper citable de un
   hit de recuperación: el `Chunk` recuperado + su `score`, exponiendo la metadata
   de cita (`source_url`, `title`, `section`) que f6/f8 necesitan. Es el tipo de
   nivel superior que envuelve el `tuple[Chunk, float]` crudo de f4.
2. El modelo **`RetrievalResult`** en `src/wowrag/models.py` — el resultado de una
   recuperación: la lista de `RetrievedChunk` (ordenada por score descendente) más
   la **señal de abstención** (`below_threshold: bool`) y el `max_score`.
3. La **interfaz `Retriever`** (Protocol swappable) en `retrieval/base.py`: el punto
   de intercambio que toda implementación de recuperador debe satisfacer.
4. La **excepción de dominio `RetrieverError`** para entrada inválida (p. ej. query
   vacía).
5. La **implementación `Retriever` concreta** (`DefaultRetriever`) — que COMPONE,
   por inyección de dependencias, un `EmbeddingProvider` (embebe la query) y un
   `VectorStore` (`similarity_search`), aplicando el umbral de score para producir
   la señal de abstención. Testeable con `FakeEmbeddingProvider` + `FakeVectorStore`
   (sin Postgres, sin GPU, sin red).
6. La **reutilización** de los campos de configuración existentes `top_k` (k por
   defecto) y `score_threshold` (umbral de abstención) de `Settings`.

> **`RetrievedChunk` diferido de f4:** f4 dejó deliberadamente este modelo para f5
> (ver `specs/f4-vector-store-pgvector/design.md` §3 y §13). f4 devuelve la búsqueda
> cruda como `list[tuple[Chunk, float]]`; f5 introduce el wrapper citable sobre ese
> par. `models.py` SÍ se toca en f5 (añade `RetrievedChunk` y `RetrievalResult`).

### Fuera de alcance (explícito)

f5 **solo computa y EXPONE la señal de abstención**. NO produce el mensaje de
abstención, no construye prompts, no llama a ningún LLM, no genera la respuesta
final. Concretamente, queda fuera de alcance:

- **Prompt building** (formato del contexto, marcadores de cita, persona): **f6**.
- **LLM provider** (Ollama): **f7**.
- **Orquestación + mensaje de abstención + respuesta final + short-circuit del
  LLM** (cuando `below_threshold` es `true`): **f8** — f8 CONSUME la señal que f5
  expone.
- **Reranking** (reordenar top-k antes de generar): **f12**, se intercalará entre
  `retrieve` y la generación.
- **Scraping de wowhead**: **f11**.
- **HTTP API / FastAPI**: **f9**.
- Benchmarks de calidad de recuperación / hit-rate: **f10**.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Query -> embedding -> top-k retrieval with scores and metadata; configurable k
> and score threshold used for abstention signaling."

| Fragmento del acceptance                              | Requisitos que lo cubren            |
|-------------------------------------------------------|-------------------------------------|
| Query -> embedding                                    | R10, R11                            |
| top-k retrieval with scores                           | R8, R12, R13, R14                   |
| and metadata                                          | R1, R2, R3, R15                     |
| configurable k                                        | R16, R17, R18                       |
| and score threshold used for abstention signaling     | R4, R5, R6, R7, R19, R20            |

(Requisitos transversales: interfaz `Retriever` R8, R9; excepción de dominio R21,
R22; entrada inválida R10; exports R23.)

## Requisitos

### Modelo `RetrievedChunk` (hit citable)

**R1** — El sistema DEBE definir un modelo `RetrievedChunk` en
`src/wowrag/models.py` que envuelva un hit de recuperación como un campo
`chunk: Chunk` (el `Chunk` existente) más un campo `score: float`.

**R2** — El sistema DEBE que `RetrievedChunk` exponga, mediante propiedades de solo
lectura, la metadata de cita `source_url`, `title` y `section` delegando en su
`chunk`, de modo que f6/f8 puedan construir citas sin desempaquetar el `Chunk`.

**R3** — El sistema DEBE que `RetrievedChunk` conserve el `score` (float) tal cual
lo devuelve `VectorStore.similarity_search` (coseno; mayor = más similar), sin
recalcularlo ni normalizarlo.

### Modelo `RetrievalResult` (resultado + señal de abstención)

**R4** — El sistema DEBE definir un modelo `RetrievalResult` en
`src/wowrag/models.py` con al menos los campos `chunks: list[RetrievedChunk]`
(ordenados por score descendente), `max_score: float` y `below_threshold: bool`.

**R5** — El sistema DEBE que, en un `RetrievalResult` con al menos un chunk,
`max_score` sea igual al `score` del primer (mejor) `RetrievedChunk` de `chunks`.

**R6** — CUANDO la recuperación produce al menos un chunk y `max_score` es menor
que el umbral configurado, el sistema DEBE poner `below_threshold = true` en el
`RetrievalResult`.

**R7** — CUANDO la recuperación produce al menos un chunk y `max_score` es mayor o
igual que el umbral configurado, el sistema DEBE poner `below_threshold = false`
en el `RetrievalResult`.

### Interfaz `Retriever`

**R8** — El sistema DEBE definir una interfaz `Retriever` (Protocol) en
`src/wowrag/retrieval/base.py` con un método
`retrieve(query: str, k: int | None = None) -> RetrievalResult`, como único punto
de intercambio para las implementaciones de recuperador.

**R9** — El sistema DEBE que toda implementación de `Retriever` dependa solo de las
interfaces `EmbeddingProvider` y `VectorStore` (no de implementaciones concretas),
de modo que sea construible e invocable en tests con `FakeEmbeddingProvider` +
`FakeVectorStore`, sin Postgres ni GPU.

### Entrada de query y embedding

**R10** — SI `retrieve` recibe una `query` vacía o compuesta solo de espacios en
blanco, ENTONCES el sistema DEBE lanzar `RetrieverError` sin llamar al
`EmbeddingProvider` ni al `VectorStore`.

**R11** — CUANDO `retrieve` recibe una `query` no vacía, el sistema DEBE embeber
esa query en exactamente un vector llamando a `EmbeddingProvider.embed` con una
lista de un solo elemento, y usar ese vector para la búsqueda.

### Top-k retrieval con scores y metadata

**R12** — CUANDO `retrieve` ejecuta la búsqueda, el sistema DEBE llamar a
`VectorStore.similarity_search(query_vector, k)` y envolver cada par
`(Chunk, float)` devuelto en un `RetrievedChunk` con el mismo `chunk` y `score`.

**R13** — El sistema DEBE que `RetrievalResult.chunks` preserve el orden por score
descendente (mejor primero) que `similarity_search` ya garantiza, sin reordenar.

**R14** — El sistema DEBE que `RetrievalResult.chunks` contenga como mucho `k`
elementos (el mismo límite que aplica `similarity_search`).

**R15** — El sistema DEBE que cada `RetrievedChunk` de `RetrievalResult.chunks`
conserve la metadata de cita (`source_url`, `title`, `section`) del `Chunk`
recuperado.

### `k` configurable

**R16** — CUANDO `retrieve` se llama sin `k` (o con `k = None`), el sistema DEBE
usar `Settings.top_k` como valor por defecto de `k`.

**R17** — CUANDO `retrieve` se llama con un `k` explícito (entero positivo), el
sistema DEBE usar ese `k`, ignorando `Settings.top_k`.

**R18** — SI `retrieve` recibe un `k` explícito menor o igual que cero, ENTONCES
el sistema DEBE lanzar `RetrieverError` sin llamar al `VectorStore`.

### Umbral de score configurable → señal de abstención

**R19** — El sistema DEBE usar `Settings.score_threshold` como umbral por defecto
para computar `below_threshold`, comparando `max_score < score_threshold`.

**R20** — CUANDO la recuperación devuelve cero chunks (almacén vacío o sin hits),
el sistema DEBE producir un `RetrievalResult` con `chunks = []`, `max_score = 0.0`
y `below_threshold = true` (sin evidencia ⇒ señal de abstención activa), sin lanzar
excepción.

### Excepción de dominio

**R21** — El sistema DEBE definir una excepción de dominio
`RetrieverError(Exception)` en `src/wowrag/retrieval/base.py` para los fallos de
entrada del recuperador (query vacía, `k` no positivo).

**R22** — El sistema DEBE NO enmascarar errores de infraestructura propagados por
las capas inferiores: si `EmbeddingProvider` lanza `EmbeddingError` o `VectorStore`
lanza `VectorStoreError`, el `Retriever` DEBE dejar propagar esa excepción tal cual
(no convertirla en un `RetrievalResult` vacío ni silenciarla).

### Exports del paquete

**R23** — El sistema DEBE re-exportar `Retriever`, `RetrieverError` y la
implementación concreta desde `src/wowrag/retrieval/__init__.py`, y re-exportar
`RetrievedChunk` y `RetrievalResult` desde `src/wowrag/models.py` (vía su `__all__`
si existe), de modo que los consumidores dependan del paquete/módulo de modelos, no
de los módulos internos.
