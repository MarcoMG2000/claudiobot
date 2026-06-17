# Review - feature f10-evaluation-harness - Slice A (de 2)

**Veredicto:** APPROVED

Alcance revisado: SOLO Slice A (nucleo determinista: dataset + metricas + runner + tests). Slice B (CLI/reporte/composicion perezosa: R22-R26 entrypoint, R28, R30-final) NO esta en este slice y NO se evalua para aprobacion aqui. La feature permanece in_progress hasta que ambos slices aterricen.

## ./init.sh
- exit 0, verde. 245 passed, 2 skipped, 5 deselected, 1 warning (StarletteDeprecationWarning del testclient de FastAPI, preexistente y ajena a f10). Baseline pre-slice 210 passed -> +35 tests nuevos, todos not integration.
- pytest de los 3 ficheros f10 directamente -> 35 passed en 0.35s, coleccion OK, sin red.

## Trazabilidad requirements <-> tests (Slice A: R1-R21, R27, R29, R30-parcial)

Todos verificados como tests que CORREN en la suite por defecto (ninguno skip ni deselect).

- R1: [x] test_eval_dataset.py::test_golden_item_fields, ::test_golden_item_defaults, ::test_golden_item_blank_question_rejected
- R2: [x] test_eval_dataset.py::test_in_corpus_requires_expected_urls, ::test_load_golden_invalid_item_raises
- R3: [x] test_eval_dataset.py::test_out_of_corpus_rejects_expected_urls
- R4: [x] test_eval_dataset.py::test_load_golden_parses_jsonl, ::test_load_golden_tolerates_blank_lines, ::test_load_golden_malformed_json_raises, ::test_load_golden_invalid_item_raises (verifican num de linea 1-based)
- R5: [x] test_eval_dataset.py::test_default_fixture_loads (fixture commiteado, >=1 in-corpus + >=1 fuera-de-corpus)
- R6: [x] test_eval_harness.py::test_run_depends_only_on_protocol_and_produces_report (FakeOrchestrator = solo metodo answer, Protocol estructural)
- R7: [x] test_eval_harness.py::test_run_calls_orchestrator_once_per_item (spy calls == items, en orden)
- R8: [x] test_eval_metrics.py::test_hit_rate_counts_url_intersection, ::test_hit_rate_only_over_in_corpus_items
- R9: [x] test_eval_metrics.py::test_hit_rate_counts_url_intersection
- R10: [x] test_eval_metrics.py::test_hit_rate_none_when_no_in_corpus
- R11: [x] test_eval_metrics.py::test_hit_rate_only_from_sources
- R12: [x] test_eval_metrics.py::test_faithfulness_proxy_is_deterministic, ::test_faithfulness_proxy_cited_and_high_overlap
- R13: [x] test_eval_metrics.py::test_faithfulness_proxy_cited_and_high_overlap, ::test_faithfulness_proxy_uncited_is_low, ::test_faithfulness_proxy_low_overlap_is_low, ::test_faithfulness_proxy_no_reference_degrades_to_citation, ::test_faithfulness_proxy_in_range
- R14: [x] test_eval_metrics.py::test_faithfulness_excludes_abstained, ::test_faithfulness_proxy_mean_none_when_all_abstained
- R15: [x] test_eval_metrics.py::test_faithfulness_llm_judge_with_fake, ::test_judge_uses_injected_provider_only; test_eval_harness.py::test_run_with_fake_judge_populates_llm_score
- R16: [x] test_eval_metrics.py::test_metrics_import_does_not_pull_heavy_backends (subproceso), ::test_judge_uses_injected_provider_only; test_eval_harness.py::test_run_no_judge_by_default_leaves_llm_none
- R17: [x] test_eval_metrics.py::test_faithfulness_llm_judge_with_fake, ::test_faithfulness_llm_judge_skips_abstained (FakeLLMProvider; sin red)
- R18: [x] test_eval_metrics.py::test_abstention_precision_recall
- R19: [x] test_eval_metrics.py::test_abstention_precision_recall
- R20: [x] test_eval_metrics.py::test_abstention_recall_none_when_no_out_of_corpus, ::test_abstention_precision_none_when_no_abstentions
- R21: [x] test_eval_metrics.py::test_abstention_only_from_flag
- R27: [x] diff vacio de config.py/models.py/rag/ vs HEAD (solo importados); ejercitado por FakeOrchestrator/FakeLLMProvider
- R29: [x] test_eval_harness.py completo (FakeOrchestrator, sin red) + test_metrics_import_does_not_pull_heavy_backends
- R30 (parcial): [x] test_eval_dataset.py / test_eval_harness.py importan GoldenItem, load_golden, GoldenDatasetError, EvalHarness, EvalReport desde wowrag.eval. (R30-final con simbolos CLI = Slice B.)

