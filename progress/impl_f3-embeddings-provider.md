# Informe de implementación — f3-embeddings-provider

- **Feature:** `f3-embeddings-provider` — Embeddings provider (abstraction + bge-m3)
- **Agente:** implementer
- **Fecha:** 2026-06-15
- **Estado:** implementación completa; pendiente de review (NO marcada `done`)

## Resumen

Se implementó la capa de embeddings siguiendo los skeletons del `design.md`,
respetando el patrón de abstracción de f1/f2 (Protocol en `base.py`,
implementación real en módulo aparte, excepción de dominio,
`from __future__ import annotations`). La dependencia pesada (FlagEmbedding /
torch) queda totalmente aislada: import lazy dentro de `__init__` y fichero
`requirements-ml.txt` separado, no cargado por `init.sh`. La suite base
permanece verde en Python 3.14 sin ML libs instaladas.

## Archivos creados

| Archivo | Task | Contenido |
|---------|------|-----------|
| `src/wowrag/embeddings/base.py` | T1 | `EmbeddingError(Exception)` + `EmbeddingProvider` Protocol (propiedad read-only `dimension`, método `embed`). |
| `src/wowrag/embeddings/fake.py` | T2 | `FakeEmbeddingProvider` determinista, solo `hashlib` + `math`, cero imports ML. |
| `src/wowrag/embeddings/bge_m3.py` | T3 | `BgeM3Embeddings` con import lazy de `FlagEmbedding.BGEM3FlagModel` en `__init__`, chequeo CUDA, batching. |
| `requirements-ml.txt` | T6 | `FlagEmbedding>=1.3.0`, `torch>=2.3.0`; comentado como instalación manual fuera de `init.sh`. |
| `tests/test_embeddings_interface.py` | T7 | 7 tests del contrato del Protocol vía `FakeEmbeddingProvider`. |
| `tests/test_embeddings_fake.py` | T8 | 7 tests de propiedades del fake + seguridad del import lazy de bge_m3. |
| `tests/test_embeddings_bge_m3.py` | T9 | 6 tests de integración (todos `@pytest.mark.integration`). |

## Archivos editados

| Archivo | Task | Cambio |
|---------|------|--------|
| `src/wowrag/config.py` | T4 | Añadidos `embedding_batch_size: int = 32` y `embedding_device: str = "cpu"` a `Settings`. NO se tocó `embedding_model` ni `embedding_dim`. |
| `src/wowrag/embeddings/__init__.py` | T5 | Reemplazado el placeholder por re-exports de `EmbeddingError`, `EmbeddingProvider`, `FakeEmbeddingProvider`, `BgeM3Embeddings` con `__all__`. |
| `specs/f3-embeddings-provider/tasks.md` | — | T1..T10 marcadas `[x]`. |
| `progress/current.md` | — | Feature en curso + plan. |

`requirements.txt` NO se modificó (el design indica que la suite unitaria no
requiere nuevas deps; las ML viven solo en `requirements-ml.txt`).

## Trazabilidad R ↔ test

