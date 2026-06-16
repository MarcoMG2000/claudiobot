# Requirements — f4-vector-store-pgvector

> Feature: `f4-vector-store-pgvector` — Vector store (abstraction + pgvector) and
> indexing.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. La **interfaz `VectorStore`** (Protocol swappable) en `store/base.py`: el punto
   de intercambio que toda implementación de almacén vectorial debe satisfacer
   (inicialización de esquema/migración, `upsert`, `similarity_search`).
2. El **`VectorStoreError`** — excepción de dominio del almacén vectorial.
3. El **`FakeVectorStore`** — implementación in-memory, solo stdlib, con
   similitud coseno, usable en todos los tests unitarios (f4, f5) sin Postgres.
4. La **implementación `PgVectorStore`** — respaldada por PostgreSQL + pgvector,
   con migración de esquema, e import lazy del driver (aislamiento de la
   dependencia pesada, igual espíritu que f3 con `FlagEmbedding`).
5. El **pipeline de indexado** (`IndexingPipeline`) — camino end-to-end
   corpus → load → chunk → embed → upsert, compuesto por interfaces.
6. Los **parámetros de configuración** nuevos en `Settings` (nombre de tabla,
   métrica de distancia), reutilizando `postgres_dsn`, `embedding_dim` y `top_k`
   ya existentes.

> **Diferido a f5:** el modelo `RetrievedChunk` (wrapper citable de chunk +
> score) NO forma parte de f4. f4 devuelve resultados de búsqueda como
> `list[tuple[Chunk, float]]` (par `(chunk, score)`); f5 introducirá el wrapper
> `RetrievedChunk` sobre ese par. Por eso el retorno en tupla es el **contrato
> mínimo deliberado** de f4. `models.py` queda **intacto** en esta feature.

### Fuera de alcance (explícito)

- **Retriever** (query → embedding → top-k → umbral → señal de abstención):
  diferido a **f5**. f4 expone `similarity_search` cruda; la lógica de umbral y
  abstención NO vive aquí.
- **Reranking**: diferido a **f12**.
- **Scraping de wowhead**: diferido a **f11**; f4 indexa el corpus local existente.
- **HTTP API / FastAPI**: diferido a **f9**.
- Benchmarks de rendimiento o calidad de recuperación (parte de **f10**).

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "VectorStore interface; pgvector-backed implementation with schema migration;
> upsert chunks+embeddings+metadata; similarity search; indexing pipeline that
> ingests a corpus end-to-end."

| Fragmento del acceptance                                | Requisitos que lo cubren        |
|---------------------------------------------------------|---------------------------------|
| VectorStore interface                                   | R1, R2, R3, R4, R5              |
| pgvector-backed implementation with schema migration    | R12, R13, R14, R15, R16, R17    |
| upsert chunks+embeddings+metadata                       | R6, R7, R8, R18                 |
| similarity search                                       | R9, R10, R11, R19               |
| indexing pipeline that ingests a corpus end-to-end      | R20, R21, R22, R23              |

(Requisitos transversales: excepción de dominio R24–R25; `FakeVectorStore`
R26–R29; configuración R30–R32; exports R33.)

## Requisitos

### Interfaz `VectorStore`

**R1** — El sistema DEBE definir una interfaz `VectorStore` (Protocol) en
`src/wowrag/store/base.py` que sirva como único punto de intercambio para las
implementaciones de almacén vectorial.

**R2** — El sistema DEBE definir en `VectorStore` un método
`ensure_schema() -> None` que prepare el esquema (tabla, columna vector,
índice) de forma idempotente, sin error si el esquema ya existe.

**R3** — El sistema DEBE definir en `VectorStore` un método
`upsert(chunks: list[Chunk], embeddings: list[list[float]]) -> int` que
almacene cada chunk junto con su vector y su metadata, devolviendo el número de
filas insertadas o actualizadas.

