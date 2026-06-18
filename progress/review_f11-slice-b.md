# Review feature f11-wowhead-ingestion - Slice B (FINAL gate, re-review)

Veredicto: APPROVED

Alcance: Slice B de 2 (final) = normalizador + pipeline + CLI (T7-T11 + T-B-tests + Z1).
Puerta FINAL: se valida que Slice A union Slice B cubre R1-R31 con cobertura EFECTIVA.

Re-revision tras el change-round 1. El veredicto previo fue CHANGES_REQUESTED por un
hueco UNICO: selectolax estaba aislado en requirements-scrape.txt (no instalado por
init.sh), dejando los 7 tests parser-backed en estado skipped en CI, con R12/R14/R15/R16
y el round-trip real R20 sin cobertura efectiva (R29 incumplido en la parte central). El
implementer aplico la correccion recomendada al pie de la letra. El hueco esta RESUELTO.

---

## Hueco de selectolax: RESUELTO

La correccion del reviewer se aplico exactamente:

1. selectolax==0.4.10 MOVIDO a requirements.txt (pineado con ==), comentario que cita el
   precedente f9 (requirements.txt:11-17). init.sh ahora lo instala.
2. requirements-scrape.txt ELIMINADO (git status: D requirements-scrape.txt). Solo
   contenia selectolax; httpx ya estaba en requirements.txt desde f9.
3. test_requirements_pinned.py: selectolax movido a PINNED (l.24); comentario actualizado
   (l.11-16); torch/sentence-transformers/psycopg siguen en DEFERRED (l.26). 2 passed.
4. Quitados los importorskip de selectolax de los 7 tests parser-backed:
   - normalizer fixture (test_wowhead_normalizer.py:29-32, sin guard): 5 tests corren.
   - test_wowhead_pipeline.py::test_run_with_real_normalizer_roundtrips (l.250): corre.
   - test_wowhead_cli.py::test_main_end_to_end_with_real_normalizer (l.185): corre.
   El marker integration se MANTIENE solo en test_live_fetch_respects_robots (R30).
5. normalizer.py: el mensaje de ScrapeError ahora apunta a pip install -r requirements.txt
   (l.76-79). El import de selectolax SIGUE siendo lazy dentro de __init__ (l.73-74, R25) y
   eleva ScrapeError si falta (R31). Logica intacta.

### Estado verificado en venv FRESCO (no contaminado)

Borre .venv por completo y ejecute bash ./init.sh desde cero. init.sh creo el venv,
instalo requirements.txt (incluido selectolax) y corrio pytest excluyendo integration:

  297 passed, 2 skipped, 6 deselected, 1 warning (exit 0)

Coincide EXACTO con lo esperado. Confirmaciones:

- pip show selectolax: 0.4.10, instalado por init.sh (no a mano; el venv se borro).
- Los 2 skipped restantes son LEGITIMOS y ajenos a f11:
  - test_embeddings_bge_m3.py:23 (FlagEmbedding ausente, f3).
  - test_store_pgvector.py:29 (psycopg ausente, f4).
  CERO tests de f11 quedan skipped por falta de selectolax.
- Los 6 deselected: 5 de test_llm_ollama.py (integration, f7) + 1 de
  test_wowhead_pipeline.py::test_live_fetch_respects_robots (integration, f11 R30).
- 1 warning = StarletteDeprecationWarning preexistente de f9. Sin warnings nuevos.

### Los 7 tests antes-skipped ahora CORREN y PASAN (pytest -v)

Confirmado individualmente (20 passed, 1 deselected en el subconjunto Slice B):
- normalizer::test_normalize_populates_document_fields  PASSED  (R12,R13,R14,R15)
- normalizer::test_boilerplate_stripped                 PASSED  (R12)
- normalizer::test_section_empty_when_absent            PASSED  (R15)
- normalizer::test_title_falls_back_to_title_tag        PASSED  (R14)
- normalizer::test_empty_body_returns_none              PASSED  (R16 decision)
- pipeline::test_run_with_real_normalizer_roundtrips    PASSED  (R12-R15,R19,R20 real)
- cli::test_main_end_to_end_with_real_normalizer        PASSED  (R22,R20 real)

Ninguno skipped, ninguno deselected (salvo el integration de R30). El nucleo de f11
(HTML a Document) ahora SI se ejercita en CI. R29 cumplido tambien en la parte parser-backed.

---

