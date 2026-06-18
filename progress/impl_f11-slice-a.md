# Implementación — f11-wowhead-ingestion · Slice A (fetch + robots + rate-limit)

> Slice A de 2 (entrega encadenada). Feature en `in_progress` con spec aprobado.
> Implementado SOLO el transporte cortés (T1–T6 + T-A-tests). Slice B
> (normalizador + pipeline + CLI) **NO** tocado. Pendiente del reviewer; NO se
> marca `done` ni se edita `feature-list.json`.

## Tasks Slice A completadas (todas `[x]` en `tasks.md`)

- **T1** — `Fetcher` Protocol + jerarquía de errores (`IngestError` →
  `FetchError`, `ScrapeError`) + `FetchResult(url, status_code, text)` en
  `src/wowrag/ingest/wowhead/base.py`.
- **T2** — `HttpxFetcher` (import lazy de `httpx` dentro de `__init__`, patrón
  `OllamaLLM`; falta → `FetchError`, no `ImportError`; envía header `User-Agent`)
  + `FakeFetcher` (red-free, mapa URL→`FetchResult`/`(status,text)`, registra
  `requested_urls`) en `src/wowrag/ingest/wowhead/fetcher.py`.
- **T3** — `RobotsGate` (stdlib `urllib.robotparser`, sin dep nueva; obtiene
  robots.txt vía el mismo `Fetcher`, cache por host, política permisiva + log si
  robots inaccesible) en `src/wowrag/ingest/wowhead/robots.py`.
- **T4** — `RateLimiter` (reloj/`sleep` inyectables, sin estado global; primera
  `acquire` sin espera, segunda < intervalo → `sleep(diferencia)`) en
  `src/wowrag/ingest/wowhead/throttle.py`.
- **T5** — Campos de scraper en `Settings`: `scrape_user_agent`,
  `scrape_min_interval_s=1.0`, `scrape_allowed_host="www.wowhead.com"`,
  `scrape_max_pages=100`, `scrape_corpus_path="data/corpus"` (todos nuevos,
  opcionales, default sano; ninguna clave existente alterada) en
  `src/wowrag/config.py`.
