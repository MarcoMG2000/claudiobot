# Tasks — f3-embeddings-provider

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests unitarios usan solo stdlib y `FakeEmbeddingProvider`; sin
> torch, sin GPU, sin servicios externos. La trazabilidad `R<n>` ↔ test es
> obligatoria (`docs/verification.md`); nombra o comenta cada test con su `R<n>`.
> NO marques la feature `done` ni edites `feature-list.json` (eso es del
> leader/reviewer).

## Implementación

- [x] **T1 — Interfaz `EmbeddingProvider` y excepción `EmbeddingError`.**
  Crear `src/wowrag/embeddings/base.py` con:
  - `EmbeddingError(Exception)` — excepción de dominio.
  - `EmbeddingProvider` Protocol con propiedad de solo lectura `dimension: int`
    y método `embed(texts: list[str]) -> list[list[float]]`. Incluir docstring
    con el contrato: lista vacía → `[]`, texto vacío → `EmbeddingError`,
    resultado tiene la misma longitud que la entrada, cada vector tiene
    exactamente `dimension` floats.
  _(Cubre R1, R2, R3, R4, R6)_

- [x] **T2 — `FakeEmbeddingProvider` en `fake.py`.**
  Crear `src/wowrag/embeddings/fake.py` con `FakeEmbeddingProvider`:
  - Constructor `__init__(self, dimension: int = 1024)`.
  - Propiedad `dimension` que devuelve el valor del constructor.
  - `embed([])` → `[]`.
  - `embed(texts)` itera, rechaza textos vacíos/espacios con `EmbeddingError`
    indicando la posición.
  - `_text_to_vector(text)` genera vector de `dimension` floats a partir de
    `sha256(text.encode()).digest()`, normalizado a norma unitaria via `math`.
  - Cero imports de torch / FlagEmbedding / sentence-transformers.
  _(Cubre R12, R13, R14, R16)_

- [x] **T3 — `BgeM3Embeddings` con import lazy en `bge_m3.py`.**
  Crear `src/wowrag/embeddings/bge_m3.py` con `BgeM3Embeddings`:
  - Constructor `__init__(self, model_name, dimension, batch_size, device)` con
    defaults coherentes con `Settings` (`"BAAI/bge-m3"`, 1024, 32, `"cpu"`).
  - Import de `FlagEmbedding.BGEM3FlagModel` **dentro del constructor** (no a
    nivel de módulo); si falla → `EmbeddingError` con mensaje de instalación.
  - Comprobación CUDA: si `device == "cuda"` y `torch.cuda.is_available()` es
    falso → `EmbeddingError`.
  - Propiedad `dimension` que devuelve el valor del constructor sin llamar al modelo.
  - `embed([])` → `[]`.
  - `embed(texts)`: valida que ningún texto sea vacío/espacios (`EmbeddingError`
    con posición); procesa en batches de `batch_size`; usa `output["dense_vecs"]`.
  _(Cubre R5, R7, R8, R9, R11, R15, R16)_

- [x] **T4 — Nuevos campos en `Settings`.**
  Editar `src/wowrag/config.py`, añadir a la clase `Settings`:
  - `embedding_batch_size: int = 32`
  - `embedding_device: str = "cpu"`
  Los campos `embedding_model` y `embedding_dim` ya existen; no tocarlos.
  _(Cubre R10, R17)_

- [x] **T5 — Re-exportar desde `embeddings/__init__.py`.**
  Reemplazar el contenido placeholder de `src/wowrag/embeddings/__init__.py`
  con imports y `__all__` que exporten `EmbeddingError`, `EmbeddingProvider`,
  `FakeEmbeddingProvider`, `BgeM3Embeddings`.
  _(Cubre R18)_

- [x] **T6 — Crear `requirements-ml.txt`.**
  Crear `requirements-ml.txt` en la raíz con `FlagEmbedding>=1.3.0` y
  `torch>=2.3.0`. Añadir comentario que lo identifique como dependencia manual
  excluida de `init.sh`. NO añadir estas dependencias a `requirements.txt`.
  _(Condición necesaria para R8, R9; salvaguarda el riesgo torch/Python 3.14)_

## Tests