## Trazabilidad requirements a tests (R1-R31) - TODA cobertura EFECTIVA (no skipped)

Verificado en venv fresco; todos los tests listados CORREN y PASAN en init.sh
(salvo R30, intencionalmente integration/deselected).

### Slice A (en main, corren por defecto)
- R1: [x] test_wowhead_fetcher.py (Protocol / FakeFetcher)
- R2: [x] test_wowhead_fetcher.py::test_httpx_fetcher_sets_user_agent
- R3: [x] test_wowhead_fetcher.py::test_httpx_fetcher_missing_dep_raises_fetcherror
- R4: [x] test_wowhead_fetcher.py (FakeFetcher mapea)
- R5: [x] test_wowhead_robots.py::test_allows_when_robots_permits (+ orden pipeline)
- R6: [x] robots (disallowed nunca fetched); pipeline::test_disallowed_and_off_allowlist_skipped
- R7: [x] test_wowhead_robots.py::test_robots_cached_per_host
- R8: [x] test_wowhead_throttle.py::test_first_acquire_no_wait
- R9: [x] test_wowhead_throttle.py::test_second_acquire_within_interval_sleeps
- R10: [x] fetcher::test_httpx_fetcher_sets_user_agent; test_config.py
- R11: [x] test_wowhead_throttle.py::test_acquire_uses_injected_clock

### Slice B (todas EFECTIVAS ahora - antes skipped)
- R12: [x] normalizer::test_normalize_populates_document_fields, ::test_boilerplate_stripped;
  pipeline::test_run_with_real_normalizer_roundtrips. CORREN.
- R13: [x] normalizer::test_normalize_populates_document_fields (source_url);
  pipeline::test_output_roundtrips_through_jsonl_loader. CORREN.
- R14: [x] normalizer::test_normalize_populates_document_fields (h1),
  ::test_title_falls_back_to_title_tag (title). CORREN.
- R15: [x] normalizer::test_normalize_populates_document_fields (h2),
  ::test_section_empty_when_absent (vacio). CORREN.
- R16: [x] normalizer::test_empty_body_returns_none (decision a None, CORRE);
  pipeline::test_empty_document_skipped (manejo). Ambas efectivas.
- R17: [x] cli::test_main_runs_with_injected_fetcher (urls posicional); allowlist en pipeline.
- R18: [x] pipeline::test_disallowed_and_off_allowlist_skipped (foranea no escrita ni pedida)
- R19: [x] pipeline::test_run_writes_jsonl
- R20: [x] pipeline::test_output_roundtrips_through_jsonl_loader (parser-free) Y
  ::test_run_with_real_normalizer_roundtrips (real, ahora CORRE);
  cli::test_main_end_to_end_with_real_normalizer (real, CORRE). Round-trip via
  JsonlCorpusLoader de f1 sin cambios.
- R21: [x] cli::test_cli_uses_settings_out_default
- R22: [x] cli::test_main_runs_with_injected_fetcher (rc 0 + corpus);
  __main__.py SystemExit(main()); cli::test_main_end_to_end_with_real_normalizer.
- R23: [x] pipeline::test_report_counts; cli::test_main_prints_summary
- R24: [~] REINTERPRETADO/RELAJADO para selectolax (ver design.md sec.8.1). El requisito
  literal pedia aislar el parser en requirements-scrape.txt fuera de init.sh; la desviacion
  (parser ligero a requirements.txt) esta DOCUMENTADA y JUSTIFICADA en design.md (precedente
  f9, wheel binario, docs/verification.md exige tests que pasen). torch/sentence-transformers/
  psycopg siguen diferidos (lo pesado SI se aisla). test_requirements_pinned.py verde con la
  nueva politica. Aceptable.
- R25: [x] normalizer::test_import_module_is_lazy_no_selectolax;
  cli::test_import_cli_is_network_free (subprocess: httpx/selectolax NO en sys.modules).
  Verificado tambien a mano: importar paquete + cli + normalizer con selectolax INSTALADO da
  heavy modules vacio (import sigue lazy aunque la dep ya este disponible).
- R26: [x] Document de wowrag.models; IngestReport local; git diff src = solo ingest/wowhead/
  (Slice A intacto). f1-f10 sin cambios.