| R | Descripción (resumen) | Test que lo cubre | Tipo |
|---|------------------------|-------------------|------|
| R1 | Interfaz `EmbeddingProvider.embed` | `test_embeddings_interface.py::test_provider_protocol_compatible` | unit |
| R2 | Propiedad read-only `dimension` | `test_embeddings_interface.py::test_provider_protocol_compatible` | unit |
| R3 | `embed([])` → `[]` sin excepción | `test_embeddings_interface.py::test_embed_empty_list` | unit |
| R4 | N textos → N vectores en orden | `test_embeddings_interface.py::test_embed_returns_same_count`; `test_embeddings_bge_m3.py::test_embed_batch` | unit + integ |
| R5 | Batching para listas largas | `test_embeddings_bge_m3.py::test_embed_batch` (batch_size=2, 5 textos) | integ |
| R6 | Cada vector tiene `dimension` floats | `test_embeddings_interface.py::test_embed_vector_dimension` | unit |
| R7 | Mismo texto → vector idéntico (intra-instancia) | `test_embeddings_interface.py::test_embed_same_text_reproducible`; `test_embeddings_bge_m3.py::test_embed_reproducible_intra_session` | unit + integ |
| R8 | `BgeM3Embeddings` usa bge-m3 dense_vecs | `test_embeddings_bge_m3.py::test_embed_single_text` | integ |
| R9 | Import lazy de FlagEmbedding | `test_embeddings_fake.py::test_bge_m3_module_importable_without_flagembedding`; `test_embeddings_fake.py::test_bge_m3_instantiation_raises_embedding_error` | unit |
| R10 | `embedding_model`/`batch_size`/`device` en `Settings` | `test_config.py::test_settings_defaults_without_env` y `test_config.py::test_settings_exposes_all_required_fields` (defaults 32 / `"cpu"` vía `EXPECTED_DEFAULTS`); `test_config.py::test_embedding_batch_size_and_device_overridable_from_env` (configurables desde entorno) | unit |
| R11 | `dimension` sin cargar modelo | `test_embeddings_bge_m3.py::test_dimension_without_model_load`; `test_embeddings_bge_m3.py::test_embed_single_text` | integ |
| R12 | `FakeEmbeddingProvider` sin deps ML | `test_embeddings_fake.py::test_fake_provider_uses_no_ml_libraries` | unit |
| R13 | Determinismo cross-instance del fake | `test_embeddings_fake.py::test_determinism_cross_instance`; `test_embeddings_interface.py::test_embed_same_text_reproducible` | unit |
| R14 | `dimension` configurable (default 1024) | `test_embeddings_fake.py::test_custom_dimension`; `test_embeddings_fake.py::test_default_dimension` | unit |
| R15 | `device="cuda"` sin CUDA → `EmbeddingError` | `test_embeddings_bge_m3.py::test_cuda_unavailable_raises` | integ |
| R16 | Texto vacío/espacios → `EmbeddingError` con posición | `test_embeddings_interface.py::test_embed_invalid_text_raises`; `test_embeddings_interface.py::test_embed_whitespace_text_raises`; `test_embeddings_bge_m3.py::test_embed_empty_text_raises_integration` | unit + integ |
| R17 | `embedding_dim` es source of truth | `test_embeddings_fake.py::test_settings_embedding_dim_feeds_fake`; `test_embeddings_fake.py::test_default_dimension` | unit |
| R18 | Re-exports desde `embeddings/__init__.py` | `test_embeddings_interface.py` y `test_embeddings_fake.py` importan los 4 símbolos desde `wowrag.embeddings` (falla la suite si no se exportan) | unit |

Todos los `R1..R18` quedan cubiertos por ≥1 test. R5, R8, R11, R15 se cubren
solo con tests de integración (requieren el modelo real); el resto tienen
cobertura unitaria que corre en `init.sh`.

## Estado de las tasks

- [x] T1 — base.py (interfaz + excepción)
- [x] T2 — fake.py
- [x] T3 — bge_m3.py (import lazy)
- [x] T4 — campos en Settings
- [x] T5 — re-exports en __init__.py
- [x] T6 — requirements-ml.txt
- [x] T7 — test_embeddings_interface.py
- [x] T8 — test_embeddings_fake.py
- [x] T9 — test_embeddings_bge_m3.py (integración)
- [x] T10 — verificación final

## Verificación final (`./init.sh`)

```
==> wow-classic-rag :: init
==> Python: Python 3.14.4
==> Instalando dependencias
==> Ejecutando pytest (no integration)
86 passed, 1 skipped in 0.22s
==> init OK
EXIT_CODE=0
```

- **Exit code:** 0
- **Suite no-integration:** 86 passed (71 previos + 14 de T7/T8 + 1 nuevo de cobertura R10:
  `test_config.py::test_embedding_batch_size_and_device_overridable_from_env`). Los defaults
  de `embedding_batch_size`/`embedding_device` se afirman ahora en `EXPECTED_DEFAULTS`.
- **1 skipped:** `tests/test_embeddings_bge_m3.py` completo, vía
  `pytest.importorskip("FlagEmbedding")` a nivel de módulo (esperado; FlagEmbedding
  no instalado). Los 6 tests de integración existen y están marcados
  `@pytest.mark.integration` (verificado estáticamente: 6/6 marcados).

### Comprobaciones explícitas de T10

1. `from wowrag.embeddings import EmbeddingProvider, FakeEmbeddingProvider,
   BgeM3Embeddings, EmbeddingError` → **OK sin FlagEmbedding instalado**
   (verificado con `PYTHONPATH=src python -c ...` → `IMPORT_OK`).
2. `import wowrag.embeddings.bge_m3` no introduce `FlagEmbedding` en
   `sys.modules` → **OK** (import lazy confirmado).
3. `requirements-ml.txt` existe y **NO** está referenciado por `requirements.txt`
   ni por `init.sh` → **OK** (grep sin coincidencias).
4. `test_requirements_pinned.py` sigue verde: `torch`/`sentence-transformers`
   ausentes de `requirements.txt` → **OK**.

## Desviaciones del spec

Ninguna. Se respetaron los skeletons del `design.md` literalmente. Único matiz
de implementación (dentro del contrato del spec): los tests de integración usan
un `pytest.importorskip("FlagEmbedding")` a nivel de módulo además del mark
`@pytest.mark.integration`, de modo que el fichero también se omite con limpieza
si alguien lo ejecutara con `-m integration` sin las ML libs instaladas. No
altera el comportamiento de `init.sh` (que excluye por mark).