**R4** — El sistema DEBE definir en `VectorStore` un método
`similarity_search(query_vector: list[float], k: int) -> list[tuple[Chunk, float]]`
que devuelva los `k` chunks más similares al vector de consulta, cada uno como un
par `(chunk, score)` usando el modelo `Chunk` existente de `src/wowrag/models.py`.

**R5** — El sistema DEBE definir en `VectorStore` una propiedad de solo lectura
`dimension: int` que devuelva la dimensión esperada de los vectores que el
almacén acepta y devuelve.

### `upsert` (chunks + embeddings + metadata)

**R6** — CUANDO se llama a `upsert` con `chunks` y `embeddings` de la misma
longitud N (N ≥ 1), el sistema DEBE almacenar exactamente N entradas, cada una
emparejando el chunk i-ésimo con el vector i-ésimo en el mismo orden.

**R7** — SI se llama a `upsert` con `len(chunks) != len(embeddings)`, ENTONCES
el sistema DEBE lanzar `VectorStoreError` identificando ambas longitudes, sin
almacenar ninguna entrada parcial.

**R8** — CUANDO se llama a `upsert` con un chunk cuyo `chunk_id` ya existe en el
almacén, el sistema DEBE reemplazar (upsert) su texto, vector y metadata en
lugar de crear un duplicado, de modo que el `chunk_id` permanezca único.

**R18** — El sistema DEBE persistir, para cada chunk, su `chunk_id`, `text`,
`source_url`, `title` y `section`, de modo que el `Chunk` devuelto en cada par
`(Chunk, float)` de `similarity_search` conserve esa metadata para construir
citas aguas abajo.

### `similarity_search`

**R9** — CUANDO se llama a `similarity_search(query_vector, k)` con un almacén
no vacío, el sistema DEBE devolver una lista de como mucho `k` pares
`(Chunk, float)`, ordenada de mayor a menor similitud (mejor primero, score
descendente).

**R10** — El sistema DEBE usar **similitud coseno** como métrica de relevancia, y
DEBE devolver en cada par el `score` (segundo elemento, `float`) como valor de
coseno donde un valor mayor significa mayor similitud.

**R11** — CUANDO se llama a `similarity_search` sobre un almacén vacío, el
sistema DEBE devolver una lista vacía sin lanzar excepción.

**R19** — SI `similarity_search` recibe un `query_vector` cuya longitud no
coincide con `dimension`, ENTONCES el sistema DEBE lanzar `VectorStoreError`
identificando la dimensión esperada y la recibida.

### Implementación `PgVectorStore` con migración de esquema

**R12** — El sistema DEBE proveer una implementación concreta `PgVectorStore` de
`VectorStore`, respaldada por PostgreSQL + la extensión `pgvector`.

**R13** — El sistema DEBE realizar la importación del driver de Postgres
(`psycopg` y/o `pgvector`) **dentro del constructor o de los métodos** de
`PgVectorStore`, no a nivel de módulo, de modo que `store/pgvector_store.py`
sea importable sin el driver instalado.

**R14** — SI se intenta construir o usar `PgVectorStore` y el driver de Postgres
no está instalado, ENTONCES el sistema DEBE lanzar `VectorStoreError` con un
mensaje que indique cómo instalar las dependencias del almacén.

**R15** — CUANDO se invoca `PgVectorStore.ensure_schema()`, el sistema DEBE
crear (si no existen) la extensión `vector`, la tabla de chunks y un índice de
similitud vectorial coseno, y DEBE ser idempotente (segunda invocación sin error).

**R16** — El sistema DEBE definir la columna de vectores de `PgVectorStore` con
dimensión igual a `Settings.embedding_dim`, tomando `embedding_dim` como única
fuente de verdad para la dimensión de la columna.

**R17** — El sistema DEBE mantener la sentencia SQL de migración de esquema en un
fichero versionado `src/wowrag/store/migrations.sql`, parametrizado por nombre de
tabla y dimensión, en lugar de SQL disperso por la lógica.

### Excepción de dominio