- **T6** — `requirements-scrape.txt` (`selectolax==0.4.10`, cabecera "NOT loaded
  by init.sh") + `__init__.py` re-exportando SOLO el conjunto público de Slice A
  sin arrastrar httpx/parser de forma eager.
- **T-A-tests** — `tests/test_wowhead_fetcher.py`,
  `tests/test_wowhead_robots.py`, `tests/test_wowhead_throttle.py` (21 tests
  nuevos) + extensión de `tests/test_config.py` (defaults + env-override de los
  campos scrape).

## Archivos creados

- `src/wowrag/ingest/wowhead/__init__.py` (35)
- `src/wowrag/ingest/wowhead/base.py` (61)
- `src/wowrag/ingest/wowhead/fetcher.py` (121)
- `src/wowrag/ingest/wowhead/robots.py` (88)
- `src/wowrag/ingest/wowhead/throttle.py` (55)
- `requirements-scrape.txt` (13)
- `tests/test_wowhead_fetcher.py` (180)
- `tests/test_wowhead_robots.py` (96)
- `tests/test_wowhead_throttle.py` (99)

## Archivos editados

- `src/wowrag/config.py` (+15): 5 campos `scrape_*` nuevos.
- `tests/test_config.py` (+30): defaults en `EXPECTED_DEFAULTS` +
  `test_scrape_settings_overridable_from_env`.
- `specs/f11-wowhead-ingestion/tasks.md`: T1–T6 + T-A-tests marcadas `[x]`.

## Trazabilidad R<n> → test (Slice A)

| R   | Cubierto por |
|-----|--------------|
| R1  | `test_fetcher.py::test_fake_fetcher_satisfies_protocol`, `::test_fake_fetcher_returns_mapped_result` |
| R2  | `test_fetcher.py::test_httpx_fetcher_sets_user_agent` (instancia `HttpxFetcher` como `Fetcher` concreto vía httpx fake) |
| R3  | `test_fetcher.py::test_httpx_fetcher_missing_dep_raises_fetcherror`, `::test_httpx_fetcher_get_transport_error_raises_fetcherror` |
| R4  | `test_fetcher.py::test_fake_fetcher_returns_mapped_result`, `::test_fake_fetcher_accepts_status_text_tuple`, `::test_fake_fetcher_records_requested_urls`, `::test_fake_fetcher_unmapped_url_raises_without_default`, `::test_fake_fetcher_default_status_for_unmapped` |
| R5  | `test_robots.py::test_allows_when_robots_permits`, `::test_missing_robots_is_permissive`, `::test_robots_fetch_error_is_permissive` |
| R6  | `test_robots.py::test_denies_when_robots_disallows`, `::test_disallowed_url_never_fetched` (prueba vía `requested_urls`) |
| R7  | `test_robots.py::test_robots_cached_per_host` |
| R8  | `test_throttle.py::test_first_acquire_no_wait`; default `scrape_min_interval_s` en `test_config.py` |
| R9  | `test_throttle.py::test_second_acquire_within_interval_sleeps`, `::test_second_acquire_after_interval_no_wait` |
| R10 | `test_fetcher.py::test_httpx_fetcher_sets_user_agent`; default `scrape_user_agent` + env-override en `test_config.py` |
| R11 | `test_throttle.py::test_acquire_uses_injected_clock` (+ reloj/sleep fake en todos los tests de throttle) |
| R17 | default `scrape_allowed_host` + env-override en `test_config.py` (parcial; uso de allowlist en pipeline → Slice B) |
| R21 | default `scrape_corpus_path` + env-override en `test_config.py` (parcial; uso en CLI/pipeline → Slice B) |
| R24 | `requirements-scrape.txt` con `selectolax` pineado, fuera de `requirements.txt`/`init.sh`; `test_requirements_pinned.py` sigue verde (parser NO en requirements.txt) |
| R25 (lado httpx) | `test_fetcher.py::test_import_module_is_lazy_no_httpx`; verificado además que importar `wowrag.ingest.wowhead` y submódulos no carga `httpx` ni `selectolax` (`sys.modules` check) |
| R26–R28 | No se modifica el esquema `Document` ni f1–f10; no se reimplementa f2–f8; no se añade HTTP (f9) ni reordenado (f12). Slice A solo añade el subpaquete `ingest/wowhead/` y campos opcionales en `config.py`. Toda la suite previa (256) sigue verde. |
| R29 (parcial) | Toda la lógica de Slice A se testea con `FakeFetcher`, reloj/sleep fake; sin red; corre en `./init.sh` (`not integration`). |
| R30 (parcial) | No se añadieron tests `@integration` en Slice A; el `test_live_fetch_respects_robots` es de Slice B. Slice A no introduce ningún test que toque red. |

> R12–R16, R19, R20, R22, R23, R31, y los lados "parser"/"final" de R25/R29/R30
> son de **Slice B** y NO se implementan en este run.

## Verificación

- Baseline previo: `256 passed, 2 skipped, 5 deselected` (exit 0).
- Tras Slice A: **`277 passed, 2 skipped, 5 deselected, 1 warning`** (exit 0)
  vía `./init.sh`. +21 tests nuevos de transporte cortés en la suite por
  defecto, todos verdes.
- Import-isolation verificada fuera de pytest: `import wowrag.ingest.wowhead`
  (+ `fetcher`/`robots`/`throttle`) → `httpx` y `selectolax` NO en `sys.modules`
  (R25). El warning de `init.sh` es el `StarletteDeprecationWarning` preexistente
  de f9, ajeno a f11.

## Slice B NO tocado (confirmación)

No se crearon `normalizer.py`, `pipeline.py`, `cli.py`, `__main__.py`, ni
fixtures HTML, ni `test_wowhead_normalizer/pipeline/cli.py`. No se usa
`selectolax` en código (solo se declara en `requirements-scrape.txt`, instalado
manualmente por Slice B). El corpus JSONL de salida queda para Slice B.

## Conteo aproximado de líneas cambiadas

~793 líneas (≈388 código no-test: src + config + requirements; ≈375 tests + 45
de edits de tests/config; tasks.md marcas mínimas). La porción no-test (~388)
queda dentro del presupuesto ~400 de Slice A.

## Desviaciones del spec

Ninguna desviación de diseño. Notas menores, todas dentro del spec:

1. `FakeFetcher` admite además un `default_status` opcional (p. ej. 404) para
   simular robots.txt ausente sin tener que mapear cada URL; el spec lo permite
   ("o `(status, text)` … o eleva `FetchError`/404 según configuración", §4).
2. `RobotsGate._load` distingue robots inaccesible (transporte/`FetchError`) de
   robots ausente (status ≥ 400 o cuerpo vacío); ambos → política permisiva +
   log, exactamente como documenta `design.md` §11 (alternativa conservadora
   descartada por defecto).
3. `scrape_corpus_path` se añade ya en Slice A porque T5 (task de Slice A) lo
   lista explícitamente; su consumo real (CLI/pipeline) es de Slice B. Es un
   campo opcional inerte hasta entonces.
