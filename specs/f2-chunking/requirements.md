# Requirements — f2-chunking

> Feature: `f2-chunking` — Chunking pipeline.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es verificable por
> al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. El **modelo de datos `Chunk`** — un fragmento de texto derivado de un
   `Document`, con metadata heredada y un `chunk_id` estable/determinista.
2. La **interfaz `Chunker`** (Protocol swappable) que transforma un `Document`
   en una secuencia de `Chunk`.
3. La **implementación `OverlapChunker`** — split por caracteres con ventana
   deslizante y solapamiento configurable.
4. Los **parámetros de configuración** (`chunk_size`, `chunk_overlap`) expuestos
   vía `pydantic-settings` en `Settings`.

### Fuera de alcance (explícito)

- Embeddings, indexado en vector store, retrieval: diferidos a f3/f4/f5.
- Chunking semántico (sentence-boundary, spaCy): diferido a una feature futura.
- Scraping/carga del corpus (f11): ya disponible a través de `f1`.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Documents split into overlapping chunks preserving metadata and a stable
> chunk id; configurable size/overlap."

| Fragmento del acceptance                          | Requisitos que lo cubren |
|---------------------------------------------------|--------------------------|
| Documents split into … chunks                     | R1, R2, R3               |
| overlapping chunks                                | R4, R5                   |
| preserving metadata                               | R6                       |
| stable chunk id                                   | R7, R8                   |
| configurable size/overlap                         | R9, R10                  |

## Requisitos

### Modelo `Chunk`

**R1** — El sistema DEBE proveer un modelo `Chunk` con los campos obligatorios
`chunk_id` (str), `text` (str), `source_url` (str), `title` (str) y `section`
(str).

**R2** — SI se intenta construir un `Chunk` con `text` vacío o solo espacios,
ENTONCES el sistema DEBE lanzar un error de validación que identifique el campo
`text`.

**R3** — El sistema DEBE proveer `Chunk` como un `pydantic.BaseModel` para
permitir serialización/deserialización JSON sin código adicional.

### Interfaz `Chunker`

**R4** — El sistema DEBE definir una interfaz `Chunker` (Protocol) con un
método que, dado un `Document`, devuelva una lista ordenada de `Chunk`.

**R5** — El sistema DEBE proveer una implementación concreta `OverlapChunker`
de `Chunker` que divida el texto del documento mediante una ventana deslizante
con tamaño y solapamiento configurables, produciendo al menos un `Chunk` por
cada `Document` cuyo `text` no esté vacío.

### Preservación de metadata

**R6** — CUANDO `OverlapChunker` divide un `Document`, el sistema DEBE copiar
los campos `source_url`, `title` y `section` del `Document` a cada `Chunk`
resultante, sin modificación.

### Chunk id estable (determinista)

**R7** — El sistema DEBE generar el `chunk_id` de cada `Chunk` de forma
determinista a partir de `source_url`, `section` y la posición del chunk dentro
del documento, de modo que procesar el mismo `Document` con los mismos
parámetros siempre produzca los mismos `chunk_id`.

**R8** — SI se procesa el mismo `Document` dos veces con los mismos parámetros,
ENTONCES el sistema DEBE producir listas de `Chunk` cuyo `chunk_id` sea
idéntico entre ejecuciones (sin depender del tiempo ni de valores aleatorios).

### Configuración via pydantic-settings

**R9** — El sistema DEBE exponer el parámetro `chunk_size` (número de
caracteres máximos por chunk, sin valor mágico) en `Settings` vía
`pydantic-settings`, permitiendo su configuración desde entorno o `.env`.

**R10** — El sistema DEBE exponer el parámetro `chunk_overlap` (número de
caracteres de solapamiento entre chunks consecutivos) en `Settings` vía
`pydantic-settings`, permitiendo su configuración desde entorno o `.env`.

### Restricciones y contratos

**R11** — SI `chunk_overlap` es mayor o igual que `chunk_size`, ENTONCES el
sistema DEBE lanzar una excepción de configuración que identifique la condición
inválida al construir el `OverlapChunker`.

**R12** — CUANDO el texto de un `Document` es más corto que `chunk_size`, el
sistema DEBE producir exactamente un `Chunk` con todo el texto del documento.

**R13** — El sistema DEBE garantizar que la concatenación lógica de los chunks
resultantes cubre todo el texto original (ningún fragmento de texto queda sin
chunkear).
