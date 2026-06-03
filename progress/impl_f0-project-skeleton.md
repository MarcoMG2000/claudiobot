# Implementación — f0-project-skeleton

- **Feature:** `f0-project-skeleton` — Project skeleton & configuration system.
- **Estado:** implementación completa, pendiente de review. NO marcada `done`.
- **Fecha:** 2026-06-03

## Tasks cubiertas en esta sesión

T1–T10 ya estaban implementadas (código + tests) pero sin marcar. Verifiqué
que cada artefacto existe y pasa antes de marcarlas. Tasks nuevas de esta
sesión:

- **T11** — Creado `tests/test_requirements_pinned.py` (R13): afirma que
  `pydantic-settings`, `pyyaml` y `pytest` están pineados con `==`, y que
  `fastapi`/`uvicorn`/`torch`/`sentence-transformers`/`psycopg` no aparecen.
- **T12** — Creado `tests/test_repo_hygiene.py` (R14): afirma que `.gitignore`
  contiene `.env`, `.venv`, `__pycache__`, y que `.env.example` existe y
  documenta los 8 campos de R5.
- **T13** — Verificación con `./init.sh`.

Verifiqué previamente que `requirements.txt`, `.gitignore` y `.env.example` ya
satisfacían las aserciones de T11/T12 — no requirieron ajustes (sin desviación
del spec).

Todas las tasks T1–T13 quedan marcadas `[x]` en `tasks.md`.

## Trazabilidad R<n> ↔ test

| R    | Test (fichero::función) |
|------|--------------------------|
| R1   | `tests/test_package_imports.py::test_import_wowrag_succeeds`, `::test_top_level_exports_present` |
| R2   | `tests/test_package_imports.py::test_placeholder_subpackages_import` |
| R3   | `tests/test_config.py::test_settings_defaults_without_env` |
| R4   | `tests/test_config.py::test_env_var_overrides_default`, `::test_env_var_takes_priority_over_env_file` |
| R5   | `tests/test_config.py::test_settings_defaults_without_env`, `::test_settings_exposes_all_required_fields` |
| R6   | `tests/test_config.py::test_reads_values_from_env_file`, `::test_env_var_takes_priority_over_env_file` |
| R7   | `tests/test_personas.py::test_load_simple_persona_returns_persona` |
| R8   | `tests/test_personas.py::test_load_simple_persona_returns_persona` |
| R9   | `tests/test_personas.py::test_unknown_persona_raises_with_name` |
| R10  | `tests/test_personas.py::test_load_simple_persona_returns_persona`, `::test_all_bundled_personas_load` |
| R11  | `tests/test_personas.py::test_orc_persona_has_zug_zug` |
| R12  | `tests/test_personas.py::test_default_persona_resolves_from_settings`, `::test_default_persona_uses_default_setting` |
| R13  | `tests/test_requirements_pinned.py::test_required_dependencies_are_pinned`, `::test_deferred_dependencies_absent` |
| R14  | `tests/test_repo_hygiene.py::test_gitignore_ignores_secrets_and_caches`, `::test_env_example_exists_and_documents_r5_fields` |

Los 14 requisitos (R1–R14) están cubiertos por al menos un test.

## Resultado de `./init.sh`

- **Tests:** 26 passed (suite no-integration).
- **Exit code:** 0.
- Python del entorno: 3.14.4.

## Próximo paso

Reviewer valida trazabilidad y tasks. El cierre a `done` lo decide el flujo
tras el review; no se marca aquí.
