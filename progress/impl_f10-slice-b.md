# Implementación — f10-evaluation-harness · Slice B (de 2, final)

Feature: `f10-evaluation-harness` (status `in_progress`, spec aprobado por humano).
Entrega: 2 slices encadenados. **Este run implementa SOLO Slice B** (CLI / reporte
ejecutable + composición perezosa del orquestador real). Slice A (núcleo
determinista: dataset + métricas + runner + sus tests) ya aterrizó y está commiteado
(commit previo; ver `progress/impl_f10-slice-a.md` y `progress/review_f10-slice-a.md`).

Con Slice B, todas las tasks (T1–T11 + T-A-tests + T-B-tests + Z1) quedan `[x]`.

## Tasks completadas en este run (marcadas `[x]` en `specs/f10-evaluation-harness/tasks.md`)

- **T9** — Campo opcional `eval_dataset_path: str | None = None` en
  `src/wowrag/config.py` (R28). No altera ninguna clave existente; default sano
  (`None` → fixture commiteado); no exige entorno para el camino por defecto. La CLI
  lo usa como default cuando no se pasa `--dataset`.
- **T10** — CLI `src/wowrag/eval/cli.py` con `main(argv=None, orchestrator=None) ->
  int` + `src/wowrag/eval/__main__.py` (R24, R25, R26):
  - `argparse` con `--dataset` (default `None` → `eval_dataset_path` o fixture) y
    `--out` (artefacto JSON opcional).
  - `load_golden(dataset_path)` → `EvalHarness(orch).run(items)` → resumen stdout
    (`_format_summary`, R24) + `report.model_dump_json(indent=2)` a `--out` si se pide (R25).
  - **Composición perezosa (R26):** `_build_orchestrator()` hace
    `from wowrag.api.dependencies import build_orchestrator` DENTRO de la función
    (reúsa el punto de composición real de f9 — bge-m3 + pgvector + Ollama). Ningún
    import pesado al tope del módulo; `cli.py` usa `RagOrchestrator` solo bajo
    `TYPE_CHECKING`. `Settings` también se importa de forma perezosa dentro de
    `_default_dataset_path()`.
  - **Inyectable (R29):** cuando `main` recibe `orchestrator=`, `_build_orchestrator`
    nunca se alcanza → cero DB/ML/Ollama/red en el suite por defecto.
  - `__main__.py`: `raise SystemExit(main())` para que `python -m wowrag.eval` funcione (R24).
- **T11** — Finalizados los exports de `src/wowrag/eval/__init__.py`: se re-exporta
  `main` (CLI) junto al resto del conjunto público, con `__all__` (R30). El re-export
  de `main` es import-safe porque la composición real es perezosa dentro de
  `cli._build_orchestrator` → importar `wowrag.eval` sigue sin arrastrar
  torch/psycopg/httpx.
- **T-B-tests** — `tests/test_eval_cli.py` (10 tests, todos `not integration`, con
  `FakeOrchestrator` inyectado + `tmp_path`).
- **Z1** — Verificación final: `./init.sh` exit 0, suite `not integration` en verde
  (256 passed). `python -m wowrag.eval` corre contra el fixture (ver Sanity-check).

## Archivos creados

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `src/wowrag/eval/cli.py` | 121 | `main` + `_build_orchestrator` (lazy, reúsa f9) + `_format_summary` (R24-R26, R28) |
| `src/wowrag/eval/__main__.py` | 12 | `python -m wowrag.eval` → `cli.main()` (R24) |
| `tests/test_eval_cli.py` | 284 | 10 tests CLI (R24, R25, R26, R28-CLI, R30) |

## Archivos modificados

| Archivo | Cambio | Rol |
|---------|--------|-----|
| `src/wowrag/config.py` | +7 | campo opcional `eval_dataset_path` (R28) |
| `tests/test_config.py` | +12 | default-assert (`EXPECTED_DEFAULTS`) + env-override test de `eval_dataset_path` (R28) |
| `src/wowrag/eval/__init__.py` | ±10 (5 ins / 5 del) | re-exporta `main`; docstring actualizado (R30) |
| `specs/f10-evaluation-harness/tasks.md` | T9–T11, T-B-tests, Z1 → `[x]` | progreso |

