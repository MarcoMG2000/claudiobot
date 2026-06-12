# Design — f2-chunking

> CÓMO se construye el modelo `Chunk` y el pipeline de chunking. Respeta el
> layout de `docs/architecture.md` §6 (capa `ingest/chunking.py`) y las
> convenciones de `docs/conventions.md` (interfaces en `base.py`, implementación
> aparte, type hints obligatorios, pydantic como en f0/f1).

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py               # EDITAR — añadir modelo Chunk (pydantic BaseModel)
    config.py               # EDITAR — añadir chunk_size y chunk_overlap a Settings
    ingest/
      __init__.py           # EDITAR — re-exportar Chunker, OverlapChunker, ChunkingError
      chunking.py           # NUEVO — interfaz Chunker (Protocol) + OverlapChunker + ChunkingError
tests/
  test_models.py            # EDITAR — añadir casos para Chunk (R1, R2, R3)
  test_chunking.py          # NUEVO — OverlapChunker (R4–R13)
```

Notas:
- `models.py` ya aloja `Document` (f1); `Chunk` se añade en el mismo fichero
  siguiendo el patrón indicado en `docs/architecture.md` §6 y el comentario de
  docstring existente (`Chunk` → f2).
- El layout de `docs/architecture.md` §6 ubica el chunker en
  `ingest/chunking.py` — se respeta sin reubicar.
- `config.py` sigue el patrón pydantic-settings existente: se añaden dos campos
  con defaults razonables, sin hardcodear números en el código de producción.

## 2. Modelo `Chunk` (R1, R2, R3)

`src/wowrag/models.py` — se añade tras `Document`:

```python
class Chunk(BaseModel):
    """Un fragmento de texto derivado de un Document, con metadata heredada.

    Fields
    ------
    chunk_id   : Identificador estable (determinista) de este chunk.
    text       : Fragmento de texto (obligatorio, no vacío).
    source_url : Heredado de Document; necesario para citas aguas abajo.
    title      : Heredado de Document.
    section    : Heredado de Document.
    """

    chunk_id: str
    text: str
    source_url: str
    title: str
    section: str

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be a non-empty string")
        return v
```

Contrato:
- `chunk_id`, `text`, `source_url`, `title`, `section` son todos obligatorios.
- `text` vacío o solo espacios → `ValidationError` (R2).
- `BaseModel` hereda serialización JSON transparente (R3).
- No hay campo `index` en el modelo; el índice solo se usa internamente para
  derivar el `chunk_id` (ver §4).

## 3. Configuración (R9, R10)

`src/wowrag/config.py` — se añaden dos campos a `Settings`:

```python
chunk_size: int = 512      # máximo de caracteres por chunk
chunk_overlap: int = 64    # caracteres de solapamiento entre chunks consecutivos
```

Defaults elegidos para ser razonables con textos de wowhead (párrafos cortos) y
con el modelo de embeddings bge-m3 (ventana de 8192 tokens pero chunks cortos
mejoran precision). Ambos son enteros positivos; la validación de la relación
`overlap < size` ocurre en el constructor de `OverlapChunker`, no en `Settings`,
para no acoplar la validación de dominio a la configuración.

## 4. Interfaz `Chunker` y excepción (R4, R11)

`src/wowrag/ingest/chunking.py`:

```python
from typing import Protocol
from wowrag.models import Chunk, Document


class ChunkingError(Exception):
    """Raised when chunking parameters are invalid (e.g. overlap >= size)."""


class Chunker(Protocol):
    """Swap point: divide un Document en una lista ordenada de Chunk."""

    def chunk(self, document: Document) -> list[Chunk]:
        ...
```

- `Protocol` (no ABC) — coherente con `CorpusLoader` en f1.
- `ChunkingError` es la excepción de dominio para parámetros inválidos.

## 5. Implementación `OverlapChunker` (R4, R5, R6, R7, R8, R11, R12, R13)

`src/wowrag/ingest/chunking.py` (continuación):

```python
import hashlib


