# Requirements — f3-embeddings-provider

> Feature: `f3-embeddings-provider` — Embeddings provider (abstraction + bge-m3).
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es verificable por
> al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. La **interfaz `EmbeddingProvider`** (Protocol swappable) que convierte una
   lista de textos en una lista de vectores de dimensión fija.
2. La **implementación `BgeM3Embeddings`** — bge-m3 multilingual via
   `FlagEmbedding` con importación lazy y aislamiento de la dependencia pesada.
3. El **`FakeEmbeddingProvider`** — implementación determinista sin dependencias
   ML, usable en todos los tests unitarios (f3 y futuros f4/f5).
4. Los **parámetros de configuración** (`embedding_model`, `embedding_dim`,
   `embedding_batch_size`, `embedding_device`) expuestos vía `pydantic-settings`.

### Fuera de alcance (explícito)

- Indexado en vector store / pgvector: diferido a f4.
- Reranking: diferido a f12.
- Scraping de wowhead: diferido a f11.
- Tests de rendimiento o benchmarks de calidad de embeddings.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "EmbeddingProvider interface with a bge-m3 implementation; batch embedding;
> deterministic dimension; unit-testable via a fake provider."

| Fragmento del acceptance                          | Requisitos que lo cubren |
|---------------------------------------------------|--------------------------|
| EmbeddingProvider interface                       | R1, R2, R3               |
| bge-m3 implementation                             | R7, R8, R9, R10          |
| batch embedding                                   | R4, R5                   |
| deterministic dimension                           | R6, R11                  |
| unit-testable via a fake provider                 | R12, R13, R14            |

## Requisitos

### Interfaz `EmbeddingProvider`

**R1** — El sistema DEBE definir una interfaz `EmbeddingProvider` (Protocol) con
un método `embed(texts: list[str]) -> list[list[float]]` que, dada una lista de
textos no vacíos, devuelva una lista de vectores de punto flotante con la misma
longitud que la entrada.

**R2** — El sistema DEBE definir en `EmbeddingProvider` una propiedad
`dimension: int` de solo lectura que devuelva la dimensionalidad fija del espacio
de embedding del proveedor concreto.

**R3** — CUANDO se llama a `embed` con una lista vacía (`texts = []`), el sistema
DEBE devolver una lista vacía sin lanzar excepción.

### Batch embedding

**R4** — CUANDO se llama a `embed` con una lista de N textos (N ≥ 1), el sistema
DEBE devolver exactamente N vectores en el mismo orden que los textos de entrada.

**R5** — El sistema DEBE soportar listas de entrada de cualquier longitud ≥ 1,
procesando internamente en lotes (batches) de tamaño configurable para no agotar
la memoria de la GPU.

### Dimensión determinista y consistente

**R6** — El sistema DEBE garantizar que todos los vectores devueltos por una
misma instancia de `EmbeddingProvider` tienen exactamente `dimension` elementos
de tipo `float`.

**R7** — CUANDO se llama a `embed` con el mismo texto dos veces en la misma
instancia, el sistema DEBE devolver vectores cuya diferencia L2 sea cero
(reproducibilidad dentro de la sesión).

### Implementación `BgeM3Embeddings`

**R8** — El sistema DEBE proveer una implementación concreta `BgeM3Embeddings`
de `EmbeddingProvider` que utilice el modelo `BAAI/bge-m3` vía `FlagEmbedding`
para producir embeddings densos (`dense_vecs`).

**R9** — El sistema DEBE realizar la importación de `FlagEmbedding` (y de
`torch`/`sentence-transformers` transitivamente) **dentro del método o
constructor** de `BgeM3Embeddings`, no a nivel de módulo, de modo que el módulo
`bge_m3.py` sea importable sin tener `FlagEmbedding` instalado.

**R10** — El sistema DEBE exponer `embedding_model` (nombre del modelo HuggingFace),
`embedding_batch_size` (int, tamaño de batch para `FlagEmbedding`) y
`embedding_device` (str, p. ej. `"cpu"`, `"cuda"`) como campos de `Settings` en
`src/wowrag/config.py`, configurables desde entorno o `.env`.

**R11** — El sistema DEBE que `BgeM3Embeddings.dimension` devuelva
`Settings.embedding_dim` (valor por defecto: 1024) sin depender de cargar el
modelo en memoria para consultar la dimensión.

### `FakeEmbeddingProvider`

**R12** — El sistema DEBE proveer una implementación `FakeEmbeddingProvider` de
`EmbeddingProvider` que no importe `torch`, `FlagEmbedding` ni
`sentence-transformers`, instalable y usable sin GPU ni ML libs.

**R13** — CUANDO se llama a `FakeEmbeddingProvider.embed` con el mismo texto
dos veces (en la misma instancia o entre instancias con la misma semilla), el
sistema DEBE devolver vectores idénticos (determinismo por hash del texto).

**R14** — El sistema DEBE que `FakeEmbeddingProvider.dimension` sea configurable
en su constructor (por defecto: 1024) y que todos los vectores que devuelva
tengan exactamente esa dimensión.

### Excepción de dominio

**R15** — SI se intenta construir `BgeM3Embeddings` con `embedding_device` igual
a `"cuda"` pero CUDA no está disponible en el sistema, ENTONCES el sistema DEBE
lanzar una excepción `EmbeddingError` con un mensaje que identifique la condición.

**R16** — SI `embed` recibe un texto vacío o compuesto solo de espacios en blanco
en la lista de entrada, ENTONCES el sistema DEBE lanzar `EmbeddingError`
identificando la posición del texto inválido.

### Configuración vía pydantic-settings

**R17** — El sistema DEBE que el campo `embedding_dim: int = 1024` existente en
`Settings` sea el único source of truth para la dimensión de los embeddings
producidos por `BgeM3Embeddings` y `FakeEmbeddingProvider` cuando se crean desde
la configuración.

### Exports del paquete

**R18** — El sistema DEBE re-exportar `EmbeddingProvider`, `EmbeddingError`,
`FakeEmbeddingProvider` y `BgeM3Embeddings` desde `src/wowrag/embeddings/__init__.py`
de modo que los consumidores de la capa `embeddings` dependan del paquete, no de
los módulos internos.
