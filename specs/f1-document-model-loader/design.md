# Design — f1-document-model-loader

> CÓMO se construye el modelo `Document` y el loader de corpus local. Respeta el
> layout de `docs/architecture.md` §6 (capa `ingest`) y las convenciones de
> `docs/conventions.md` (interfaces en `base.py`, implementación aparte, type
> hints obligatorios, pydantic como en f0).

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py              # NUEVO — Document (pydantic), modelo compartido de capas
    ingest/
      __init__.py          # EDITAR — exporta CorpusLoader, JsonlCorpusLoader (y re-export de Document opcional)
      base.py              # NUEVO — interfaz CorpusLoader (Protocol) + CorpusError / CorpusNotFoundError
      loader.py            # NUEVO — JsonlCorpusLoader (implementación)
tests/
  test_models.py           # NUEVO — Document (R1, R2, R3)
  test_corpus_loader.py    # NUEVO — JsonlCorpusLoader (R5–R11)
```

Notas:
- `models.py` aparece en el layout de `docs/architecture.md` §6 como hogar de
  `Document, Chunk, RetrievedChunk, Answer`. f1 crea **solo** `Document`; los
  demás se difieren a sus features (`Chunk`→f2, etc.).
- La interfaz vive en `ingest/base.py` siguiendo el patrón de
  `docs/conventions.md` §"Patrón de abstracción" (interfaz en `base.py` del
  paquete, implementación en módulo aparte `loader.py`).
- El placeholder actual `ingest/__init__.py` (solo docstring) se reemplaza por
  los exports reales.

## 2. Modelo `Document` (R1, R2, R3)

`src/wowrag/models.py`, pydantic `BaseModel` (consistente con `Persona` de f0):

```python
from __future__ import annotations

from pydantic import BaseModel, field_validator


class Document(BaseModel):
    """A single source document: raw text plus wowhead-style metadata."""

    text: str
    source_url: str
    title: str
    section: str = ""

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be a non-empty string")
        return v
```

Contrato:
- `text`, `source_url`, `title` obligatorios; `section` opcional con default `""`
  (R3).
- `text` vacío o solo espacios → `ValidationError` mencionando `text` (R2).
- pydantic ya falla si falta cualquier campo obligatorio (parte de R2 para
  `text`; los otros obligatorios quedan cubiertos por el comportamiento estándar
  de pydantic).

## 3. Interfaz `CorpusLoader` (R4) y excepciones (R7, R8)

`src/wowrag/ingest/base.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from wowrag.models import Document


class CorpusError(Exception):
    """Base error for corpus loading problems."""


class CorpusNotFoundError(CorpusError):
    """Raised when the corpus path is missing or not a directory.
    Message includes the offending path."""


class MalformedCorpusError(CorpusError):
    """Raised when a line is invalid JSON or fails Document validation.
    Message includes the file path and 1-based line number."""


class CorpusLoader(Protocol):
    """Swap point: reads a local corpus directory into Documents."""

    def load(self, corpus_dir: str | Path) -> list[Document]:
        ...
```

- `Protocol` (no ABC) para mantener el contrato estructural y permitir fakes en
  tests sin herencia (coherente con el estilo del proyecto). Si el implementer
  prefiere ABC por simetría con futuros `base.py`, es aceptable siempre que la
  firma `load(corpus_dir) -> list[Document]` se respete.
- `CorpusNotFoundError` cubre R7; `MalformedCorpusError` cubre R8. Ambas derivan
  de `CorpusError` para que el caller pueda capturar la familia.

## 4. Implementación `JsonlCorpusLoader` (R5, R6, R8, R9, R10, R11)

`src/wowrag/ingest/loader.py`:

```python
class JsonlCorpusLoader:
    """Reads every ``*.jsonl`` file in a directory; one Document per line."""

    def load(self, corpus_dir: str | Path) -> list[Document]:
        ...
```

Comportamiento:
- Resuelve `corpus_dir` a `Path`. SI no existe o no es directorio →
  `raise CorpusNotFoundError(f"... {corpus_dir!r}")` (R7).
- Enumera ficheros `*.jsonl` de forma **ordenada** (`sorted(dir.glob("*.jsonl"))`)
  para resultado determinista.
- Por cada fichero, itera líneas con índice 1-based:
  - Línea en blanco (`strip() == ""`) → se ignora (R10).
  - `json.loads(line)`; si falla → `MalformedCorpusError` con fichero + nº línea
    (R8).
  - `Document(**obj)`; si `ValidationError` → `MalformedCorpusError` con fichero
    + nº línea, encadenando la causa (`raise ... from exc`) (R8).
- Sin ficheros `.jsonl` → devuelve `[]` (R9).
- No realiza red ni I/O fuera del directorio (R11) — solo `pathlib`/`json`.

> Implementación de referencia (el implementer puede refinar):
```python
import json
from pathlib import Path