- [x] **T7 — `tests/test_embeddings_interface.py`.**
  Tests del contrato del Protocol usando `FakeEmbeddingProvider` como
  implementación concreta (cero deps ML). Casos mínimos (citar `R<n>`):
  - `test_embed_empty_list`: `fake.embed([])` → `[]`. _(R3)_
  - `test_embed_returns_same_count`: `fake.embed(["a", "b", "c"])` → 3 vectores. _(R4)_
  - `test_embed_vector_dimension`: cada vector tiene `len(v) == fake.dimension`. _(R6)_
  - `test_embed_same_text_reproducible`: `fake.embed(["t"])` dos veces → mismos
    vectores. _(R7)_
  - `test_provider_protocol_compatible`: `FakeEmbeddingProvider` es asignable a
    `EmbeddingProvider` y satisface el Protocol estructuralmente. _(R1, R2)_
  - `test_embed_invalid_text_raises`: `fake.embed(["ok", ""])` → `EmbeddingError`
    mencionando posición 1. _(R16)_
  - `test_embed_whitespace_text_raises`: `fake.embed(["  "])` → `EmbeddingError`. _(R16)_

- [x] **T8 — `tests/test_embeddings_fake.py`.**
  Tests de propiedades específicas del `FakeEmbeddingProvider`. Casos mínimos:
  - `test_custom_dimension`: `FakeEmbeddingProvider(dimension=64)` → vectores de
    64 floats. _(R14)_
  - `test_default_dimension`: `FakeEmbeddingProvider()` → `dimension == 1024`. _(R14, R17)_
  - `test_determinism_cross_instance`: dos instancias independientes con misma
    `dimension` producen el mismo vector para el mismo texto. _(R13)_
  - `test_settings_embedding_dim_feeds_fake`: `FakeEmbeddingProvider(dimension=Settings().embedding_dim)`
    se construye sin error; `dimension` coincide. _(R17)_
  - `test_bge_m3_module_importable_without_flagembedding`: `import wowrag.embeddings.bge_m3`
    no lanza `ImportError` aunque FlagEmbedding no esté instalado. _(R9)_
  - `test_bge_m3_instantiation_raises_embedding_error`: `BgeM3Embeddings()` lanza
    `EmbeddingError` (no `ImportError`) cuando FlagEmbedding falta. _(R9)_

- [x] **T9 — `tests/test_embeddings_bge_m3.py` (integración).**
  Crear el fichero con `@pytest.mark.integration` en cada test. Se excluyen
  automáticamente por `init.sh`. Casos mínimos (requieren GPU + FlagEmbedding):
  - `test_embed_single_text`: `BgeM3Embeddings().embed(["Hello WoW"])` → 1 vector
    de 1024 floats. _(R8, R11)_
  - `test_embed_batch`: lista de 5 textos → 5 vectores, todos de 1024 floats.
    _(R4, R5)_
  - `test_embed_reproducible_intra_session`: mismo texto, dos llamadas en la
    misma instancia → vectores idénticos. _(R7)_
  - `test_cuda_unavailable_raises`: `BgeM3Embeddings(device="cuda")` en máquina
    sin CUDA → `EmbeddingError`. _(R15)_ _(skip si CUDA está disponible)_
  - `test_embed_empty_text_raises_integration`: `BgeM3Embeddings().embed([""])` →
    `EmbeddingError`. _(R16)_
  - `test_dimension_without_model_load`: propiedad `dimension` devuelve 1024 sin
    necesidad de llamar a `encode`. _(R11)_

## Cierre

- [x] **T10 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con
  la suite `not integration` en verde. Debe incluir los 71 tests previos más
  todos los tests nuevos de T7 y T8. Los tests de T9 deben existir en disco y
  estar correctamente marcados `@pytest.mark.integration`; no tienen que pasar
  en init.sh. Comprobar que:
  - Todos los `R<n>` de `requirements.md` tienen al menos un test (unitario o
    de integración).
  - `from wowrag.embeddings import EmbeddingProvider, FakeEmbeddingProvider,
    BgeM3Embeddings, EmbeddingError` funciona sin FlagEmbedding instalado.
  - `requirements-ml.txt` existe pero no está referenciado en `requirements.txt`
    ni en `init.sh`.
  _(Verificación integral; no añade requirements nuevos)_
