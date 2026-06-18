# Review - feature f11-wowhead-ingestion - Slice A (fetch + robots + rate-limit)

**Veredicto:** APPROVED

> Alcance: Slice A de 2 (entrega encadenada). La feature sigue in_progress
> hasta que aterrice Slice B. Aqui solo se aprueba el transporte cortes
> (T1-T6 + T-A-tests): base.py, fetcher.py, robots.py, throttle.py, __init__.py
> parcial, campos scrape_* en config.py y requirements-scrape.txt. Slice B
> (normalizador + pipeline + CLI) NO se revisa aqui y permanece [ ].

## Trazabilidad requirements / tests (Slice A)

Todos los tests listados corren en la suite por defecto (not integration).

| R | Estado | Test que lo verifica |
|---|--------|----------------------|
| R1 | [x] | test_wowhead_fetcher.py::test_fake_fetcher_satisfies_protocol, ::test_fake_fetcher_returns_mapped_result |
| R2 | [x] | test_wowhead_fetcher.py::test_httpx_fetcher_sets_user_agent (instancia HttpxFetcher como Fetcher concreto via httpx fake) |
| R3 | [x] | test_wowhead_fetcher.py::test_httpx_fetcher_missing_dep_raises_fetcherror (match requirements-scrape.txt), ::test_httpx_fetcher_get_transport_error_raises_fetcherror |
| R4 | [x] | test_wowhead_fetcher.py::test_fake_fetcher_returns_mapped_result, ::test_fake_fetcher_accepts_status_text_tuple, ::test_fake_fetcher_records_requested_urls, ::test_fake_fetcher_unmapped_url_raises_without_default, ::test_fake_fetcher_default_status_for_unmapped |
| R5 | [x] | test_wowhead_robots.py::test_allows_when_robots_permits, ::test_missing_robots_is_permissive, ::test_robots_fetch_error_is_permissive |
| R6 | [x] | test_wowhead_robots.py::test_denies_when_robots_disallows, ::test_disallowed_url_never_fetched (via requested_urls, no solo el bool) |
| R7 | [x] | test_wowhead_robots.py::test_robots_cached_per_host |
| R8 | [x] | test_wowhead_throttle.py::test_first_acquire_no_wait; default scrape_min_interval_s en test_config.py |
| R9 | [x] | test_wowhead_throttle.py::test_second_acquire_within_interval_sleeps (math 0.7s), ::test_second_acquire_after_interval_no_wait |
| R10 | [x] | test_wowhead_fetcher.py::test_httpx_fetcher_sets_user_agent; default + env-override scrape_user_agent en test_config.py |
| R11 | [x] | test_wowhead_throttle.py::test_acquire_uses_injected_clock |
| R24 | [x] | requirements-scrape.txt con selectolax==0.4.10 pineado, fuera de requirements.txt; test_requirements_pinned.py verde |
| R25 (httpx) | [x] | test_wowhead_fetcher.py::test_import_module_is_lazy_no_httpx; verificado fuera de pytest: import paquete+submodulos -> httpx/selectolax NO en sys.modules |
| R26 | [x] | git diff --stat HEAD -- src/ = solo config.py (+15, aditivo); esquema Document y f1-f10 intactos |
| R27 | [x] | No se reimplementa f2-f8 |
| R28 | [x] | No se anade endpoint HTTP ni reordenado |
| R29 (parcial) | [x] | Logica Slice A testeada con FakeFetcher + reloj/sleep fake, sin red, dentro de ./init.sh |
| R30 (parcial) | [x] | Slice A no introduce tests de red; mark integration registrado en pyproject.toml |

> R12-R23, R31 y los lados parser/final de R25/R29/R30 son de Slice B (no entran).
> R17/R21 PARCIALES: solo campos de Settings (scrape_allowed_host,
> scrape_corpus_path) con default + env-override en
> test_config.py::test_scrape_settings_overridable_from_env; su uso real es Slice B.

Sin huecos de cobertura en el alcance de Slice A.

## Tasks (Slice A [x], Slice B [ ])

- T1 Fetcher Protocol + errores + FetchResult: [x]
- T2 HttpxFetcher (lazy httpx) + FakeFetcher: [x]
- T3 RobotsGate (stdlib urllib.robotparser, cache por host): [x]
- T4 RateLimiter (reloj/sleep inyectables): [x]
- T5 campos scrape_* en Settings: [x]
- T6 requirements-scrape.txt + __init__.py parcial: [x]
- T-A-tests tests del transporte cortes: [x]
- T7-T11, T-B-tests, Z1 (Slice B + cierre): [ ] - correctamente pendientes

Verificado en specs/f11-wowhead-ingestion/tasks.md: Slice A todo [x], Slice B todo [ ].

## Checkpoints

