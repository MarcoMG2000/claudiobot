# Implementación — f10-evaluation-harness · Slice A (de 2)

Feature: `f10-evaluation-harness` (status `in_progress`, spec aprobado por humano).
Entrega: 2 slices encadenados. **Este run implementa SOLO Slice A** (núcleo
determinista: dataset + métricas + runner + sus tests). Slice B (CLI/reporte
ejecutable + composición perezosa) NO se ha tocado.

## Tasks completadas (marcadas `[x]` en `specs/f10-evaluation-harness/tasks.md`)

- **T1** — `GoldenItem` en `src/wowrag/eval/models.py` (campos + validadores R1/R2/R3).
- **T2** — `load_golden` + `GoldenDatasetError` en `src/wowrag/eval/dataset.py` (R4).
- **T3** — fixture commiteado `src/wowrag/eval/data/golden.jsonl` (R5).
- **T4** — `retrieval_hit_rate` + `abstention_scores` en `src/wowrag/eval/metrics.py`
  (R8, R9, R10, R11, R18, R19, R20, R21).
- **T5** — `faithfulness_proxy` / `faithfulness_proxy_mean` + `STOPWORDS` + tokenizador
  en `metrics.py` (R12, R13, R14). Helper `count_excluded_abstained` para R14.
- **T6** — `faithfulness_llm_judge` (hook juez-LLM opcional, inyectado) en `metrics.py`
  (R15, R16, R17). No importa `OllamaLLM`; usa `LLMProvider` vía `TYPE_CHECKING`.
- **T7** — `EvalReport` en `eval/models.py` (R22, R23).
- **T8** — `EvalHarness` en `src/wowrag/eval/harness.py` (R6, R7, R27, R29) + exports
  parciales en `src/wowrag/eval/__init__.py` (R30 parcial; CLI se añade en Slice B).
- **T-A-tests** — `tests/test_eval_dataset.py`, `tests/test_eval_metrics.py`,
  `tests/test_eval_harness.py` (trazabilidad `R<n>` ↔ test).

Slice B (T9, T10, T11, T-B-tests, Z1) quedan sin marcar — NO es este run.

## Archivos creados

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `src/wowrag/eval/__init__.py` | 39 | re-exports públicos (R30 parcial) |
| `src/wowrag/eval/models.py` | 69 | `GoldenItem` (R1-R3), `EvalReport` (R22-R23) |
| `src/wowrag/eval/dataset.py` | 62 | `load_golden`, `GoldenDatasetError` (R4) |
| `src/wowrag/eval/metrics.py` | 217 | 3 métricas + hook juez-LLM (R8-R21) |
| `src/wowrag/eval/harness.py` | 72 | `EvalHarness` (R6, R7, R27, R29) |
| `src/wowrag/eval/data/golden.jsonl` | 4 | fixture in-corpus + fuera-de-corpus (R5) |
| `tests/test_eval_dataset.py` | 153 | esquema + loader |
| `tests/test_eval_metrics.py` | 302 | 3 métricas + juez con fake + import-libre |
| `tests/test_eval_harness.py` | 140 | runner E2E con `FakeOrchestrator` |

(No se creó `data/__init__.py`: `data/` es un directorio de datos, no un paquete;
`load_golden` lo resuelve con `Path(__file__).parent / "data" / "golden.jsonl"`,
igual que `personas/*.yaml`.)

## Archivos modificados (fuera de src/tests)

- `specs/f10-evaluation-harness/tasks.md` — marcadas `[x]` las tasks de Slice A.

## Archivos NO tocados (frontera respetada)

- `feature-list.json` — sin cambios (feature sigue `in_progress`; no marcada `done`).
- `progress/current.md`, `progress/history.md` — territorio del leader; no tocados.
- `src/wowrag/config.py` — sin cambios (`git diff` vacío). No hizo falta
  `eval_dataset_path` en Slice A (sólo lo usaría la CLI de Slice B; R28).
- `src/wowrag/models.py`, `src/wowrag/rag/`, `src/wowrag/llm/`,
  `src/wowrag/retrieval/`, `src/wowrag/generation/` — sólo importados, no
  modificados (R27).
- Slice B NO creado: no existe `eval/cli.py`, `eval/__main__.py`,
  `tests/test_eval_cli.py`. No hay wiring de `build_orchestrator`.

## Trazabilidad R<n> → test (requisitos de Slice A: R1–R21, R27, R29, R30 parcial)