## Archivos NO tocados (frontera respetada)

- `feature-list.json` — sin cambios (feature sigue `in_progress`; NO marcada `done` —
  es el paso post-review del leader/reviewer).
- `progress/current.md`, `progress/history.md` — territorio del leader; no tocados.
- Slice A: `src/wowrag/eval/{models,dataset,metrics,harness}.py`,
  `src/wowrag/eval/data/golden.jsonl` — NO modificados (solo importados; el runner de
  Slice A se reúsa via `from wowrag.eval.harness import EvalHarness`).
- f5–f9: `src/wowrag/{models,rag,llm,retrieval,generation,embeddings,store}/` —
  solo importados por interfaz; `build_orchestrator` de f9 reusado, no duplicado (R27).
- `requirements.txt` / `requirements-ml.txt` — sin dependencias nuevas (solo stdlib
  `argparse`/`pathlib`/`json` + pydantic ya presente).

## Trazabilidad R<n> → test (requisitos de Slice B: R24, R25, R26, R28, R30-final)

| R    | Test(s) |
|------|---------|
| R24  | `test_eval_cli.py::test_main_prints_summary`, `::test_main_runs_against_committed_fixture` (resumen stdout + retorna 0; entrypoint ejecutable) |
| R25  | `test_eval_cli.py::test_main_writes_json_artifact` (escribe `EvalReport` JSON en `--out`, round-trip), `::test_main_no_out_writes_no_file` (sin `--out` no escribe) |
| R26  | `test_eval_cli.py::test_main_does_not_build_real_orchestrator_when_injected` (inyectado → `_build_orchestrator` no se llama), `::test_import_eval_is_network_free` (subproceso: `import wowrag.eval` e `import wowrag.eval.cli` no arrastran torch/psycopg/httpx), `::test_build_orchestrator_reuses_f9_lazily` (delega en `build_orchestrator` de f9) |
| R28  | `test_config.py::test_eval_dataset_path_default_is_none_and_overridable` (default `None` + env-override), `test_config.py::test_settings_defaults_without_env`/`::test_settings_exposes_all_required_fields` (vía `EXPECTED_DEFAULTS`), `test_eval_cli.py::test_default_dataset_path_uses_settings` (la CLI usa el campo cuando falta `--dataset`) |
| R30 (final) | `test_eval_cli.py::test_exports` (todos los símbolos incl. `main` en `__all__` y accesibles), `::test_golden_item_export_is_usable`, `::test_import_eval_is_network_free` (paquete completo + CLI import-libre) |

### Confirmación: la feature completa R1–R30 está ahora cubierta (Slice A + Slice B)

- **R1–R21, R27, R29, R30-parcial** → cubiertos por Slice A
  (`tests/test_eval_dataset.py`, `tests/test_eval_metrics.py`,
  `tests/test_eval_harness.py`; ver `progress/impl_f10-slice-a.md` y la review aprobada).
- **R22, R23** → adelantados a Slice A (modelo `EvalReport` + `model_dump_json`),
  validados de nuevo en Slice B vía el artefacto `--out`
  (`test_main_writes_json_artifact` deserializa y comprueba campos agregados).
- **R24, R25, R26, R28, R30-final** → cubiertos por Slice B (tabla anterior).
- Resultado: **R1–R30 completos**, cada `R<n>` con ≥1 test en el suite por defecto
  (`pytest -m "not integration"`).

## Verificación

- Baseline `./init.sh` (antes de Slice B): **245 passed, 2 skipped, 5 deselected**, exit 0.
- Final `./init.sh` (después de Slice B): **256 passed, 2 skipped, 5 deselected**, exit 0,
  1 warning (StarletteDeprecationWarning del testclient de FastAPI, preexistente y
  ajeno a f10).
  - +11 tests nuevos (10 en `test_eval_cli.py` + 1 R28 en `test_config.py`), todos en
    el suite por defecto (`not integration`).
