# Design — f4-vector-store-pgvector

> CÓMO se construye la capa de almacén vectorial y el pipeline de indexado.
> Respeta el layout de `docs/architecture.md` §6 (`src/wowrag/store/`) y las
> convenciones del proyecto: interfaz en `base.py`, implementación real en módulo
> aparte, excepción de dominio, import lazy del driver pesado,
> `from __future__ import annotations`. Sigue el patrón ya establecido en
> f1 (`CorpusLoader`), f2 (`Chunker`) y f3 (`EmbeddingProvider`).

## 0. Decisión de entrega: 3 PRs encadenados (stacked)

f4 es **grande**: interfaz + excepción + `FakeVectorStore` + `PgVectorStore` +
migración SQL + pipeline de indexado + fakes + tests. La fase de apply **excede el
presupuesto de ~400 líneas de un PR único**. En la puerta de aprobación, el humano
decidió **partir el trabajo en 3 slices encadenados (stacked PRs)**, cada uno
auto-contenido, verde bajo tests, e independientemente commiteable:

1. **Slice A — interfaz + fake + config** — `store/base.py` (`VectorStore`
   Protocol + `VectorStoreError`), `FakeVectorStore` (in-memory, coseno stdlib),
   re-exports de `store/__init__.py`, los 2 campos nuevos de `Settings`
   (`vector_table`, `distance_metric`) con sus tests de default + override, y todos
   los tests unitarios del contrato + fake + config
   (R1–R11, R18, R19, R24, R26–R33). Sin DB, sin driver. Todo verde bajo `init.sh`.
2. **Slice B — pgvector + migración** — `PgVectorStore` (import lazy de
   `psycopg`/`pgvector` → `VectorStoreError` si falta), `migrations.sql`
   idempotente, `requirements-pg.txt` (driver fuera del base `requirements.txt`) y
   tests `@pytest.mark.integration` (R12–R17, R25). El módulo importa sin el
   driver instalado; los tests de integración se excluyen de `init.sh`. Todo verde
   bajo `init.sh`.
3. **Slice C — pipeline de indexado** — `IndexingPipeline` en el módulo nuevo
   `index/` + tests end-to-end con fakes
   (`FakeCorpusLoader`/`JsonlCorpusLoader` + `OverlapChunker` +
   `FakeEmbeddingProvider` + `FakeVectorStore`) (R20–R23). Todo verde bajo
   `init.sh`.

El spec se mantiene **único**; `tasks.md` agrupa las tasks bajo las tres slices con
sus criterios de salida. La numeración `R<n>` es estable y no depende del slicing.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    config.py                  # EDITAR — añadir vector_table, distance_metric
    store/
      __init__.py              # EDITAR — re-exportar interfaz, fake, pgvector y excepción
      base.py                  # NUEVO — VectorStore (Protocol) + VectorStoreError
      fake.py                  # NUEVO — FakeVectorStore (in-memory, stdlib, coseno)
      pgvector_store.py        # NUEVO — PgVectorStore (import lazy de psycopg/pgvector)
      migrations.sql           # NUEVO — DDL parametrizada (extensión, tabla, índice)
    index/
      __init__.py              # NUEVO — re-exportar IndexingPipeline
      pipeline.py              # NUEVO — IndexingPipeline (compone interfaces)
requirements-pg.txt            # NUEVO — psycopg[binary] + pgvector; excluido de init.sh
tests/
  test_store_interface.py          # NUEVO — contrato VectorStore vía FakeVectorStore
  test_store_fake.py               # NUEVO — coseno, top-k, upsert, dimensión del fake
  test_store_pgvector.py           # NUEVO — PgVectorStore (@pytest.mark.integration)
  test_index_pipeline.py           # NUEVO — end-to-end con fakes (sin Postgres/GPU)
  test_config.py                   # EDITAR — añadir vector_table, distance_metric a defaults/override
