# Design — f3-embeddings-provider

> CÓMO se construye la capa de embeddings. Respeta el layout de
> `docs/architecture.md` §6 (`src/wowrag/embeddings/`) y las convenciones del
> proyecto: interfaz en `base.py`, implementación real en módulo aparte,
> excepción de dominio, imports type-safe con `from __future__ import annotations`.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    config.py                  # EDITAR — añadir embedding_batch_size, embedding_device
    embeddings/
      __init__.py              # EDITAR — re-exportar interfaz, fake, bge-m3 y excepción
      base.py                  # NUEVO — EmbeddingProvider (Protocol) + EmbeddingError
      fake.py                  # NUEVO — FakeEmbeddingProvider (sin deps ML)
      bge_m3.py                # NUEVO — BgeM3Embeddings (import lazy de FlagEmbedding)
requirements.txt               # EDITAR — añadir pydantic, sin ML libs; crear requirements-ml.txt
requirements-ml.txt            # NUEVO — FlagEmbedding + torch; excluido de init.sh
tests/
  test_embeddings_interface.py # NUEVO — contrato de EmbeddingProvider vía FakeEmbeddingProvider
  test_embeddings_fake.py      # NUEVO — determinismo y dimensión de FakeEmbeddingProvider
  test_embeddings_bge_m3.py    # NUEVO — BgeM3Embeddings (integración, marcados @pytest.mark.integration)
```

Notas:
- `config.py` ya tiene `embedding_model: str = "BAAI/bge-m3"` y
  `embedding_dim: int = 1024`; solo se añaden los dos campos nuevos.
- `embeddings/__init__.py` es actualmente un placeholder (f0); se reemplaza con
  los re-exports reales.
- No se modifica `models.py` (Chunk ya existe) ni ningún otro módulo de `ingest/`.

## 2. Estrategia torch / Python 3.14 (riesgo conocido)

### Diagnóstico del riesgo

El entorno usa Python 3.14 (CPython). A la fecha del spec (2026-06-12),
`torch`, `sentence-transformers` y `FlagEmbedding` **no garantizan wheels
publicados para Python 3.14**. Si se declaran como dependencias base en
`requirements.txt`:

- `pip install -r requirements.txt` falla en CI/init.sh.
- Los 71 tests existentes no pueden ejecutarse.
- La suite base queda rota sin necesidad de GPU.

### Decisión adoptada: aislamiento total de la dependencia ML

**Estrategia elegida**: _Lazy import + extra opcional separado_

1. **`requirements.txt` base** — no incluye `FlagEmbedding`, `torch` ni
   `sentence-transformers`. La suite completa corre sin ellos.

2. **`requirements-ml.txt`** — fichero separado (no cargado por `init.sh`) que
   declara las dependencias ML pesadas:
   ```
   FlagEmbedding>=1.3.0
   torch>=2.3.0
   ```
   Se instala manualmente (`pip install -r requirements-ml.txt`) solo cuando hay
   GPU disponible o se quiere probar la implementación real.

3. **Import lazy en `BgeM3Embeddings`** — la importación de `FlagEmbedding`
   ocurre **dentro del constructor `__init__`**, no a nivel de módulo:
   ```python
   def __init__(self, ...):
       try:
           from FlagEmbedding import BGEM3FlagModel  # lazy import
       except ImportError as exc:
           raise EmbeddingError(
               "FlagEmbedding is not installed. "
               "Run: pip install -r requirements-ml.txt"
           ) from exc
       ...
   ```
   Esto hace que `from wowrag.embeddings import BgeM3Embeddings` funcione sin
   `FlagEmbedding` instalado. Solo al instanciar la clase se exige la dependencia.

4. **Tests de `BgeM3Embeddings` marcados `@pytest.mark.integration`** — el
   `pyproject.toml` ya registra el mark `integration` y `init.sh` ejecuta
   `pytest -m "not integration"`, por lo que estos tests se omiten
   automáticamente. Coherente con el patrón ya establecido para pgvector/Ollama.

5. **`FakeEmbeddingProvider`** — implementación 100% stdlib (solo `hashlib` y
   `math`), usable en todos los tests unitarios de f3, f4, f5 sin GPU ni torch.

### Alternativas descartadas

- **A. `sentence-transformers` en vez de `FlagEmbedding`**: bge-m3 produce tres
  tipos de vectores (denso, sparse, ColBERT). `sentence-transformers` solo expone
  los densos de forma directa y usa una API diferente. `FlagEmbedding.BGEM3FlagModel`
  es la API canónica de BAAI y permite optar por sparse/ColBERT en el futuro sin
  cambiar la interfaz. Descartado.

- **B. Dependencia opcional vía `pyproject.toml [project.optional-dependencies]`**:
  viable, pero el proyecto aún no usa `pyproject.toml` como build backend (usa
  `requirements.txt` plano). Añadir un build backend solo para este extra es un
  over-engineering para la etapa actual. Descartado.

- **C. Import condicional a nivel de módulo con `TYPE_CHECKING`**: no funciona en
  runtime; `TYPE_CHECKING` es solo para herramientas de análisis estático.
  El import dentro del constructor es el patrón correcto para lazy runtime imports.
  Descartado.

- **D. Stub `FlagEmbedding` en `requirements.txt`**: instalar un stub no-op
  rompería silenciosamente la funcionalidad real. Descartado.

## 3. Interfaz `EmbeddingProvider` y excepción (R1, R2, R3, R6)

`src/wowrag/embeddings/base.py`:

```python
from __future__ import annotations
from typing import Protocol


