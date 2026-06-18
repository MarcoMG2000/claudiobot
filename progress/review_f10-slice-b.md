# Review feature f10-evaluation-harness Slice B (de 2, FINAL gate)

Veredicto: APPROVED

Alcance: Slice B (CLI / reporte ejecutable + composicion perezosa: R22-R26, R28, R30-final) Y verificacion de cierre de la feature completa (R1-R30, Slice A + Slice B juntos). Slice A ya fue aprobado en progress/review_f10-slice-a.md; aqui NO se re-revisa en profundidad, pero SI se confirma que la union cubre R1-R30.

## ./init.sh
- exit 0, verde. 256 passed, 2 skipped, 5 deselected, 1 warning (StarletteDeprecationWarning del testclient de FastAPI; preexistente, ajena a f10).
- Coincide con la expectativa del gate (~256 passed / 2 skipped / 5 deselected).
- Baseline pre-Slice-B = 245 passed -> +11 tests (10 en test_eval_cli.py + 1 R28 en test_config.py), todos not integration.
- Ficheros f10 directos: 45 passed (cli 10, dataset 10, metrics 20, harness 5); collect-only = 45 colectados, 0 deselected, 0 skipped.

## Trazabilidad Slice B (R22-R26, R28, R30-final) vs tests que CORREN
- R22 [x] cli::test_main_writes_json_artifact (campos agregados) + Slice A harness::test_run_depends_only_on_protocol_and_produces_report.
- R23 [x] cli::test_main_writes_json_artifact (round-trip model_validate_json) + Slice A harness::test_report_json_serializable.
- R24 [x] cli::test_main_prints_summary (resumen + rc 0), test_main_runs_against_committed_fixture.
- R25 [x] cli::test_main_writes_json_artifact (escribe JSON en --out), test_main_no_out_writes_no_file (borde sin --out).
- R26 [x] cli::test_main_does_not_build_real_orchestrator_when_injected, test_import_eval_is_network_free (subproceso: import wowrag.eval e import wowrag.eval.cli sin torch/psycopg/httpx), test_build_orchestrator_reuses_f9_lazily.
- R28 [x] config::test_eval_dataset_path_default_is_none_and_overridable, test_settings_defaults_without_env, test_settings_exposes_all_required_fields; cli::test_default_dataset_path_uses_settings.
- R30 final [x] cli::test_exports (11 simbolos incl. main en __all__), test_golden_item_export_is_usable, test_import_eval_is_network_free.

## Cobertura R1-R30 de la feature completa (Slice A + Slice B)

Formato: R(n) [slice] -> test(s) -> OK

- R1 [A] dataset::test_golden_item_fields/_defaults/_blank_question_rejected -> [x]
- R2 [A] dataset::test_in_corpus_requires_expected_urls, test_load_golden_invalid_item_raises -> [x]
- R3 [A] dataset::test_out_of_corpus_rejects_expected_urls -> [x]
- R4 [A] dataset::test_load_golden_parses_jsonl/_tolerates_blank_lines/_malformed_json_raises/_invalid_item_raises -> [x]
- R5 [A] dataset::test_default_fixture_loads -> [x]
- R6 [A] harness::test_run_depends_only_on_protocol_and_produces_report -> [x]
- R7 [A] harness::test_run_calls_orchestrator_once_per_item -> [x]
- R8 [A] metrics::test_hit_rate_counts_url_intersection/_only_over_in_corpus_items -> [x]
- R9 [A] metrics::test_hit_rate_counts_url_intersection -> [x]
- R10 [A] metrics::test_hit_rate_none_when_no_in_corpus -> [x]
- R11 [A] metrics::test_hit_rate_only_from_sources -> [x]
- R12 [A] metrics::test_faithfulness_proxy_is_deterministic/_cited_and_high_overlap -> [x]
- R13 [A] metrics::test_faithfulness_proxy_cited/uncited/low_overlap/no_reference/in_range -> [x]
- R14 [A] metrics::test_faithfulness_excludes_abstained, test_faithfulness_proxy_mean_none_when_all_abstained -> [x]
- R15 [A] metrics::test_faithfulness_llm_judge_with_fake; harness::test_run_with_fake_judge_populates_llm_score -> [x]
- R16 [A+B] metrics::test_metrics_import_does_not_pull_heavy_backends, test_judge_uses_injected_provider_only; harness::test_run_no_judge_by_default_leaves_llm_none; cli::test_import_eval_is_network_free -> [x]
- R17 [A] metrics::test_faithfulness_llm_judge_with_fake/_skips_abstained (FakeLLMProvider) -> [x]
- R18 [A] metrics::test_abstention_precision_recall -> [x]
- R19 [A] metrics::test_abstention_precision_recall -> [x]
- R20 [A] metrics::test_abstention_recall_none_when_no_out_of_corpus, test_abstention_precision_none_when_no_abstentions -> [x]
- R21 [A] metrics::test_abstention_only_from_flag -> [x]
- R22 [A+B] harness::test_run_depends_only_on_protocol_and_produces_report; cli::test_main_writes_json_artifact -> [x]
- R23 [A+B] harness::test_report_json_serializable; cli::test_main_writes_json_artifact -> [x]
- R24 [B] cli::test_main_prints_summary, test_main_runs_against_committed_fixture -> [x]
- R25 [B] cli::test_main_writes_json_artifact, test_main_no_out_writes_no_file -> [x]
- R26 [B] cli::test_main_does_not_build_real_orchestrator_when_injected, test_import_eval_is_network_free, test_build_orchestrator_reuses_f9_lazily -> [x]
- R27 [A] diff vacio f5-f9/config/models vs HEAD; ejercitado via fakes -> [x]
- R28 [B] config::test_eval_dataset_path_default_is_none_and_overridable; cli::test_default_dataset_path_uses_settings -> [x]
- R29 [A+B] harness (FakeOrchestrator); cli (fake inyectado, sin DB/ML/Ollama/red) -> [x]
- R30 [B] cli::test_exports, test_golden_item_export_is_usable -> [x]