```

Notas:
- `store/__init__.py` es actualmente un placeholder (f0); se reemplaza con los
  re-exports reales (R33).
- `config.py` ya tiene `postgres_dsn`, `embedding_dim` y `top_k`; **no se
  redefinen** (R32). Solo se añaden `vector_table` y `distance_metric` (R30, R31).
- `models.py` **NO se toca** en f4: `similarity_search` devuelve
  `list[tuple[Chunk, float]]` usando el modelo `Chunk` ya existente. El wrapper
  `RetrievedChunk` se difiere a f5 (ver §3).
- `requirements.txt` base **no** gana dependencias nuevas; las de DB van en
  `requirements-pg.txt` (igual espíritu que `requirements-ml.txt` de f3). El test
  `tests/test_requirements_pinned.py` ya exige que `psycopg` NO aparezca en
  `requirements.txt` (lista `DEFERRED`); este diseño lo respeta.

## 2. Estrategia psycopg / pgvector / Python 3.14 (riesgo conocido)

### Diagnóstico del riesgo

El entorno usa Python 3.14 (CPython; confirmado por `*.cpython-314.pyc` en el
repo). A la fecha del spec, los wheels de `psycopg[binary]` y `pgvector` para
Python 3.14 **no están garantizados**, y además requieren un **Postgres vivo con
la extensión pgvector** para ejecutar cualquier test real. Si se declaran como
dependencias base en `requirements.txt`:

- `pip install -r requirements.txt` puede fallar en CI/`init.sh`.
- La suite completa no podría ejecutarse sin un Postgres disponible.
- Se rompería la suite base sin necesidad de DB.

### Decisión adoptada: aislamiento total de la dependencia DB

**Estrategia elegida** (idéntica en espíritu a f3): _import lazy + extra opcional
separado + fake in-memory para tests_.

1. **`requirements.txt` base** — no incluye `psycopg` ni `pgvector`. La suite
   completa corre sin ellos (coherente con `test_requirements_pinned.py`).

2. **`requirements-pg.txt`** — fichero separado (no cargado por `init.sh`):
   ```
   # Postgres + pgvector driver. NOT loaded by init.sh.
   # Install manually: pip install -r requirements-pg.txt
   psycopg[binary]>=3.2.0
   pgvector>=0.3.0
   ```
   Se instala manualmente solo cuando hay un Postgres disponible y se quiere
   probar `PgVectorStore`.

3. **Import lazy en `PgVectorStore`** — la importación de `psycopg`/`pgvector`
   ocurre **dentro del constructor**, no a nivel de módulo:
   ```python
   def __init__(self, ...):
       try:
           import psycopg
           from pgvector.psycopg import register_vector
       except ImportError as exc:
           raise VectorStoreError(
               "Postgres driver not installed. "
               "Install store dependencies: pip install -r requirements-pg.txt"
           ) from exc
       ...
   ```
   Esto hace que `from wowrag.store import PgVectorStore` funcione sin el driver
   instalado (R13). Solo al instanciar la clase se exige la dependencia (R14).

4. **Tests de `PgVectorStore` marcados `@pytest.mark.integration`** — el
   `pyproject.toml` ya registra el mark `integration` e `init.sh` ejecuta
   `pytest -m "not integration"`, por lo que estos tests se omiten
   automáticamente (mismo patrón que f3 con bge-m3).

5. **`FakeVectorStore`** — implementación 100% stdlib (`math`), in-memory, con
   la misma semántica coseno/top-k que `PgVectorStore`. Cubre TODOS los tests
   unitarios de f4 y del pipeline de indexado, y queda disponible para f5.

## 3. Contrato de resultado de búsqueda: `tuple[Chunk, float]` (f4) / `RetrievedChunk` diferido a f5

`models.py` **NO se modifica** en f4. `similarity_search` devuelve
`list[tuple[Chunk, float]]`: cada elemento es un par `(chunk, score)` donde
`chunk` es el modelo `Chunk` ya existente de `src/wowrag/models.py` y `score` es
el coseno (mayor = más similar). La lista va ordenada por score descendente
(mejor primero, R9, R10).

> **Decisión (puerta de aprobación):** el wrapper `RetrievedChunk` se **difiere a
> f5**. f5 introducirá un modelo `RetrievedChunk` que envuelve el par
> `(Chunk, score)` para producir resultados citables estables; por eso el retorno
> en tupla de f4 es el **contrato mínimo deliberado**: f4 expone la búsqueda cruda
> sin acoplar un modelo de presentación que aún no se necesita. El `Chunk`
> devuelto ya transporta `chunk_id`, `text`, `source_url`, `title` y `section`
> (R18), de modo que f5 puede construir el wrapper sin perder metadata.

## 4. Interfaz `VectorStore` y excepción (R1–R5, R24)

`src/wowrag/store/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from wowrag.models import Chunk