class EmbeddingError(Exception):
    """Domain exception for embedding failures (missing deps, invalid input, device)."""


class EmbeddingProvider(Protocol):
    """Swap point: convierte textos en vectores de dimensión fija.

    Implementaciones concretas: BgeM3Embeddings (real), FakeEmbeddingProvider (tests).
    """

    @property
    def dimension(self) -> int:
        """Dimensionalidad fija del espacio de embedding de este proveedor."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Parameters
        ----------
        texts:
            Non-empty strings to embed.  Empty list returns [].
            Empty or whitespace-only strings raise EmbeddingError.

        Returns
        -------
        list[list[float]]
            One vector per input text, each with exactly `dimension` elements,
            in the same order as the input.

        Raises
        ------
        EmbeddingError
            If any text is empty/whitespace, or if the backend fails.
        """
        ...
```

Contrato del Protocol:
- `dimension` es propiedad de solo lectura; no tiene setter.
- `embed([])` → `[]` (R3).
- `embed(texts)` → `len(result) == len(texts)` (R4).
- Cada vector tiene `len(v) == self.dimension` (R6).

## 4. `FakeEmbeddingProvider` (R12, R13, R14)

`src/wowrag/embeddings/fake.py` — sin imports de ML:

```python
from __future__ import annotations
import hashlib
import math
from wowrag.embeddings.base import EmbeddingError


