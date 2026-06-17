# Review — feature f6-prompt-builder

**Veredicto:** APPROVED

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `test_builtprompt_fields` (test_models_prompt.py)
- R2: [x] cubierto por `test_source_fields`, `test_builtprompt_fields` (test_models_prompt.py)
- R3: [x] cubierto por `test_system_and_user_nonempty` (test_prompt_builder.py)
- R4: [x] cubierto por `test_system_and_user_nonempty` (test_prompt_builder.py)
- R5: [x] cubierto por `test_sources_match_markers` (test_prompt_builder.py)
- R6: [x] cubierto por `test_exports_from_package` (Protocol importable; signature verified by direct inspection of `prompt_builder_base.py:40-45` — matches spec exactly); structural satisfaction implicit in all 16 builder tests
- R7: [x] cubierto por `test_builder_depends_only_on_models` (test_prompt_builder.py)
- R8: [x] cubierto por `test_empty_query_raises` (test_prompt_builder.py — tests both "" and "   ")
- R9: [x] cubierto por `test_user_contains_query` (test_prompt_builder.py)
- R10: [x] cubierto por `test_default_persona_from_config` (test_prompt_builder.py)
- R11: [x] cubierto por `test_explicit_persona_overrides_config` (test_prompt_builder.py)
- R12: [x] cubierto por `test_persona_style_injected` (test_prompt_builder.py)
- R13: [x] cubierto por `test_grounding_instructions_present`, `test_grounding_independent_of_persona` (test_prompt_builder.py)
- R14: [x] cubierto por `test_grounding_instructions_present`, `test_grounding_independent_of_persona` (test_prompt_builder.py)
- R15: [x] cubierto por `test_grounding_instructions_present`, `test_grounding_independent_of_persona` (test_prompt_builder.py)
- R16: [x] cubierto por `test_grounding_independent_of_persona` (test_prompt_builder.py — loops over simple/orc/troll)
- R17: [x] cubierto por `test_context_has_sequential_citation_markers` (test_prompt_builder.py)
- R18: [x] cubierto por `test_context_includes_chunk_text_and_url` (test_prompt_builder.py)
- R19: [x] cubierto por `test_sources_match_markers` (test_prompt_builder.py)
- R20: [x] cubierto por `test_context_only_from_result` (test_prompt_builder.py — regex scans for foreign URLs)
- R21: [x] cubierto por `test_empty_context_builds_valid_prompt` (test_prompt_builder.py)
- R22: [x] cubierto por `test_sources_match_markers`, `test_builtprompt_accepts_empty_sources` (test_prompt_builder.py + test_models_prompt.py)
- R23: [x] cubierto por `test_default_persona_from_config` (test_prompt_builder.py — uses Settings(default_persona="orc"), no new config field)
- R24: [x] cubierto por `test_missing_persona_propagates` (test_prompt_builder.py)
- R25: [x] cubierto por `test_empty_query_raises` (raises PromptBuilderError — confirms it exists as Exception subclass)
- R26: [x] cubierto por `test_missing_persona_propagates` (test_prompt_builder.py — asserts PersonaNotFoundError, not PromptBuilderError)
- R27: [x] cubierto por `test_exports_from_package` (test_prompt_builder.py) + `test_models_exported` (test_models_prompt.py)

## Tasks completas

- T1: [x] `Source` + `BuiltPrompt` added to `src/wowrag/models.py`; `__all__` updated
- T2: [x] `src/wowrag/generation/prompt_builder_base.py` created with Protocol + exception
- T3: [x] `src/wowrag/generation/prompt_builder.py` created with `DefaultPromptBuilder`
- T4: [x] `src/wowrag/generation/__init__.py` updated with re-exports
- T5: [x] `tests/test_models_prompt.py` — 4 tests
- T6: [x] `tests/test_prompt_builder.py` — 16 tests
- Z1: [x] `./init.sh` (165 passed, 3 skipped, exit 0)

## Checkpoints

- C1: [x] Archivos base presentes; `./init.sh` termina con exit 0 (165 passed, 3 skipped)
- C2: [x] Solo f6 en `in_progress` (f6 y f7 corren en paralelo según contexto del leader; f6 es la feature bajo revisión); todas las features `done` previas (f0–f4) tienen tests que pasan
- C3: [x] `src/wowrag/generation/` respeta la separación por capas; sin SQL ni HTTP a Ollama en código de f6; `generation/base.py` NO creado (reservado para f7 per design.md §3); `src/wowrag/llm/` pertenece a f7 (no write-set de f6)
- C4: [x] Tests DB-free/GPU-free/network-free; ninguno marcado integration; 20/20 pasan
- C5: [x] f6 incluye instrucción de grounding en el prompt (R13–R15); no implementa abstención (frontera f8 respetada; R21 confirma que contexto vacío no lanza excepción)
- C6: [x] `specs/f6-prompt-builder/` contiene `requirements.md`, `design.md`, `tasks.md`; EARS estricto; todas las tasks `[x]`; todos los R1–R27 cubiertos por tests

## Verificación de fronteras (scope boundary)

- NO llama a LLM/Ollama: confirmado — zero imports de `wowrag.llm` o `httpx` en `prompt_builder*.py`
- NO orquesta ni emite mensaje de abstención: confirmado — `_NO_CONTEXT_NOTICE` es solo una indicación de ausencia de contexto para el LLM, no el mensaje de abstención de f8
- NO lee `below_threshold`: confirmado — `_format_context` y `build()` no acceden al campo
- NO redefine personas: confirmado — `load_persona` / `default_persona` de f0 reutilizados tal cual
- `config.py` NO modificado: confirmado — la edición de `tests/test_config.py` en el working tree pertenece a f7 (documentado en `progress/impl_f7-llm-provider-ollama.md` T7)
- `generation/base.py` NO creado: confirmado — solo `prompt_builder_base.py`, `prompt_builder.py`, `__init__.py` en `generation/`

## Observaciones menores (no bloquean aprobación)

1. R6 no tiene un test explícito de `isinstance(DefaultPromptBuilder(), PromptBuilder)` con `runtime_checkable`. La cobertura actual (importación del Protocol + uso estructural en 16 tests) es suficiente per las convenciones del proyecto, que usa Protocol sin `@runtime_checkable`. No se requiere cambio.
2. `test_context_only_from_result` usa `import re` dentro del cuerpo del test (línea 381). Menor style nit per `conventions.md` (imports al nivel de módulo), pero no viola ningún requisito y el test es correcto.

## Cambios requeridos

Ninguno.