class VectorStoreError(Exception):
    """Domain exception for vector-store failures.

    Raised for missing DB driver, dimension mismatches, mismatched
    chunks/embeddings lengths, or connection failures.
    """


class VectorStore(Protocol):
    """Swap point: persiste chunks+vectores+metadata y hace búsqueda por similitud.

    Implementaciones concretas: PgVectorStore (real) y FakeVectorStore (tests).
    Callers depend on this Protocol, never on a concrete implementation.
    """

    @property
    def dimension(self) -> int:
        """Dimensión esperada de los vectores que acepta/devuelve el almacén."""
        ...

    def ensure_schema(self) -> None:
        """Prepara esquema (tabla/columna/índice) de forma idempotente."""
        ...

    def upsert(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> int:
        """Almacena chunks con sus vectores y metadata.

        Returns el número de filas insertadas o actualizadas.
        Raises VectorStoreError si len(chunks) != len(embeddings).
        Upsert por chunk_id: re-almacenar un chunk_id existente lo reemplaza.
        """
        ...

    def similarity_search(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Chunk, float]]:
        """Devuelve hasta k pares (chunk, score) más similares (coseno), score desc.

        Cada elemento es (Chunk, float): el Chunk existente + su score de coseno.
        Almacén vacío → []. query_vector de dimensión incorrecta →
        VectorStoreError.
        """
        ...
```

Contrato del Protocol:
- `ensure_schema()` idempotente (R2, R15, R29).
- `upsert` empareja por índice, valida longitudes (R6, R7), upsert por
  `chunk_id` (R8), persiste metadata (R18).
- `similarity_search` → ≤ k resultados, coseno, score desc (R9, R10); vacío → []
  (R11); dimensión incorrecta → `VectorStoreError` (R19).

## 5. `FakeVectorStore` (R26–R29, R7, R8, R11, R19)

`src/wowrag/store/fake.py` — sin imports de DB/red, solo `math`:

```python
from __future__ import annotations

import math

from wowrag.models import Chunk
from wowrag.store.base import VectorStoreError


class FakeVectorStore:
    """In-memory VectorStore for unit tests. Zero DB dependencies.

    Cosine similarity over stored vectors, mismas semánticas que PgVectorStore.
    """

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension
        # chunk_id -> (Chunk, vector)
        self._rows: dict[str, tuple[Chunk, list[float]]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    def ensure_schema(self) -> None:
        # No-op: in-memory store has no schema to migrate (R29).
        return None

    def upsert(self, chunks, embeddings) -> int:
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"len(chunks)={len(chunks)} != len(embeddings)={len(embeddings)}"
            )  # R7
        for chunk, vec in zip(chunks, embeddings):
            self._rows[chunk.chunk_id] = (chunk, list(vec))  # R8 upsert by id
        return len(chunks)  # R6

    def similarity_search(self, query_vector, k) -> list[tuple[Chunk, float]]:
        if len(query_vector) != self._dimension:
            raise VectorStoreError(
                f"query_vector dim {len(query_vector)} != expected {self._dimension}"
            )  # R19
        if not self._rows:
            return []  # R11
        scored = [
            (self._cosine(query_vector, vec), chunk)
            for chunk, vec in self._rows.values()
        ]
        scored.sort(key=lambda t: t[0], reverse=True)  # R9, R10 score desc
        return [(chunk, score) for score, chunk in scored[:k]]  # (Chunk, float)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)
```

Propiedades:
- Solo stdlib (`math`); cero imports de psycopg/pgvector (R26).
- Coseno explícito, top-k por score desc (R27), paridad con la real (R9, R10).
- Upsert por `chunk_id`: clave de diccionario garantiza unicidad (R28).
- `ensure_schema` no-op (R29).
- Como los vectores del `FakeEmbeddingProvider` (f3) ya son de norma unitaria, el
  coseno aquí es consistente con el orden esperado en tests del pipeline.

## 6. `PgVectorStore` con import lazy y migración (R12–R17, R25)

`src/wowrag/store/pgvector_store.py`:

```python
from __future__ import annotations

from pathlib import Path

from wowrag.models import Chunk
from wowrag.store.base import VectorStoreError