| R    | Test(s) |
|------|---------|
| R1   | `test_eval_dataset.py::test_golden_item_fields`, `::test_golden_item_defaults`, `::test_golden_item_blank_question_rejected` |
| R2   | `test_eval_dataset.py::test_in_corpus_requires_expected_urls` (+ `::test_load_golden_invalid_item_raises`) |
| R3   | `test_eval_dataset.py::test_out_of_corpus_rejects_expected_urls` |
| R4   | `test_eval_dataset.py::test_load_golden_parses_jsonl`, `::test_load_golden_tolerates_blank_lines`, `::test_load_golden_malformed_json_raises`, `::test_load_golden_invalid_item_raises` |
| R5   | `test_eval_dataset.py::test_default_fixture_loads` |
| R6   | `test_eval_harness.py::test_run_depends_only_on_protocol_and_produces_report` (FakeOrchestrator = sólo Protocol) |
| R7   | `test_eval_harness.py::test_run_calls_orchestrator_once_per_item` |
| R8   | `test_eval_metrics.py::test_hit_rate_counts_url_intersection`, `::test_hit_rate_only_over_in_corpus_items` |
| R9   | `test_eval_metrics.py::test_hit_rate_counts_url_intersection` |
| R10  | `test_eval_metrics.py::test_hit_rate_none_when_no_in_corpus` |
| R11  | `test_eval_metrics.py::test_hit_rate_only_from_sources` |
| R12  | `test_eval_metrics.py::test_faithfulness_proxy_is_deterministic`, `::test_faithfulness_proxy_cited_and_high_overlap` |
| R13  | `test_eval_metrics.py::test_faithfulness_proxy_cited_and_high_overlap`, `::test_faithfulness_proxy_uncited_is_low`, `::test_faithfulness_proxy_low_overlap_is_low`, `::test_faithfulness_proxy_no_reference_degrades_to_citation`, `::test_faithfulness_proxy_in_range` |
| R14  | `test_eval_metrics.py::test_faithfulness_excludes_abstained`, `::test_faithfulness_proxy_mean_none_when_all_abstained` |
| R15  | `test_eval_metrics.py::test_faithfulness_llm_judge_with_fake`, `::test_judge_uses_injected_provider_only`; `test_eval_harness.py::test_run_with_fake_judge_populates_llm_score` |
| R16  | `test_eval_metrics.py::test_metrics_import_does_not_pull_heavy_backends`, `::test_judge_uses_injected_provider_only`; `test_eval_harness.py::test_run_no_judge_by_default_leaves_llm_none` |
| R17  | `test_eval_metrics.py::test_faithfulness_llm_judge_with_fake`, `::test_faithfulness_llm_judge_skips_abstained` |
| R18  | `test_eval_metrics.py::test_abstention_precision_recall` |
| R19  | `test_eval_metrics.py::test_abstention_precision_recall` |
| R20  | `test_eval_metrics.py::test_abstention_recall_none_when_no_out_of_corpus`, `::test_abstention_precision_none_when_no_abstentions` |
| R21  | `test_eval_metrics.py::test_abstention_only_from_flag` |
| R22  | `test_eval_harness.py::test_run_depends_only_on_protocol_and_produces_report` |
| R23  | `test_eval_harness.py::test_report_json_serializable` |
| R27  | implícito: f5–f9 sólo importados, no modificados (`git diff` de `config.py`/`models.py`/`rag/` vacío); ejercitado por `FakeOrchestrator`/`FakeLLMProvider` |
| R29  | `test_eval_harness.py` completo (FakeOrchestrator, sin red); `test_eval_metrics.py::test_metrics_import_does_not_pull_heavy_backends` |
| R30 (parcial) | `test_eval_dataset.py` + `test_eval_harness.py` importan `GoldenItem`, `load_golden`, `GoldenDatasetError`, `EvalHarness`, `EvalReport` desde `wowrag.eval`. (R30 final con símbolos de CLI = Slice B.) |

R22/R23: cubiertos por el modelo `EvalReport` (T7) ya en Slice A, validados vía el
runner. Los conteos del reporte (in_corpus/out_of_corpus/excluded_abstained) se
verifican en `test_run_depends_only_on_protocol_and_produces_report`.

## Verificación

- Baseline `./init.sh` (antes de implementar): **210 passed, 2 skipped, 5 deselected**, exit 0.
- Final `./init.sh` (después de Slice A): **245 passed, 2 skipped, 5 deselected**, exit 0.
  - +35 tests nuevos de Slice A, todos en la suite por defecto (`not integration`).
- `import wowrag.eval` / `import wowrag.eval.metrics` NO arrastran torch/psycopg/httpx
  (verificado en subproceso limpio, `test_metrics_import_does_not_pull_heavy_backends`).
- Faithfulness por defecto = proxy determinista (sin LLM). Juez-LLM opcional,
  inyectado y fakeable; no se definió variante `@integration` contra Ollama real en
  Slice A (es un hook puro testeado con `FakeLLMProvider`/stub — sin red; la variante
  real `@integration` puede añadirse junto a la CLI en Slice B sin tocar el default).

## Desviaciones del spec

- **Subproceso para R16** (`test_metrics_import_does_not_pull_heavy_backends`): el
  test corre en un subproceso limpio porque la sesión de pytest ya carga
  `wowrag.llm.ollama` indirectamente (el `__init__` del paquete `wowrag.llm`
  importa `OllamaLLM`). El subproceso necesita `PYTHONPATH=src` (pytest usa
  `pythonpath=["src"]`, pero `wowrag` NO está instalado en el venv); el test lo
  inyecta vía `env`. Esto verifica el contrato real de R16 (no arrastrar deps
  pesadas) mejor que comprobar `sys.modules` dentro de la sesión de pytest.
- **`count_excluded_abstained`** se expuso como función aparte en `metrics.py` para
  que `EvalHarness` rellene `EvalReport.excluded_abstained` de forma trazable (el
  design dejaba al implementer elegir dónde calcular los conteos; §7).
- Sin desviaciones de diseño en métricas/loader/runner: fórmulas, normalización y
  bordes `None` exactamente como en `design.md` §5.

## Pendiente (Slice B, NO en este run)

T9 (campo opcional `eval_dataset_path`), T10 (`cli.py` + `__main__.py`, composición
perezosa con `build_orchestrator` de f9), T11 (finalizar exports), T-B-tests
(`test_eval_cli.py`), Z1 (verificación integral R1–R30). La feature permanece
`in_progress` hasta que ambos slices aterricen y el reviewer apruebe.