R22/R23 son tecnicamente Slice B en el mapping del acceptance, pero EvalReport (T7) se adelanto a Slice A y esta cubierto:
- R22: [x] test_eval_harness.py::test_run_depends_only_on_protocol_and_produces_report (campos agregados + conteos)
- R23: [x] test_eval_harness.py::test_report_json_serializable (model_dump_json + round-trip model_validate_json)

Requirements de Slice B fuera de este slice (NO evaluados): R24, R25, R26 (entrypoint CLI/composicion perezosa), R28 (campo config opcional), R30-final. Correctamente ausentes.

## Tasks (specs/f10-evaluation-harness/tasks.md)

Slice A - todas [x]: T1 GoldenItem (R1-R3), T2 load_golden+GoldenDatasetError (R4), T3 fixture golden.jsonl (R5), T4 retrieval_hit_rate+abstention_scores (R8-R11, R18-R21), T5 faithfulness proxy+STOPWORDS+tokenizador (R12-R14), T6 faithfulness_llm_judge hook (R15-R17), T7 EvalReport (R22-R23), T8 EvalHarness + exports parciales (R6,R7,R27,R29,R30-parcial), T-A-tests (3 ficheros).

Slice B - correctamente [ ] (no es este run): T9, T10, T11, T-B-tests, Z1. Sin tasks de Slice A en [ ]. Conforme a la entrega encadenada aprobada.

## Verificacion de la matematica de metricas (contra el codigo, no el reporte)

- hit-rate (metrics.py:53-73): hit = set(item.expected_urls) interseccion {s.url for s in answer.sources} no vacio (URL exacta) - R9 OK. Fraccion hits/len(in_corpus) SOLO sobre item.in_corpus is True - R8 OK. None si no hay in-corpus - R10 OK. Derivado solo de answer.sources - R11 OK.
- faithfulness proxy (metrics.py:80-121): 0.5*cited + 0.5*overlap; cited=1.0 si len(sources)>=1. overlap = (tokens(answer) interseccion tokens(reference)) / |tokens(reference)| -> direccion correcta (tokens de la REFERENCIA cubiertos por la respuesta, R13b). Tokenizacion [a-z0-9]+, minusculas, menos STOPWORDS (frozenset bilingue modulo-constante) - R13 OK. Sin reference_answer -> degrada a cited - R13b OK. Rango [0,1] garantizado. Abstenidos EXCLUIDOS en faithfulness_proxy_mean (if not ans.abstained) y None si todos abstuvieron - R14 OK. count_excluded_abstained separado - R14 OK. Edge verificado en vivo: reference_answer solo-stopwords -> ref_tokens vacio -> fallback a cited (sin ZeroDivision); score 1.0 cuando citado. Robusto.
- abstencion (metrics.py:133-161): recall = correct_abst/out_of_corpus, precision = correct_abst/abstained; correct_abst = items fuera-de-corpus con answer.abstained True (R18). recall=None si no hay fuera-de-corpus; precision=None si nada abstuvo (R20). Solo de answer.abstained (R21). Formulas exactas como design.md 5.3. Sin desviaciones de formula.

## Evaluacion de aislamiento de imports (R16)