_MIGRATIONS = Path(__file__).with_name("migrations.sql")


class PgVectorStore:
    """Real VectorStore backed by PostgreSQL + pgvector (lazy driver import).

    El import de psycopg/pgvector ocurre en __init__, así el módulo es
    importable sin el driver instalado (R13).
    """

    def __init__(
        self,
        dsn: str,
        dimension: int,
        table: str = "chunks",
        metric: str = "cosine",
    ) -> None:
        try:
            import psycopg  # noqa: F401 (lazy import, R13)
            from pgvector.psycopg import register_vector  # noqa: F401
        except ImportError as exc:
            raise VectorStoreError(
                "Postgres driver not installed. "
                "Install store dependencies: pip install -r requirements-pg.txt"
            ) from exc  # R14
        self._dsn = dsn
        self._dimension = dimension
        self._table = table
        self._metric = metric
        self._psycopg = psycopg
        self._register_vector = register_vector

    @property
    def dimension(self) -> int:
        return self._dimension  # R16: embedding_dim is the source of truth

    def _connect(self):
        try:
            conn = self._psycopg.connect(self._dsn)
        except Exception as exc:  # connection failure → domain error (R25)
            raise VectorStoreError(f"Postgres connection failed: {exc}") from exc
        self._register_vector(conn)
        return conn

    def ensure_schema(self) -> None:
        ddl = _MIGRATIONS.read_text(encoding="utf-8").format(
            table=self._table, dim=self._dimension
        )  # R17: SQL lives in migrations.sql, parametrizado
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(ddl)  # R15 idempotente (CREATE ... IF NOT EXISTS)
            conn.commit()

    def upsert(self, chunks, embeddings) -> int:
        if len(chunks) != len(embeddings):
            raise VectorStoreError(...)  # R7
        # INSERT ... ON CONFLICT (chunk_id) DO UPDATE  -> upsert por id (R8)
        # persiste chunk_id, text, source_url, title, section, embedding (R18)
        ...
        return len(chunks)

    def similarity_search(self, query_vector, k) -> list[tuple[Chunk, float]]:
        if len(query_vector) != self._dimension:
            raise VectorStoreError(...)  # R19
        # SELECT chunk_id, text, source_url, title, section,
        #        1 - (embedding <=> %s) AS score
        # ORDER BY embedding <=> %s LIMIT k   (<=> = cosine distance, R10)
        # mapea cada fila a (Chunk(...), score)  -> list[tuple[Chunk, float]]
        ...
```

Notas de implementación (para el implementer):
- `<=>` es el operador de **distancia coseno** de pgvector; el `score` que se
  devuelve es `1 - distancia` para que "mayor = más similar" (R10). `ORDER BY`
  por distancia ascendente == score descendente (R9).
- El índice de migración usa `vector_cosine_ops` (coseno), coherente con R10/R31.
- Las cláusulas `with conn` cierran/commitean; una conexión fallida se traduce a
  `VectorStoreError` (R25), nunca a un resultado vacío.

## 7. `migrations.sql` (R15, R16, R17)

`src/wowrag/store/migrations.sql` — DDL idempotente y parametrizada por
`{table}` y `{dim}` (sustituidos con `str.format` en `ensure_schema`):

```sql
-- f4: pgvector schema migration. Idempotent. Parametrized by {table} and {dim}.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS {table} (
    chunk_id   TEXT PRIMARY KEY,
    text       TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title      TEXT NOT NULL,
    section    TEXT NOT NULL,
    embedding  vector({dim}) NOT NULL
);

CREATE INDEX IF NOT EXISTS {table}_embedding_cosine_idx
    ON {table} USING hnsw (embedding vector_cosine_ops);