class FakeEmbeddingProvider:
    """Deterministic embedding provider for unit tests. Zero ML dependencies.

    Each text maps to a fixed vector derived from SHA-256 of its UTF-8
    encoding. Same text → same vector across instances and sessions.
    """

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise EmbeddingError(
                    f"Text at position {i} is empty or whitespace-only."
                )
            result.append(self._text_to_vector(text))
        return result

    def _text_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()  # 32 bytes
        # Tile the digest bytes to fill `dimension` floats, normalize to unit sphere
        raw = [(digest[j % 32] / 255.0) - 0.5 for j in range(self._dimension)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
```

Propiedades:
- Determinista: `sha256(text)` es el único input. Mismo texto → mismo vector
  en cualquier instancia, sesión o proceso (R13).
- Sin torch, sin FlagEmbedding, sin numpy: stdlib únicamente (R12).
- Dimensión configurable; por defecto 1024 para coincidir con bge-m3 (R14, R17).
- Vectores normalizados a norma unitaria, lo que los hace compatibles con
  cosine-similarity en pgvector (f4) sin sorpresas.

## 5. `BgeM3Embeddings` (R7, R8, R9, R10, R11, R15, R16)

`src/wowrag/embeddings/bge_m3.py`:

```python
from __future__ import annotations
from wowrag.embeddings.base import EmbeddingError


class BgeM3Embeddings:
    """Real bge-m3 embedding provider via FlagEmbedding (lazy import).

    The FlagEmbedding import happens inside __init__, so this module is
    importable without FlagEmbedding installed (R9).
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        dimension: int = 1024,
        batch_size: int = 32,
        device: str = "cpu",
    ) -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel  # lazy import (R9)
        except ImportError as exc:
            raise EmbeddingError(
                "FlagEmbedding is not installed. "
                "Install ML dependencies: pip install -r requirements-ml.txt"
            ) from exc

        if device == "cuda":
            import torch
            if not torch.cuda.is_available():
                raise EmbeddingError(
                    "embedding_device='cuda' requested but CUDA is not available."
                )  # R15

        self._dimension = dimension
        self._batch_size = batch_size
        self._model = BGEM3FlagModel(model_name, use_fp16=(device != "cpu"))

    @property
    def dimension(self) -> int:
        return self._dimension  # R11: no model call needed

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise EmbeddingError(
                    f"Text at position {i} is empty or whitespace-only."
                )  # R16
        # Process in batches (R5)
        result: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            output = self._model.encode(batch, batch_size=self._batch_size)
            result.extend(output["dense_vecs"].tolist())
        return result
```

## 6. Configuración en `Settings` (R10, R17)

`src/wowrag/config.py` — campos añadidos a `Settings`:

```python
embedding_batch_size: int = 32   # número de textos por batch en BgeM3Embeddings
embedding_device: str = "cpu"    # "cpu" | "cuda"; sin GPU por defecto
```

Los campos `embedding_model: str = "BAAI/bge-m3"` y `embedding_dim: int = 1024`
ya existen. Solo se añaden los dos nuevos.

Punto de composición sugerido (para f4 o el indexing pipeline):

```python
def build_embedding_provider(settings: Settings | None = None) -> BgeM3Embeddings:
    s = settings or Settings()
    return BgeM3Embeddings(
        model_name=s.embedding_model,
        dimension=s.embedding_dim,
        batch_size=s.embedding_batch_size,
        device=s.embedding_device,
    )
```

Este helper NO se crea en f3; se añade cuando f4 lo necesite. Se documenta
aquí como contrato de uso esperado.

## 7. Exports del paquete `embeddings` (R18)

`src/wowrag/embeddings/__init__.py` — reemplazar el placeholder:

```python
from wowrag.embeddings.base import EmbeddingError, EmbeddingProvider
from wowrag.embeddings.fake import FakeEmbeddingProvider
from wowrag.embeddings.bge_m3 import BgeM3Embeddings

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "BgeM3Embeddings",
]
```

## 8. `requirements-ml.txt` (nuevo fichero)

```
# ML dependencies for bge-m3. NOT loaded by init.sh.
# Install manually: pip install -r requirements-ml.txt
FlagEmbedding>=1.3.0
torch>=2.3.0
```

`requirements.txt` base no se modifica para este feature (no hay nuevas
dependencias unitarias; `pydantic-settings`, `pyyaml`, `pytest` siguen siendo
suficientes para la suite entera salvo los tests de integración).

## 9. Estrategia de tests

### Tests unitarios (sin GPU, sin FlagEmbedding) — corren con `init.sh`

- `test_embeddings_interface.py`: verifica el contrato del Protocol usando
  `FakeEmbeddingProvider` como implementación concreta.
  - `embed([])` → `[]` (R3)
  - `len(embed(texts)) == len(texts)` para N > 1 (R4)
  - Cada vector tiene `len(v) == dimension` (R6)
  - Mismo texto → mismo vector (R7 via fake, R13)
  - `FakeEmbeddingProvider` es usable como `EmbeddingProvider` (R1, R2)

- `test_embeddings_fake.py`: propiedades específicas del fake.
  - Dimension configurable en constructor (R14)
  - Texto vacío / solo espacios → `EmbeddingError` con posición (R16)
  - Determinismo cross-instance: `FakeEmbeddingProvider(dim).embed(t)` ==
    `FakeEmbeddingProvider(dim).embed(t)` para mismo `t` (R13)
  - `BgeM3Embeddings` es importable sin FlagEmbedding (solo import, no instanciar)
    → no lanza `ImportError` en el import (R9)

### Tests de integración (requieren GPU + FlagEmbedding) — `@pytest.mark.integration`

- `test_embeddings_bge_m3.py`:
  - `BgeM3Embeddings(...).embed(["hello"])` → 1 vector de 1024 floats (R8, R11)
  - Reproducibilidad intra-sesión mismo texto (R7)
  - Batch de N textos → N vectores (R4, R5)
  - `device="cuda"` sin CUDA → `EmbeddingError` (R15)
  - Texto vacío → `EmbeddingError` (R16)

Estos tests se excluyen automáticamente por `pytest -m "not integration"` tal
como establece `init.sh` y el mark registrado en `pyproject.toml`.

## 10. Alternativas descartadas (resumen)

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Import a nivel de módulo de FlagEmbedding | Rompe `./init.sh` en Python 3.14 sin wheels ML |
| FlagEmbedding en `requirements.txt` base | Idem; viola política de deps mínimas |
| `sentence-transformers` como backend | API no expone sparse/ColBERT; FlagEmbedding es la API canónica de BAAI |
| `ABC` en lugar de `Protocol` | Inconsistente con `Chunker` y `CorpusLoader` (f1/f2); Protocol no requiere herencia |
| `FakeEmbeddingProvider` con valores aleatorios | No determinista → tests no reproducibles entre sesiones |
| dimension fija hardcodeada en el fake | Rompe tests de f4/f5 si cambia la dimensión del modelo |
| `numpy` en el fake para normalización | Añade dependencia innecesaria; `math` stdlib es suficiente |