- import wowrag.eval (paquete completo, incl. harness) NO arrastra torch/psycopg/httpx - verificado en proceso limpio (sys.modules vacio de los tres). metrics.py/harness.py usan LLMProvider/RagOrchestrator solo bajo TYPE_CHECKING; el juez recibe LLMProvider inyectado, nunca instancia OllamaLLM (solo lo menciona en docstring).
- El test por subproceso (PYTHONPATH=src) es solido y NO es un no-op:
  1) wowrag.llm.__init__ importa OllamaLLM eager (verificado), asi que en la sesion de pytest sys.modules puede estar contaminado; subproceso limpio es la unica forma fiable de aislar el contrato.
  2) PYTHONPATH=src necesario porque wowrag no esta instalado en el venv (pytest usa pythonpath=[src], que no aplica fuera de pytest).
  3) Falla genuinamente si un backend pesado se importa eager: reproducido a mano anadiendo import httpx antes de import wowrag.eval.metrics -> AssertionError [httpx], exit 1. No es un no-op.
  - Observacion menor (no bloqueante): la asercion mira wowrag.eval.metrics, no wowrag.eval; comprobe a mano que el paquete completo tambien queda limpio. En Slice B conviene que el test R16/R26 cubra import wowrag.eval e import wowrag.eval.cli (ya planificado en test_import_eval_is_network_free).

## Verificacion de alcance (scope)

- NO hay LLM en el camino por defecto de metricas: faithfulness default = proxy determinista; juez-LLM hook opcional, inyectado, fakeable. OK.
- NO se anaden dependencias nuevas al camino por defecto (solo stdlib re, json, pathlib + pydantic ya presente). requirements.txt no tocado. OK.
- config.py, models.py, rag/, llm/, retrieval/, generation/: diff vacio vs HEAD - solo importados, no modificados (R27, R28-respetado). OK.
- Modelos de f10 en wowrag/eval/, NO en models.py global (architecture 6; precedente index/). Paquete propio eval/. OK.
- Archivos de Slice B AUSENTES: eval/cli.py, eval/__main__.py, tests/test_eval_cli.py no existen; sin wiring de build_orchestrator. OK.
- golden.jsonl empaquetado y resuelto via Path(__file__).parent (sin data/__init__.py, igual que personas/*.yaml). OK.
- Sin print() de debug en src/wowrag/eval/. OK.

## Observacion de tamano (NO bloqueante - el humano aprobo el plan de 2 slices)

El slice llego mas grande que la estimacion ~430 lineas: ~1058 lineas anadidas (~463 de produccion en eval/ + ~595 de tests: dataset 153, metrics 302, harness 140). El exceso es esencialmente test-coverage extra (mas casos por R<n> que el minimo del design), deseable, no un defecto. Se reporta como dato para el leader/humano; NO motiva rechazo. Sugerencia: mantener Slice B cerca de su ~140 lineas.

## Checkpoints (relevantes a esta feature/slice)

- C1: [x] arnes base presente; ./init.sh exit 0.
- C2: [x] una sola feature in_progress (f10); progress/current.md describe la sesion.
- C3: [x] respeta capas (eval/ paquete propio, como index/); servicios externos tras interfaz; sin print()/secretos en codigo nuevo. requirements.txt sin cambios (no aplica a este slice).
- C4: [x] un fichero de test por modulo de eval/ (dataset+models, metrics, harness+__init__); logica con fakes (FakeOrchestrator, FakeLLMProvider), sin Postgres/Ollama/red; pytest not integration > 0 y verde.
- C5: [x] grounding ejercitado via metrica: abstencion (R18-R21), citas/hit-rate (R8-R11), faithfulness proxy (R12-R14). Contrato real es f5-f8 (done); f10 lo MIDE.
- C6: [x] f10 (sdd:true) tiene specs/ con 3 docs; requirements en EARS; tasks de Slice A [x]; cada R<n> de Slice A con >=1 test. Tasks Slice B [ ] y R22-R30-final pendientes correctos: la feature NO esta done.

## Cambios requeridos

Ninguno bloqueante. Sugerencias menores para Slice B (no condicionan esta aprobacion):
1. test_import_eval_is_network_free (Slice B) deberia cubrir import wowrag.eval e import wowrag.eval.cli libres de torch/psycopg/httpx (R16/R26 a nivel paquete + CLI).
2. Considerar la variante @pytest.mark.integration del juez-LLM contra Ollama real junto a la CLI (R17 menciona la variante real); en Slice A el hook se valida solo con fake/stub, suficiente para el default.

Conclusion: Slice A cumple su alcance (R1-R21, R27, R29, R30-parcial; + R22/R23 adelantados), con trazabilidad completa, formulas correctas, aislamiento de imports solido y fronteras respetadas. ./init.sh verde. APROBADO.