from wowrag.ingest.base import (CorpusNotFoundError, MalformedCorpusError)
from wowrag.models import Document


class JsonlCorpusLoader:
    def load(self, corpus_dir):
        root = Path(corpus_dir)
        if not root.is_dir():
            raise CorpusNotFoundError(f"corpus directory not found: {root!r}")
        docs: list[Document] = []
        for path in sorted(root.glob("*.jsonl")):
            with path.open("r", encoding="utf-8") as fh:
                for lineno, raw in enumerate(fh, start=1):
                    if not raw.strip():
                        continue
                    try:
                        obj = json.loads(raw)
                        docs.append(Document(**obj))
                    except Exception as exc:
                        raise MalformedCorpusError(
                            f"{path}:{lineno}: malformed corpus line"
                        ) from exc
        return docs
```

## 5. Exports y punto de composición (R5)

`src/wowrag/ingest/__init__.py`:

```python
from wowrag.ingest.base import (
    CorpusError, CorpusLoader, CorpusNotFoundError, MalformedCorpusError,
)
from wowrag.ingest.loader import JsonlCorpusLoader

__all__ = [
    "CorpusLoader", "JsonlCorpusLoader",
    "CorpusError", "CorpusNotFoundError", "MalformedCorpusError",
]
```

- El resto del código depende de `CorpusLoader` (interfaz), no de
  `JsonlCorpusLoader`. La selección concreta se hace en el caller / factory
  (futuras features), no esparcida — coherente con `docs/conventions.md`.
- No se modifica `wowrag/__init__.py` salvo que el implementer quiera re-exportar
  `Document` a nivel raíz; es opcional y no requerido por ningún `R<n>`.

## 6. Excepciones definidas (nuevas en f1)

- `CorpusError(Exception)` — base de la familia.
- `CorpusNotFoundError(CorpusError)` — ruta inexistente / no-directorio (R7).
- `MalformedCorpusError(CorpusError)` — JSON inválido o `Document` inválido,
  con fichero y nº de línea (R8).

La abstención y errores de servicios (Postgres/Ollama) no aplican a f1.

## 7. Estrategia de tests (sin red ni servicios reales)

Todos los tests usan `tmp_path` para materializar el corpus en disco; **nada de
red, Postgres u Ollama** (`docs/conventions.md` §Tests). Patrón:

- `test_models.py`: construir `Document` válido (R1, R3); `text` vacío/blank →
  `ValidationError` (R2); `section` ausente → `""` (R3).
- `test_corpus_loader.py`: escribir `.jsonl` en `tmp_path` y cargar (R6); directorio
  vacío / sin `.jsonl` → `[]` (R9); líneas en blanco ignoradas (R10); ruta
  inexistente → `CorpusNotFoundError` (R7); línea con JSON inválido →
  `MalformedCorpusError` con nº de línea (R8); línea JSON sin `text` →
  `MalformedCorpusError` (R8); el loader satisface el `Protocol` `CorpusLoader`
  (R4, R5). R11 se cubre implícitamente: los tests pasan offline (sin fixtures de
  red); se documenta que el loader solo usa `pathlib`/`json`.

## 8. Alternativa descartada

- **Markdown + frontmatter (YAML) como formato de corpus.** Descartado como
  formato principal: requiere una dependencia extra de parsing de frontmatter,
  mezcla cuerpo libre con metadata y dificulta el mapeo 1:1 a `Document` y el
  aislamiento de errores por unidad. JSONL es streamable, sin dependencia nueva
  (solo `json` stdlib) y es el formato natural de salida del scraper de `f11`. Si
  en el futuro se necesita Markdown, se añadiría como **otra implementación** de
  `CorpusLoader` sin tocar el resto del sistema (gracias a R4).
- **Un único fichero JSON-array por corpus en vez de JSONL.** Descartado: obliga
  a cargar todo el fichero en memoria y a re-parsear todo si una entrada está
  mal; JSONL aísla el fallo por línea (R8) y permite streaming.