```

> `chunk_id` como `PRIMARY KEY` habilita el `ON CONFLICT (chunk_id) DO UPDATE`
> del upsert (R8). Índice HNSW con `vector_cosine_ops` para coseno (R10).
> `{dim}` = `embedding_dim` (R16). El uso de `str.format` con placeholders de
> nombre/dimensión es seguro porque ambos provienen de `Settings` (config de
> confianza), no de entrada de usuario; los **valores** (texto, vectores) van
> siempre por parámetros de psycopg, nunca interpolados.

## 8. `IndexingPipeline` end-to-end (R20–R23)

Decisión de ubicación: **módulo nuevo `src/wowrag/index/`**, NO dentro de
`ingest/`. Justificación según `docs/architecture.md` §6: `ingest/` es la capa de
**carga + chunking** (entrada de datos), mientras que el indexado **compone
varias capas** (ingest + embeddings + store) en un flujo offline. Meter el
pipeline en `ingest/` mezclaría la capa de carga con las capas de embeddings y
store (el revisor rechaza código que mezcle capas). Un módulo `index/` dedicado
al flujo de orquestación offline mantiene la separación limpia y deja claro el
punto de composición. (`rag/` queda reservado para la orquestación **online** de
consulta → prompt → LLM, f8.)

`src/wowrag/index/pipeline.py`:

```python
from __future__ import annotations

from pathlib import Path

from wowrag.embeddings.base import EmbeddingProvider
from wowrag.ingest.base import CorpusLoader
from wowrag.ingest.chunking import Chunker
from wowrag.store.base import VectorStore


