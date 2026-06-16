# Review — feature f3-embeddings-provider

**Veredicto:** APPROVED

> Re-review tras corregir el único defecto bloqueante de la primera ronda
> (R10 sin cobertura para los dos campos nuevos `embedding_batch_size` /
> `embedding_device`). El fix es real y verificado por mutación: borrar
> cualquiera de los dos campos rompe la suite. Sin regresión ni scope creep:
> `src/` no cambió respecto a la ronda anterior, solo `tests/test_config.py`
> y el informe de implementación. `./init.sh` exit 0.

## Re-check del defecto R10 (foco de esta ronda)

R10 ahora tiene cobertura REAL en `tests/test_config.py`:

- **Defaults asertados** (`EXPECTED_DEFAULTS`, líneas 13-14): `embedding_batch_size: 32`
  y `embedding_device: "cpu"`, ejercitados por `test_settings_defaults_without_env`
  (línea 28) y `test_settings_exposes_all_required_fields` (línea 35).
- **Override por entorno** (`test_embedding_batch_size_and_device_overridable_from_env`,
  líneas 49-56, tagged `# R10`): fija `EMBEDDING_BATCH_SIZE=8` y `EMBEDDING_DEVICE=cuda`
  (distintos de los defaults 32/`cpu`) y comprueba que `Settings` los lee. Prueba
  binding real de entorno, no re-aserción del default.
- **Prueba de mutación (verificación del revisor):** eliminando ambos campos de
  `src/wowrag/config.py` y corriendo `tests/test_config.py` con el intérprete del
  venv → **3 tests FAILED** (`test_settings_defaults_without_env`,
  `test_settings_exposes_all_required_fields`,
  `test_embedding_batch_size_and_device_overridable_from_env`). Borrar o renombrar
  cualquiera de los dos campos rompe la suite. Campos restaurados; suite verde de nuevo.

## Trazabilidad requirements ↔ tests
- R1: [x] `tests/test_embeddings_interface.py::test_provider_protocol_compatible`.
- R2: [x] `test_provider_protocol_compatible` (propiedad read-only `dimension`).
- R3: [x] `test_embeddings_interface.py::test_embed_empty_list`.
- R4: [x] `test_embeddings_interface.py::test_embed_returns_same_count` (unit) + `test_embeddings_bge_m3.py::test_embed_batch` (integ).
- R5: [x] `test_embeddings_bge_m3.py::test_embed_batch` (batch_size=2, 5 textos) — integ.
- R6: [x] `test_embeddings_interface.py::test_embed_vector_dimension`.
- R7: [x] `test_embeddings_interface.py::test_embed_same_text_reproducible` (unit) + `test_embeddings_bge_m3.py::test_embed_reproducible_intra_session` (integ).
- R8: [x] `test_embeddings_bge_m3.py::test_embed_single_text` (integ).
- R9: [x] `test_embeddings_fake.py::test_bge_m3_module_importable_without_flagembedding` + `::test_bge_m3_instantiation_raises_embedding_error`.
- R10: [x] **CORREGIDO.** `embedding_model` ya cubierto vía `EXPECTED_DEFAULTS`;
  los dos campos nuevos `embedding_batch_size` y `embedding_device` ahora cubiertos por
  `test_config.py::test_settings_defaults_without_env` +
  `test_config.py::test_settings_exposes_all_required_fields` (defaults 32 / `"cpu"`) y por
  `test_config.py::test_embedding_batch_size_and_device_overridable_from_env` (override
  por entorno a 8 / `"cuda"`). Confirmado por mutación (ver re-check arriba).
- R11: [x] `test_embeddings_bge_m3.py::test_dimension_without_model_load` + `::test_embed_single_text` (integ).
- R12: [x] `test_embeddings_fake.py::test_fake_provider_uses_no_ml_libraries`.
- R13: [x] `test_embeddings_fake.py::test_determinism_cross_instance`.
- R14: [x] `test_embeddings_fake.py::test_custom_dimension` + `::test_default_dimension`.
- R15: [x] `test_embeddings_bge_m3.py::test_cuda_unavailable_raises` (integ).
- R16: [x] `test_embeddings_interface.py::test_embed_invalid_text_raises` + `::test_embed_whitespace_text_raises` + `test_embeddings_bge_m3.py::test_embed_empty_text_raises_integration`.
- R17: [x] `test_embeddings_fake.py::test_settings_embedding_dim_feeds_fake` + `::test_default_dimension`.
- R18: [x] `test_embeddings_interface.py` y `test_embeddings_fake.py` importan los 4 símbolos desde `wowrag.embeddings`.

Todos los `R1..R18` cubiertos por ≥1 test.

## Tasks completas
- T1: [x]   - T2: [x]   - T3: [x]   - T4: [x]   - T5: [x]
- T6: [x]   - T7: [x]   - T8: [x]   - T9: [x]   - T10: [x]

Todas las tasks de `specs/f3-embeddings-provider/tasks.md` están `[x]`.

## No regresión / scope
- `git diff` sobre `src/`: solo `config.py` (los 2 campos de R10) y `embeddings/__init__.py`
  (re-exports de T5) — idénticos a lo aprobado en la primera ronda. **`src/` sin cambios
  respecto a la ronda anterior.**
- Cambios de esta ronda: `tests/test_config.py` (+12 líneas: defaults + test override) y
  `progress/impl_f3-embeddings-provider.md` (fila R10 actualizada). Sin tocar otros tests
  ni código de implementación.
- `feature-list.json`: f3 sigue `in_progress` (no se marcó `done` indebidamente).
- Aislamiento ML intacto: integración (`test_embeddings_bge_m3.py`) sigue omitida vía
  `importorskip("FlagEmbedding")` + `@pytest.mark.integration`.

## ./init.sh
- Ejecutado: **exit 0**. `86 passed, 1 skipped in 0.21s`.
- +1 test respecto a la ronda anterior (85 → 86): el nuevo
  `test_embedding_batch_size_and_device_overridable_from_env`.
- El skip es `tests/test_embeddings_bge_m3.py` completo (integración, FlagEmbedding ausente) — esperado.

## Checkpoints
- C1: [x] arnés completo; `./init.sh` exit 0.
- C2: [x] una sola feature `in_progress` (f3); estado coherente.
- C3: [x] capas respetadas; `requirements.txt` pineado y mínimo; sin prints/secretos/TODOs.
- C4: [x] test por módulo OK; fakes/integration OK; `pytest -m "not integration"` > 0 y verde.
- C5: [-] No aplica a f3 (grounding/abstención llega en f5/f8).
- C6: [x] carpeta `specs/f3/` completa, EARS OK, tasks `[x]`, y **cada R<n> (incluido R10)
  cubierto por ≥1 test**.

## Cambios requeridos
Ninguno. El defecto bloqueante de la primera ronda (R10) está resuelto y verificado.