- **Aislamiento de imports (R16/R26):** `test_import_eval_is_network_free` corre en
  subproceso limpio (PYTHONPATH=src) y asegura que `import wowrag.eval` e
  `import wowrag.eval.cli` NO cargan torch/psycopg/httpx. Verificado también a mano:
  importar `wowrag.eval.cli` deja `sys.modules` libre de los tres.
- **Faithfulness por defecto = proxy determinista (sin LLM)** y el juez-LLM sigue
  opcional/fakeable (intacto de Slice A; Slice B no toca métricas).

## Sanity-check de la CLI (R24-R26)

- `main([], orchestrator=Fake())` contra el **fixture commiteado** (4 items):
  imprime el resumen completo (`items evaluated : 4`, `in-corpus 2`, `out-of-corpus 2`,
  `abstention recall 1.000`, `abstention prec. 0.500`) y retorna 0. (Faithfulness n/a
  porque el fake abstiene en todo → todos excluidos, R14.)
- `python -m wowrag.eval --dataset src/wowrag/eval/data/golden.jsonl` (sin inyección,
  camino real): dispatcha correctamente `__main__` → `cli.main` → `_build_orchestrator`
  → `build_orchestrator` de f9, y falla — **como se espera** — en la dependencia ML
  real (`EmbeddingError: FlagEmbedding is not installed`), confirmando que la
  composición pesada es genuinamente perezosa y solo se resuelve al ejecutar el script
  sin orquestador inyectado (R26). El fallo NO es de import/wiring, sino de servicio
  real ausente (sin `requirements-ml.txt` instalado en el venv por defecto).

## Conteo aproximado de líneas del slice

~446 líneas tocadas: producción ~140 (cli.py 121 + __main__.py 12 + __init__.py ±10
neto pequeño + config.py +7), tests ~296 (test_eval_cli.py 284 + test_config.py +12).
La producción casa con la estimación del design (~140 líneas para Slice B); el resto
es cobertura de tests.

## Desviaciones del spec

- **`print()` en la CLI:** `docs/conventions.md` prohíbe `print()` *para debug*, pero
  el design (§8) especifica `print(_format_summary(report))` como **salida de usuario**
  del script (stdout summary, R24). Se usa `print` solo para el resumen del reporte
  (output legítimo de una herramienta CLI), nunca para logging/debug. No es desviación
  de diseño — está prescrito en `design.md` §8.
- **T9: se eligió añadir el campo `eval_dataset_path`** (en vez de omitirlo y pasar la
  ruta solo por `--dataset`). El design (§9) deja ambas opciones como válidas para R28;
  añadir el campo da un default configurable por entorno y traza R28 con un test de
  config dedicado (default-assert + env-override), siguiendo la lección f5/f7 que el
  propio `test_config.py` documenta. No se modificó ninguna clave existente.
- **Tests extra sobre el mínimo del design:** se añadieron
  `test_main_runs_against_committed_fixture` (R24 contra el fixture real),
  `test_main_no_out_writes_no_file` (R25 borde), `test_build_orchestrator_reuses_f9_lazily`
  (R26 reuse explícito de f9), `test_default_dataset_path_uses_settings` (R28-CLI) y
  `test_golden_item_export_is_usable` (R30). Cobertura extra deseable, no defecto.
- Sin desviaciones de fórmula/lógica: Slice B no toca métricas/loader/runner; solo
  los compone en la CLI.

## Estado de la feature

Todas las tasks de f10 (T1–T11 + T-A-tests + T-B-tests + Z1) están `[x]`. La feature
permanece `in_progress` — el cambio a `done` y el movimiento del resumen a
`progress/history.md` corresponden al leader/reviewer tras validar la trazabilidad
`R<n>` ↔ test del slice final. Sugerencias de la review de Slice A atendidas:
`test_import_eval_is_network_free` cubre ahora `import wowrag.eval` E
`import wowrag.eval.cli` (R16/R26 a nivel paquete + CLI).