- C1: [x] arnes completo; ./init.sh exit 0.
- C2: [x] una sola feature in_progress (f11).
- C3: [x] arquitectura respetada - subpaquete ingest/wowhead/ con interfaz en base.py (Protocol), httpx detras de HttpxFetcher; requirements.txt pineado; sin print de debug ni secretos.
- C4: [x] un fichero de test por modulo; logica con fakes, sin red; pytest -m "not integration" > 0 tests y verde.
- C5: [n/a] grounding no aplica al transporte de Slice A.
- C6: [x] specs/f11-wowhead-ingestion/{requirements,design,tasks}.md; EARS estricto; cada R<n> de Slice A con >=1 test.

## Verificacion de cumplimiento (slice etico-critico)

### Robots ANTES del fetch (R5/R6/R7)
- RobotsGate.allowed(url) (robots.py:48-61) obtiene robots.txt del host via el MISMO Fetcher (_load, l.63-88), parsea con RobotFileParser.parse(...) y responde can_fetch(self._ua, url). Cache por host (l.60) -> R7.
- Prueba de que la URL prohibida NUNCA se solicita (no solo el bool): test_disallowed_url_never_fetched afirma fetcher.requested_urls == [ROBOTS_URL] y denied not in fetcher.requested_urls. OK
- Robots inaccesible: permisiva + log (rp.allow_all = True), como design.md seccion 11. test_missing_robots_is_permissive (404) y test_robots_fetch_error_is_permissive (transporte) lo fijan. OK
- Nota (no bloqueante): el cableado robots-antes-de-CADA-fetch en el flujo end-to-end depende del WowheadIngestor (pipeline.py), que es Slice B. En Slice A el RobotsGate es correcto y probado en aislamiento. Conforme a design.md seccion 1.

### Rate-limit con reloj/sleep inyectables (R8/R9/R11)
- RateLimiter (throttle.py:32-55): clock y sleep inyectables (defaults time.monotonic/time.sleep). acquire() calcula wait = self._min - (now - self._last) y solo duerme si wait > 0. OK
- Math verificado: test_second_acquire_within_interval_sleeps con min=1.0, elapsed 0.3 -> sleep.calls[0] ~= 0.7 (abs(... - 0.7) < 1e-9), una sola llamada a sleep. OK
- Sin time.sleep real: _SpySleep registra duraciones sin dormir; _FakeClock sirve timestamps de una lista. Suite de throttle <0.2s. OK

### User-Agent identificable desde Settings (R10)
- Settings.scrape_user_agent (config.py:59-62) = wow-classic-rag-bot/0.1 (+https://github.com/...) - descriptivo y con URL de contacto. HttpxFetcher.__init__ envia {User-Agent: ua} en cada GET; test_httpx_fetcher_sets_user_agent captura el header. OK

### Diseno del Fetcher (R1/R2/R3/R4/R25)
- Fetcher Protocol GET-only (get(url) -> FetchResult); robots/rate-limit son colaboradores aparte (base.py:45-61). HttpxFetcher importa httpx DENTRO de __init__, ausencia -> FetchError (no ImportError). FakeFetcher registra requested_urls; importar el modulo NO importa httpx. OK

## Analisis del 1 warning

- Texto: StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead. - en .venv/Lib/site-packages/fastapi/testclient.py:1.
- Origen: lo dispara tests/test_api.py (f9) al importar fastapi.testclient.TestClient, que internamente importa starlette.testclient. Reproducido aislando f9: pytest tests/test_api.py -> 21 passed, 1 warning. Las pruebas de f11 Slice A (fetcher/robots/throttle + config) por si solas producen 0 warnings.
- Veredicto: ACEPTABLE - NO es un defecto de f11. Es una deprecacion de terceros (starlette/fastapi sobre el cliente httpx de su TestClient), preexistente del stack de f9, ajena a este slice. NO es ninguno de los defectos a vigilar: no hay cliente/socket httpx sin cerrar en f11, no es un pytest mark sin registrar (integration registrado en pyproject.toml:6), ni una deprecacion de pydantic/Settings. Atribucion del implementer (impl_f11-slice-a.md l.88-90) correcta. No requiere accion en este slice.

## Scope

- Sin codigo de Slice B: no existen normalizer.py, pipeline.py, cli.py, __main__.py, ni fixtures HTML (tests/fixtures/wowhead/ vacio), ni test_wowhead_normalizer/pipeline/cli.py. OK
- selectolax NO en requirements.txt - solo en requirements-scrape.txt (pineado, fuera de init.sh) y verificado ausente del entorno (lazy-isolation real). OK
- httpx NO re-anadido a requirements.txt por f11 (ya estaba desde f9). OK
- f1-f10 sin tocar (solo imports): git diff --stat HEAD -- src/ = unicamente config.py (+15, aditivo, solo campos scrape_* nuevos opcionales con default sano). Los models.py/generation/retrieval del snapshot ya estan commiteados (diff vs HEAD vacio) y son de f5/f6/f7. OK

## Ejecucion

- ./init.sh -> exit 0, 277 passed, 2 skipped, 5 deselected, 1 warning (3.24s).
- Tests de Slice A directos -> 20 passed in 0.14s (sin red, sin sleep real).
- test_config.py (incl. scrape) -> verde.

## Cambios requeridos

Ninguno. Slice A aprobado.