class IndexingPipeline:
    """Flujo offline de indexado: corpus -> load -> chunk -> embed -> upsert.

    Depende solo de interfaces (R23), de modo que es testeable end-to-end con
    fakes sin Postgres ni GPU.
    """

    def __init__(
        self,
        loader: CorpusLoader,
        chunker: Chunker,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    def index(self, corpus_dir: str | Path) -> int:
        """Indexa el corpus y devuelve el nº total de chunks indexados (R21, R22)."""
        self._store.ensure_schema()  # R21: schema antes de upsert
        documents = self._loader.load(corpus_dir)
        chunks = []
        for doc in documents:
            chunks.extend(self._chunker.chunk(doc))
        if not chunks:
            return 0
        embeddings = self._embedder.embed([c.text for c in chunks])
        self._store.upsert(chunks, embeddings)  # R22: C upserts
        return len(chunks)
```

Punto de composición sugerido (factory, NO obligatorio en f4 salvo lo que el
pipeline necesite — se documenta como contrato de uso para f5+):

```python
def build_vector_store(settings: Settings | None = None) -> VectorStore:
    s = settings or Settings()
    return PgVectorStore(
        dsn=s.postgres_dsn,
        dimension=s.embedding_dim,
        table=s.vector_table,
        metric=s.distance_metric,
    )
```

## 9. Configuración en `Settings` (R30, R31, R32)

`src/wowrag/config.py` — campos añadidos a `Settings`:

```python
vector_table: str = "chunks"      # nombre de la tabla de chunks en pgvector
distance_metric: str = "cosine"   # métrica de similitud del almacén
```

Reutilizados (NO redefinir, R32):
- `postgres_dsn` → DSN de conexión de `PgVectorStore`.
- `embedding_dim` → dimensión de la columna `vector(dim)` (R16) y del fake.
- `top_k` → valor por defecto de `k` para búsquedas (lo consumirá f5; f4 expone
  `k` como parámetro explícito de `similarity_search`).

> Cada campo nuevo de `Settings` DEBE tener test (default-assert + env-override).
> El reviewer de f3 rechazó exactamente ese hueco; `tasks.md` lo cubre
> explícitamente para `vector_table` y `distance_metric`.

## 10. Exports del paquete `store` (R33)

`src/wowrag/store/__init__.py` — reemplazar el placeholder:

```python
from wowrag.store.base import VectorStore, VectorStoreError
from wowrag.store.fake import FakeVectorStore
from wowrag.store.pgvector_store import PgVectorStore

__all__ = [
    "VectorStore",
    "VectorStoreError",
    "FakeVectorStore",
    "PgVectorStore",
]
```

`src/wowrag/index/__init__.py`:

```python
from wowrag.index.pipeline import IndexingPipeline

__all__ = ["IndexingPipeline"]
```

## 11. `requirements-pg.txt` (nuevo fichero)

```
# Postgres + pgvector driver for PgVectorStore. NOT loaded by init.sh.
# Install manually when a Postgres instance is available:
#   pip install -r requirements-pg.txt
psycopg[binary]>=3.2.0
pgvector>=0.3.0
```

`requirements.txt` base **no** se modifica (no hay nuevas deps unitarias;
`pydantic-settings`, `pyyaml`, `pytest` bastan para la suite no-integration).
Coherente con `tests/test_requirements_pinned.py` (que ya prohíbe `psycopg` en
`requirements.txt`).

## 12. Estrategia de tests

### Tests unitarios (sin Postgres, sin driver) — corren con `init.sh`

- `test_store_interface.py`: contrato de `VectorStore` usando `FakeVectorStore`:
  almacén vacío → `[]` (R11); upsert N → N filas (R6); longitudes
  desemparejadas → `VectorStoreError` (R7); dimensión de query incorrecta →
  `VectorStoreError` (R19); `FakeVectorStore` satisface el Protocol
  estructuralmente (R1, R26); `ensure_schema()` no-op idempotente (R2, R29);
  `import wowrag.store.pgvector_store` sin driver no lanza ImportError (R13).
- `test_store_fake.py`: coseno y top-k del fake: cada resultado es un par
  `(Chunk, float)` ordenado por score desc (R9, R10); `k` limita el nº de
  resultados (R9); upsert por `chunk_id` reemplaza (R8, R28); el `Chunk` del par
  conserva metadata (`source_url`, `title`, `section`) (R18); `dimension`
  configurable (R16 vía fake / R5); `PgVectorStore()` sin driver →
  `VectorStoreError` no `ImportError` (R14).
- `test_index_pipeline.py`: end-to-end con `JsonlCorpusLoader` (+ `tmp_path`),
  `OverlapChunker`, `FakeEmbeddingProvider`, `FakeVectorStore`: indexa un corpus
  y devuelve C (R20, R22); `ensure_schema` se invoca antes de upsert (R21,
  verificable con un spy/fake que registre orden); pipeline solo depende de
  interfaces (R23); corpus vacío → 0 chunks (R22 borde).
- `test_config.py` (editar): `vector_table` y `distance_metric` en defaults
  (R30, R31) + override por env (R30, R31).

### Tests de integración (requieren Postgres+pgvector) — `@pytest.mark.integration`

- `test_store_pgvector.py`:
  - `ensure_schema()` crea esquema; segunda llamada idempotente (R15).
  - `upsert` + `similarity_search` round-trip; orden coseno (R10, R12, R18).
  - upsert por `chunk_id` reemplaza (R8).
  - columna `vector(embedding_dim)` (R16).
  - DSN inválido / Postgres caído → `VectorStoreError` (R25).
  - `migrations.sql` usado para el DDL (R17).

Estos tests se excluyen automáticamente por `pytest -m "not integration"`.

## 13. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Import a nivel de módulo de `psycopg`/`pgvector` | Rompe `./init.sh` en Python 3.14 sin wheels y sin Postgres; viola el patrón lazy de f3 |
| `psycopg`/`pgvector` en `requirements.txt` base | Rompe la suite sin DB; viola `test_requirements_pinned.py` (psycopg en DEFERRED) |
| Pipeline de indexado dentro de `ingest/` | Mezcla capas (ingest + embeddings + store); el revisor rechaza mezcla de capas (`docs/architecture.md` §6) |
| Pipeline dentro de `rag/` | `rag/` es la orquestación **online** (consulta→LLM, f8); el indexado es **offline** |
| `RetrievedChunk` (modelo) como retorno de f4 | Diferido a f5 en la puerta de aprobación; f4 expone el contrato mínimo `tuple[Chunk, float]` y f5 envolverá el par en `RetrievedChunk` para resultados citables. Adoptar el modelo en f4 acoplaría un tipo de presentación que aún no se necesita |
| Distancia L2 (`<->`) o producto interno (`<#>`) | f3 produce vectores de norma unitaria; coseno (`<=>`) es la métrica consistente del proyecto (`architecture.md`) |
| `ABC` en lugar de `Protocol` | Inconsistente con `CorpusLoader`/`Chunker`/`EmbeddingProvider`; Protocol no requiere herencia |
| `FakeVectorStore` persistiendo en disco/sqlite | Añade I/O y dependencia innecesaria; `dict` in-memory basta para tests deterministas |
| SQL embebido en strings dentro de `pgvector_store.py` | El DDL versionado en `migrations.sql` es auditable y parametrizable (R17); evita SQL disperso |
| Redefinir `top_k`/`embedding_dim`/`postgres_dsn` en config | Ya existen; redefinirlos duplica fuentes de verdad (R32) |