Sin gaps: los 30 requisitos R1-R30 tienen al menos 1 test que corre en pytest -m not integration.

## Tasks (specs/f10-evaluation-harness/tasks.md)
Todas [x] (ambos slices): T1-T8 + T-A-tests (Slice A); T9, T10, T11, T-B-tests, Z1 (Slice B). No queda ninguna [ ].

## Verificacion CLI (R24-R26) comprobada contra el codigo real
- main([], orchestrator=Fake()) contra el fixture commiteado (4 items): imprime resumen completo (items evaluated 4, in-corpus 2, out-of-corpus 2, excluded 2) y retorna 0. Verificado en vivo con un fake que cita expected_urls: hit-rate 1.000, faithfulness 1.000, abstencion prec/recall 1.000.
- --out escribe EvalReport.model_dump_json(indent=2); round-trip OK (model_validate_json). Artefacto JSON con los 9 campos verificado en vivo.
- argparse: --dataset (default None que cae a Settings.eval_dataset_path o fixture) y --out (None que no escribe). Exit code 0 en el camino feliz.
- python -m wowrag.eval (SIN inyeccion): dispatcha __main__ -> cli.main -> _build_orchestrator -> build_orchestrator de f9 y falla en BgeM3Embeddings (FlagEmbedding is not installed) NO en import/wiring. Prueba que la composicion pesada es genuinamente perezosa. El fallo es una excepcion de infraestructura clara (conforme a docs/conventions.md), no un defecto de Slice B.

## Aislamiento de imports (R16/R26) invariante de Slice A preservada
- Subproceso limpio (PYTHONPATH=src): import wowrag.eval + import wowrag.eval.cli deja sys.modules SIN torch/psycopg/psycopg2/httpx/FlagEmbedding/ollama. La nueva CLI no rompio la invariante: cli.py usa RagOrchestrator solo bajo TYPE_CHECKING; build_orchestrator se importa DENTRO de _build_orchestrator; Settings es lazy dentro de _default_dataset_path; __init__ re-exporta main (import-safe por la composicion lazy); __main__ solo importa cli.main.
- test_import_eval_is_network_free cubre paquete + CLI (atendida la sugerencia de la review de Slice A). Corre en subproceso y falla genuinamente si un backend pesado se importa eager; no es no-op.

## DI/testabilidad (R29)
- main(argv, orchestrator=...) es inyectable; con fake inyectado _build_orchestrator jamas se alcanza (test_main_does_not_build_real_orchestrator_when_injected, monkeypatch a _boom). Todo el suite por defecto pasa un fake: CERO DB/ML/Ollama/red.

## Alcance (scope)
- Diff vs HEAD en src/: SOLO config.py (+7, campo nuevo eval_dataset_path, puramente aditivo, ninguna clave existente alterada) y eval/__init__.py (re-export de main). Nuevos: eval/cli.py, eval/__main__.py. NINGUN modulo de f5-f9 tocado.
- build_orchestrator de f9 reusado, no duplicado (DRY, R26/R27). api/dependencies.py no modificado.
- Sin dependencias nuevas en el camino por defecto (stdlib argparse/pathlib/json + pydantic ya presente). requirements txt no tocados.
- Faithfulness por defecto = proxy determinista (Slice A intacto); juez-LLM sigue opcional/fakeable. Slice B no toca metricas/loader/runner.
- print() en cli._format_summary es salida legitima de una herramienta CLI (stdout summary, R24), prescrita en design.md seccion 8; NO es print() de debug. Conforme.

## Checkpoints
- C1 [x] arnes base presente; ./init.sh exit 0.
- C2 [x] una sola feature in_progress (f10); resto done/pending; progress/current.md describe la sesion.
- C3 [x] capas respetadas (eval/ paquete propio como index/); servicios externos tras interfaz (lazy via build_orchestrator); sin print() de debug ni secretos en codigo nuevo; requirements pineados sin cambios.
- C4 [x] un fichero de test por modulo de eval/ (cli incluido); logica con fakes (FakeOrchestrator, FakeLLMProvider); pytest -m not integration > 0 y verde (256).
- C5 [x] grounding ejercitado via metrica: abstencion (R18-R21), citas/hit-rate (R8-R11), faithfulness proxy (R12-R14).
- C6 [x] f10 (sdd:true) con specs/ (3 docs), requirements en EARS, TODAS las tasks [x], cada R1-R30 con al menos 1 test que corre. Lista para done.

## Cambios requeridos
Ninguno. Slice B cumple su alcance (R22-R26, R28, R30-final); la union Slice A+B cubre R1-R30 sin gaps; todas las tasks [x]; ./init.sh verde (256 passed); CLI correcta; composicion perezosa y aislamiento de imports preservados; fronteras f5-f9 intactas. APROBADO: gate final de la feature. El cierre (done + mover resumen a progress/history.md + actualizar feature-list.json) corresponde al leader/humano.