class OverlapChunker:
    """Split por caracteres con ventana deslizante y solapamiento fijo.

    Parameters
    ----------
    chunk_size : int
        Máximo de caracteres por chunk (>0).
    chunk_overlap : int
        Caracteres de solapamiento entre chunks consecutivos (0 <= overlap < size).

    Raises
    ------
    ChunkingError
        Si chunk_overlap >= chunk_size.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ChunkingError(
                f"chunk_overlap ({chunk_overlap}) must be < chunk_size ({chunk_size})"
            )
        self._size = chunk_size
        self._overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        step = self._size - self._overlap
        positions = list(range(0, max(1, len(text)), step))
        chunks: list[Chunk] = []
        for idx, start in enumerate(positions):
            fragment = text[start : start + self._size]
            if not fragment:
                break
            chunk_id = self._make_id(document, idx)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=fragment,
                    source_url=document.source_url,
                    title=document.title,
                    section=document.section,
                )
            )
        return chunks

    @staticmethod
    def _make_id(document: Document, index: int) -> str:
        key = f"{document.source_url}|{document.section}|{index}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
```

### Estrategia de chunking: split por caracteres (decisión)

Se elige **split por caracteres** (no por tokens ni por oraciones) porque:

1. Sin dependencia de tokenizador externo (el tokenizador de bge-m3 no está
   disponible hasta f3). Los caracteres son una unidad de complejidad cero.
2. El corpus de wowhead son textos cortos y estructurados (párrafos de
   habilidades, stats de objetos). La granularidad de caracteres es suficiente.
3. Simple de razonar, simple de testear, sin librería adicional.

El implementer puede añadir un `SentenceBoundaryChunker` como segunda
implementación de `Chunker` sin tocar nada más (precisamente por estar detrás
de la interfaz). Esto se deja explícitamente fuera de esta feature.

### Derivación del `chunk_id` (decisión)

`chunk_id = sha256(source_url + "|" + section + "|" + str(index))[:16]`

- **Determinista**: mismos inputs → mismo id. ✓
- **Sin colisiones prácticas**: sha256 truncado a 16 hex = 64 bits; colisiones
  son neglibigestables dentro de un corpus de wowhead.
- **Estable a re-indexados**: si el corpus no cambia, los ids no cambian —
  propiedad crítica para upsert en pgvector (f4) sin duplicados.
- No incluye el `text` en la clave porque queremos estabilidad si el texto
  se normaliza ligeramente (ej. whitespace); el índice posicional es suficiente.

## 6. Exports del paquete `ingest` (R4, R5)

`src/wowrag/ingest/__init__.py` — se añaden los nuevos símbolos:

```python
from wowrag.ingest.chunking import Chunker, ChunkingError, OverlapChunker
```

Y se actualiza `__all__` para incluirlos. El resto del código depende de la
interfaz `Chunker`, no de `OverlapChunker`. La selección concreta se hace en
el punto de composición (futuro `build_chunker()` en `config.py` o pipeline
de indexado f4).

## 7. Estrategia de tests (sin red ni servicios reales)

Todos los tests usan datos en memoria (no necesitan `tmp_path` salvo para
tests auxiliares). Patrón:

- `test_models.py` (extensión): construir `Chunk` válido → campos correctos
  (R1); `text` vacío → `ValidationError` (R2); serializable a JSON (R3).
- `test_chunking.py`:
  - Parámetros inválidos `overlap >= size` → `ChunkingError` (R11).
  - Texto más corto que `chunk_size` → 1 chunk con todo el texto (R12).
  - Texto exactamente igual a `chunk_size` → 1 chunk (R12, R13).
  - Texto más largo → múltiples chunks con solapamiento correcto (R4, R5, R13).
  - Metadata copiada sin modificación en cada chunk (R6).
  - Dos llamadas con el mismo `Document` → mismos `chunk_id` (R7, R8).
  - Distintos documentos → distintos `chunk_id` (R7).
  - `OverlapChunker` es usable a través del tipo `Chunker` (R4).
  - `Settings.chunk_size` y `Settings.chunk_overlap` pueden leerse y pasarse
    al constructor (R9, R10).

## 8. Alternativas descartadas

### A. Split por tokens (tokenizador del modelo)

Descartado para f2: el tokenizador de bge-m3 no está disponible hasta f3
(embeddings). Añadir una dependencia de `sentence-transformers` solo para
contar tokens en esta fase viola la política de "solo lo necesario para la
feature en curso" (`docs/architecture.md` §7). Si se necesita en el futuro, se
implementa como un segundo `Chunker` concreto.

### B. Split por oraciones / NLP (spaCy, NLTK)

Descartado: añade ~100 MB de modelo de lenguaje solo para f2, y los textos de
wowhead no tienen ambigüedad de límites de oración que justifique esa complejidad.
Queda abierto como `SentenceBoundaryChunker` para una feature posterior.

### C. `chunk_id` como UUID aleatorio

Descartado: UUID aleatorio rompe la estabilidad. Re-indexar el mismo corpus
generaría ids nuevos, produciendo duplicados en pgvector (f4). El id
determinista permite upsert idempotente.

### D. `chunk_id` incluyendo hash del texto

Descartado: si el texto se normaliza (whitespace, encoding) entre ejecuciones,
el id cambiaría aunque el chunk semánticamente sea el mismo. Usar solo
`source_url + section + index` da estabilidad a texto ligeramente distinto.

### E. Colocar el chunker en un nuevo paquete `src/wowrag/chunking/`

Descartado: `docs/architecture.md` §6 ubica explícitamente `chunking.py` dentro
de `ingest/`. Respetar el layout acordado evita diffs de movimiento de archivos
en PRs futuros.
