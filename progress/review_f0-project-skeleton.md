# Review — feature f0-project-skeleton

**Veredicto:** APPROVED

## Trazabilidad requirements ↔ tests
- R1: [x] `test_import_wowrag_succeeds`, `test_top_level_exports_present` (test_package_imports.py)
- R2: [x] `test_placeholder_subpackages_import` (parametrizado sobre los 7 subpaquetes)
- R3: [x] `test_settings_defaults_without_env` (test_config.py)
- R4: [x] `test_env_var_overrides_default`, `test_env_var_takes_priority_over_env_file`
- R5: [x] `test_settings_defaults_without_env`, `test_settings_exposes_all_required_fields`
- R6: [x] `test_reads_values_from_env_file`, `test_env_var_takes_priority_over_env_file`
- R7: [x] `test_load_simple_persona_returns_persona` (verifica name, system_style, language opcional)
- R8: [x] `test_load_simple_persona_returns_persona`, `test_all_bundled_personas_load`
- R9: [x] `test_unknown_persona_raises_with_name` (mensaje contiene "nope")
- R10: [x] `test_all_bundled_personas_load` (simple/orc/troll)
- R11: [x] `test_orc_persona_has_zug_zug`
- R12: [x] `test_default_persona_resolves_from_settings`, `test_default_persona_uses_default_setting`
- R13: [x] `test_required_dependencies_are_pinned`, `test_deferred_dependencies_absent`
- R14: [x] `test_gitignore_ignores_secrets_and_caches`, `test_env_example_exists_and_documents_r5_fields`

## Tasks completas
- T1: [x]  src/wowrag/__init__.py + 7 subpaquetes placeholder
- T2: [x]  src/wowrag/config.py Settings (env_file, extra=ignore, 8 campos)
- T3: [x]  src/wowrag/personas/__init__.py (Persona, PersonaNotFoundError, load_persona)
- T4: [x]  simple.yaml, orc.yaml ("Zug zug!"), troll.yaml
- T5: [x]  default_persona() + exports en __init__.py
- T6: [x]  requirements.txt pineado
- T7: [x]  .gitignore + .env.example
- T8: [x]  tests/test_package_imports.py
- T9: [x]  tests/test_config.py
- T10: [x] tests/test_personas.py
- T11: [x] tests/test_requirements_pinned.py
- T12: [x] tests/test_repo_hygiene.py
- T13: [x] ./init.sh exit 0, 26 tests verdes

## Checkpoints
- C1 (init.sh exit 0): [x]
- C2 (estado coherente, una sola in_progress): [x]
- C3 (arquitectura, deps pineadas, sin print/secretos/TODO): [x]
- C4 (un test por módulo, fakes, pytest verde): [x]
- C5 (grounding): n/a en f0 (no hay capa de retrieval/generation aún)
- C6 (SDD: specs completas, EARS, tasks [x], R<n> cubiertos): [x]

## Acceptance F0
- src/ package layout exists: [x]
- pydantic-settings carga config env+files: [x] (R4/R6 testeados)
- personas cargables/intercambiables: [x] (load_persona + 3 YAML + default_persona)
- requirements pineado: [x] (== en las 3 deps, diferidas ausentes)
- init.sh verde: [x] (exit 0, 26 passed)

## Notas (no bloqueantes)
- init.sh corre sobre Python 3.14.4. f0 no usa ML, así que no afecta;
  el riesgo de wheels torch/sentence-transformers ya está registrado en
  design.md §8 para f3.
- __pycache__ existe en disco pero NO está trackeado por git (verificado
  con git ls-files); .gitignore lo cubre correctamente.

## Cambios requeridos
Ninguno.