- R27: [x] f11 NO reimplementa f2-f8; alimenta JsonlCorpusLoader/IndexingPipeline (R20).
- R28: [x] f11 NO anade endpoint HTTP ni reordenado.
- R29: [x] CUMPLIDO. Toda la suite por defecto de f11 (orquestacion + normalizador real)
  corre dentro de init.sh sin red, con FakeFetcher/fixtures/reloj fake/tmp_path. CERO skips
  por falta de parser.
- R30: [x] pipeline::test_live_fetch_respects_robots marcado integration (deselected).
- R31: [x] normalizer::test_missing_parser_raises_scrapeerror (bloquea selectolax.parser a
  ScrapeError, no ImportError). CORRE.

Resumen: R1-R31 TODOS con al menos un test EFECTIVO (que pasa, no skipped). El unico test no
ejecutado por defecto es el integration de R30, por diseno. R24 relajado con desviacion
documentada y aprobada.

---

## Tasks completas

- T1-T6 (Slice A): [x]
- T-A-tests: [x]
- T7 WowheadNormalizer: [x]
- T8 fixtures HTML: [x]
- T9 WowheadIngestor + IngestReport: [x]
- T10 CLI + __main__: [x]
- T11 exports __init__: [x]
- T-B-tests: [x] (los 7 parser-backed ahora corren sin skip)
- Z1 Verificacion final: [x] en tasks.md:179 (ahora marcado). init.sh muestra los 7
  parser-backed PASANDO; R12/R14/R15/R16/R29 con cobertura efectiva. Z1 SATISFECHO.

---

## Checkpoints

- C1: [x] arnes completo; ./init.sh exit 0 (297 passed en venv fresco).
- C2: [x] una sola feature in_progress (f11-wowhead-ingestion, confirmado en
  feature-list.json); features done con tests verdes; progress/current.md describe la sesion.
- C3: [x] arquitectura respetada - subpaquete ingest/wowhead/, interfaz en base.py, parser
  detras de WowheadNormalizer (lazy), httpx detras de HttpxFetcher (lazy); requirements.txt
  pineado y solo lo necesario (selectolax necesario para verificar f11); sin print de debug
  (solo el resumen intencional de la CLI), sin secretos.
- C4: [x] verificacion real - pytest excluyendo integration en verde, y AHORA la logica
  central del normalizador (R12/R14/R15/R16) SI se ejercita por defecto (los 7 tests corren).
  Fakes para lo sin red; integration para lo vivo (R30).
- C5: [n/a] grounding no aplica a la ingesta.
- C6: [x] SDD - specs completos, EARS OK; tasks todas [x]; cada R<n> con test EFECTIVO (R24
  con desviacion documentada en design.md sec.8.1).

---

## Verificacion normalizer / pipeline / CLI

Con selectolax instalado por init.sh, las 20 pruebas por defecto de Slice B PASAN.

- Normalizer (normalizer.py): import lazy de selectolax en __init__ (l.73-74) a ScrapeError
  si falta (l.76-79, R31, no ImportError). normalize (l.82-102): title (h1 fallback title,
  l.110-120, R14), section (h2 o vacio, l.122-131, R15), strip boilerplate
  _BOILERPLATE_SELECTORS (l.33-51, R12), texto del contenedor wowhead con fallback body
  (l.133-148, R12), source_url (R13), None si no hay texto (l.94-96, R16). Document de
  wowrag.models (R26). title/section se extraen ANTES de _strip_boilerplate. OK.
- Pipeline (pipeline.py): orden ESTRICTO allowlist a robots a limiter.acquire a fetcher.get
  a normalize a JSONL en out_dir/wowhead.jsonl (R18/R5/R6/R8/R9/R19). Robots-antes-de-fetch
  confirmado; URL prohibida/foranea NUNCA llega a get. IngestReport local.
- CLI (cli.py): main(argv, fetcher=None) inyectable (R29); composicion lazy en
  _build_fetcher/_build_ingestor; Settings lazy; --out default Settings.scrape_corpus_path
  (R21); resumen por stdout (R23); retorna 0 (R22). __main__.py raise SystemExit(main())
  (R22). Importar cli/paquete NO arrastra httpx/selectolax incluso con la dep instalada -
  verificado por subprocess y a mano.

## Round-trip JsonlCorpusLoader (R20)

test_output_roundtrips_through_jsonl_loader (parser-free) y test_run_with_real_normalizer
_roundtrips (parser real, ahora CORRE) y cli::test_main_end_to_end_with_real_normalizer: el
JSONL que escribe la pipeline se carga de vuelta con el JsonlCorpusLoader de f1 (sin cambios)
y devuelve Documents equivalentes (text/source_url/title/section). Cobertura EFECTIVA tanto
parser-free como con el normalizador real.