**R24** — El sistema DEBE definir una excepción de dominio
`VectorStoreError(Exception)` en `src/wowrag/store/base.py` para todos los fallos
del almacén vectorial (driver ausente, dimensiones inválidas, longitudes
desemparejadas, fallo de conexión).

**R25** — SI la conexión a Postgres falla en una operación de `PgVectorStore`,
ENTONCES el sistema DEBE propagar el fallo como `VectorStoreError` (o subclase),
sin enmascararlo como un resultado vacío.

### `FakeVectorStore` (in-memory, para tests)

**R26** — El sistema DEBE proveer una implementación `FakeVectorStore` de
`VectorStore` que almacene chunks y vectores en memoria usando solo la librería
estándar, sin importar `psycopg`, `pgvector` ni ninguna librería de red/DB.

**R27** — El sistema DEBE que `FakeVectorStore.similarity_search` calcule la
similitud coseno entre el `query_vector` y cada vector almacenado usando solo
`math`/stdlib, y devuelva los top-`k` pares `(Chunk, float)` ordenados por score
descendente, consistente con la semántica de `PgVectorStore` (R9, R10).

**R28** — CUANDO se llama a `FakeVectorStore.upsert` con un `chunk_id` ya
presente, el sistema DEBE reemplazar la entrada existente en memoria (upsert),
manteniendo el `chunk_id` único (paridad con R8).

**R29** — El sistema DEBE que `FakeVectorStore.ensure_schema()` sea una operación
no-op segura (idempotente, sin efectos externos), de modo que el contrato de
`VectorStore` sea uniforme entre fake y real.

### Configuración vía pydantic-settings

**R30** — El sistema DEBE exponer un campo `vector_table: str` (nombre de la
tabla de chunks, por defecto `"chunks"`) como campo de `Settings` en
`src/wowrag/config.py`, configurable desde entorno o `.env`.

**R31** — El sistema DEBE exponer un campo `distance_metric: str` (por defecto
`"cosine"`) como campo de `Settings`, configurable desde entorno o `.env`, que
seleccione la métrica de similitud usada por el almacén.

**R32** — El sistema DEBE reutilizar los campos existentes `postgres_dsn`,
`embedding_dim` y `top_k` de `Settings` para, respectivamente, la conexión de
`PgVectorStore`, la dimensión de la columna vectorial, y el valor por defecto de
`k` en `similarity_search`, sin redefinirlos.

### Pipeline de indexado end-to-end

**R20** — El sistema DEBE proveer un componente `IndexingPipeline` que, dado un
`CorpusLoader`, un `Chunker`, un `EmbeddingProvider` y un `VectorStore`,
ejecute el camino completo corpus → cargar documentos → chunkear → embeber →
upsert.

**R21** — CUANDO se ejecuta `IndexingPipeline.index(corpus_dir)`, el sistema DEBE
asegurar el esquema del `VectorStore` (vía `ensure_schema`) antes de hacer
`upsert`, y DEBE devolver el número total de chunks indexados.

**R22** — CUANDO `IndexingPipeline.index` procesa un corpus de M documentos que
producen C chunks en total, el sistema DEBE embeber esos C chunks y hacer upsert
de exactamente C entradas en el `VectorStore`.

**R23** — El sistema DEBE que `IndexingPipeline` dependa solo de las interfaces
`CorpusLoader`, `Chunker`, `EmbeddingProvider` y `VectorStore` (no de
implementaciones concretas), de modo que sea ejecutable end-to-end en tests con
`JsonlCorpusLoader`/fakes + `OverlapChunker` + `FakeEmbeddingProvider` +
`FakeVectorStore`, sin Postgres ni GPU.

### Exports del paquete

**R33** — El sistema DEBE re-exportar `VectorStore`, `VectorStoreError`,
`FakeVectorStore` y `PgVectorStore` desde `src/wowrag/store/__init__.py`, de modo
que los consumidores de la capa `store` dependan del paquete, no de los módulos
internos.