## Scope / no-regresion

- git diff src/ vs HEAD: solo ingest/wowhead/__init__.py (modificado, re-exports) y modulos
  nuevos (normalizer.py, pipeline.py, cli.py, __main__.py). Los archivos de Slice A
  (fetcher.py, robots.py, throttle.py, base.py) NO tienen diff: intactos. f1-f10 sin cambios.
- requirements-scrape.txt eliminado; requirements.txt gana selectolax==0.4.10 (pineado).
- 1 warning = StarletteDeprecationWarning preexistente de f9. Sin warnings nuevos.

## Referencia residual a requirements-scrape.txt (evaluacion solicitada)

Tras borrar requirements-scrape.txt, quedan referencias a ese nombre de fichero:

1. src/wowrag/ingest/wowhead/fetcher.py:40 (Slice A) - el mensaje del FetchError que se eleva
   si httpx esta ausente al instanciar HttpxFetcher apunta a pip install -r
   requirements-scrape.txt. Ese fichero YA NO existe. Y test_wowhead_fetcher.py:121 afirma
   match contra requirements-scrape.txt, fijando el mensaje obsoleto.

   Evaluacion: defecto MENOR, NO bloqueante para esta puerta:
   - La ruta es practicamente inalcanzable: httpx esta en requirements.txt desde f9, asi que
     init.sh siempre lo instala; el except ImportError es defensivo.
   - Es codigo de Slice A, FUERA del alcance de Slice B (la frontera no-tocar-Slice-A es
     correcta; el implementer la documento en impl_f11-slice-b.md).
   - No afecta a init.sh, ni a la cobertura de ningun R<n>, ni a ningun test (todos verdes).
   - PERO si la ruta se ejecutara, el operador recibiria un hint que apunta a un fichero
     inexistente, enganoso. normalizer.py ya se actualizo al hint correcto (requirements.txt),
     por lo que el repo queda inconsistente entre fetcher y normalizer.

   Recomendacion (follow-up, no bloquea f11): tarea menor posterior que actualice fetcher.py:40
   y test_wowhead_fetcher.py:121 a pip install -r requirements.txt (httpx vive ahi desde f9),
   igual que se hizo en normalizer.py. No re-abre f11.

2. Referencias en specs (requirements.md, tasks.md T6, design.md ASCII tree/snippet), docs y
   otros progress: artefactos historicos del plan original. design.md sec.8.1 documenta la
   desviacion correctamente, asi que el conjunto es coherente como registro. Aceptable; no
   engana a un operador (no son instrucciones de instalacion).

Conclusion: la unica referencia con potencial de enganar a un operador es fetcher.py:40 (y su
test). Es de Slice A, defensiva e inalcanzable en el camino por defecto: se acepta para esta
puerta y se deja como follow-up menor, NO como CHANGES_REQUESTED.

## Desviacion en design.md (verificacion solicitada)

design.md sec.8.1 (l.311-328) contiene la nota de desviacion del change-round 1: PRESENTE y
PRECISA. Explica que selectolax se movio a requirements.txt (eliminando requirements-scrape.txt)
porque el aislamiento dejaba la logica central sin cobertura efectiva en CI; cita (1) parser
ligero de wheel binario vs torch/psycopg, (2) precedente f9 httpx/fastapi, (3)
docs/verification.md (test que pase, no skipped); confirma que el import sigue lazy (R25) y
ScrapeError ante ausencia (R31), y que R24 queda relajado para selectolax. Coincide con el
codigo y los tests reales.

---

## Cambios requeridos

Ninguno bloqueante. El hueco de cobertura que motivo el CHANGES_REQUESTED previo esta RESUELTO.
f11-wowhead-ingestion queda APROBADA para cierre.

### Follow-up menor (no bloquea f11, agendar aparte)
1. Actualizar el hint obsoleto en src/wowrag/ingest/wowhead/fetcher.py:40 y el match en
   tests/test_wowhead_fetcher.py:121: de requirements-scrape.txt a requirements.txt (httpx vive
   en requirements.txt desde f9, y requirements-scrape.txt ya no existe). Codigo de Slice A;
   tarea cosmetica de consistencia, no re-abre f11.
