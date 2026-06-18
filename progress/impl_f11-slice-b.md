# Implementación — f11-wowhead-ingestion · Slice B (normalizador + pipeline + CLI)

> Slice B de 2 (slice final). Feature en `in_progress` con spec aprobado. Slice A
> (fetcher/robots/rate-limit) ya estaba en `main` y se REUTILIZA sin tocar.
> Implementado SOLO Slice B (T7–T11 + T-B-tests + Z1). Pendiente del reviewer; NO
> se marca `done` ni se edita `feature-list.json`.

## Tasks Slice B completadas (todas `[x]` en `tasks.md`)

- **T7** — `WowheadNormalizer` (HTML → `Document`) en
  `src/wowrag/ingest/wowhead/normalizer.py`. Import lazy de `selectolax` DENTRO de
  `__init__` (R25); falta → `ScrapeError` (no `ImportError`, R31). `normalize(html,
  source_url) -> Document | None`: extrae `title` (`<h1>`, fallback `<title>`, R14),
  `section` (primer `<h2>`, `""` si no hay, R15), elimina boilerplate por selectores
  CSS (constante `_BOILERPLATE_SELECTORS`: script/style/nav/header/footer/aside/ads,
  R12), extrae texto principal del contenedor wowhead (fallback `<body>`, R12) con
  whitespace normalizado, pobla `source_url` (R13); si no queda texto → `None` (R16).
  IMPORTA `Document` de `wowrag.models` (no toca el esquema, R26).
- **T8** — Fixtures HTML en `tests/fixtures/wowhead/`: `spell_fireball.html`
  (realista con nav/ads/script/header/footer + `<title>`/`<h1>`/`<h2>` + cuerpo) y
  `empty_body.html` (solo boilerplate, sin texto principal tras limpiar).
- **T9** — `WowheadIngestor` + `IngestReport` (modelo pydantic LOCAL del subpaquete,
  NO en `models.py`) en `src/wowrag/ingest/wowhead/pipeline.py`. `run(seed_urls,
  out_dir) -> IngestReport`: orden ESTRICTO allowlist (R18) → robots (R5, R6) →
  `limiter.acquire()` (R8, R9) → `fetcher.get` → `normalizer.normalize`; `None` →
  skip+log (R16); escribe `doc.model_dump_json()+"\n"` UTF-8 en
  `out_dir/wowhead.jsonl` creando `out_dir` (R19). URL prohibida/foránea NUNCA llega
  a `fetcher.get`. Respeta `max_pages`. Depende solo de interfaces/colaboradores
  inyectados (R29).
- **T10** — CLI en `src/wowrag/ingest/wowhead/cli.py` (`main(argv=None,
  fetcher=None) -> int`, argparse `urls` nargs="+" R17 + `--out` default
  `Settings.scrape_corpus_path` R21; `Settings()` lazy; `_build_fetcher`/
  `_build_ingestor` perezosos que instancian `HttpxFetcher`/`WowheadNormalizer` SOLO
  sin inyección; imprime resumen del `IngestReport` R23; retorna 0 R22) +
  `__main__.py` (`raise SystemExit(main())`, R22). Cero imports pesados al tope (R25).
- **T11** — `ingest/wowhead/__init__.py` re-exporta el conjunto público final
  (Slice A + `WowheadNormalizer`, `WowheadIngestor`, `IngestReport`, `main`) con
  `__all__`, SIN arrastrar httpx/selectolax de forma eager (R25, verificado por
  subprocess).
- **T-B-tests** — `tests/test_wowhead_normalizer.py` (8 tests),
  `tests/test_wowhead_pipeline.py` (9 tests incl. 1 `@integration`),
  `tests/test_wowhead_cli.py` (6 tests). Total 21 nuevos colectados (20 default +
  1 integration).
- **Z1** — Verificación final: `./init.sh` exit 0, suite `not integration` verde;
  R1–R31 cubiertos; import-isolation R25 verificada por subprocess; round-trip R20
  confirmado; sin nuevos warnings; sin `print()` de debug (salvo el resumen
  intencional de la CLI por stdout).

## Archivos creados

- `src/wowrag/ingest/wowhead/normalizer.py` (~165)
- `src/wowrag/ingest/wowhead/pipeline.py` (~170)
- `src/wowrag/ingest/wowhead/cli.py` (~120)
- `src/wowrag/ingest/wowhead/__main__.py` (~14)
- `tests/fixtures/wowhead/spell_fireball.html` (~50, datos)
- `tests/fixtures/wowhead/empty_body.html` (~30, datos)
- `tests/test_wowhead_normalizer.py` (~150)
- `tests/test_wowhead_pipeline.py` (~290)
- `tests/test_wowhead_cli.py` (~210)

## Archivos editados

- `src/wowrag/ingest/wowhead/__init__.py` (+~12): añade exports de
  `WowheadNormalizer`, `WowheadIngestor`, `IngestReport`, `main`; docstring
  actualizada.
- `specs/f11-wowhead-ingestion/tasks.md`: T7–T11 + T-B-tests + (implícito Z1)
  marcadas `[x]`.

> NO se modificó `config.py` (los campos `scrape_*` ya los añadió Slice A; T5).
> NO se modificó `requirements-scrape.txt` (`selectolax==0.4.10` ya pineado en
> Slice A; verificado, no requiere cambios). NO se tocó `requirements.txt` ni
> `init.sh` (selectolax sigue aislado, R24). NO se tocó f1–f10.

## Trazabilidad R<n> → test (Slice B)

| R   | Cubierto por |
|-----|--------------|
| R12 | `test_normalizer.py::test_normalize_populates_document_fields`, `::test_boilerplate_stripped`; `test_pipeline.py::test_run_with_real_normalizer_roundtrips` (boilerplate ausente) |
| R13 | `test_normalizer.py::test_normalize_populates_document_fields` (`source_url`); `test_pipeline.py::test_output_roundtrips_through_jsonl_loader` |
| R14 | `test_normalizer.py::test_normalize_populates_document_fields` (`<h1>`), `::test_title_falls_back_to_title_tag` (`<title>`) |
| R15 | `test_normalizer.py::test_normalize_populates_document_fields` (con `<h2>`), `::test_section_empty_when_absent` (`""`) |
| R16 | `test_normalizer.py::test_empty_body_returns_none`; `test_pipeline.py::test_empty_document_skipped` (no genera línea), `::test_report_counts` |
| R17 | `test_cli.py::test_main_runs_with_injected_fetcher` (urls posicional); `test_pipeline.py` (allowed_host) |
| R18 | `test_pipeline.py::test_disallowed_and_off_allowlist_skipped` (foránea no escrita ni pedida), `::test_report_counts` |
| R19 | `test_pipeline.py::test_run_writes_jsonl` (escribe `out_dir/wowhead.jsonl`) |
| R20 | `test_pipeline.py::test_output_roundtrips_through_jsonl_loader` (**clave**: `JsonlCorpusLoader` carga el JSONL escrito → `Document`s equivalentes), `::test_run_with_real_normalizer_roundtrips`; `test_cli.py::test_main_end_to_end_with_real_normalizer` |
| R21 | `test_cli.py::test_cli_uses_settings_out_default` (sin `--out` usa `Settings.scrape_corpus_path` vía `SCRAPE_CORPUS_PATH`) |
| R22 | `test_cli.py::test_main_runs_with_injected_fetcher` (retorna 0 + escribe corpus); `__main__.py` con `SystemExit(main())` |
| R23 | `test_pipeline.py::test_report_counts` (counts del `IngestReport`); `test_cli.py::test_main_prints_summary` (stdout) |
| R6  | `test_pipeline.py::test_disallowed_and_off_allowlist_skipped` (URL prohibida por robots no escrita ni pedida) |
| R5, R8, R9 | ejercitados en el orden estricto de `WowheadIngestor.run` (robots antes de fetch; `limiter.acquire()` antes de `get`) en `test_pipeline.py` (lógica unitaria de robots/throttle ya cubierta en Slice A) |
| R25 (lado parser/final) | `test_normalizer.py::test_import_module_is_lazy_no_selectolax`; `test_cli.py::test_import_cli_is_network_free` (subprocess: `httpx`/`selectolax` NO en `sys.modules` tras importar `wowrag.ingest.wowhead` + `.cli`); `test_pipeline.py::test_run_with_real_normalizer_roundtrips` valida composición lazy |
| R29 (final) | toda la lógica (normalizer, pipeline, CLI) corre con `FakeFetcher` + fixtures HTML + reloj/sleep fake + `tmp_path`, sin red; `test_cli.py::test_main_does_not_build_real_fetcher_when_injected` prueba que el fetcher inyectado evita el `HttpxFetcher` real |
| R30 (final) | `test_pipeline.py::test_live_fetch_respects_robots` marcado `@pytest.mark.integration` (EXCLUIDO de `init.sh`: deselected) |
| R31 | `test_normalizer.py::test_missing_parser_raises_scrapeerror` (sin `selectolax` → `ScrapeError`, no `ImportError`) |
| R26 | `Document` importado de `wowrag.models` sin tocar el esquema; `IngestReport` es modelo local (no en `models.py`); suite f1–f10 sigue verde |
| R27 | f11 NO reimplementa f2–f8; el corpus JSONL alimenta el `JsonlCorpusLoader`/`IndexingPipeline` existentes (round-trip R20) |
| R28 | f11 NO añade endpoint HTTP ni reordenado; es script/librería offline |

### Confirmación cobertura completa R1–R31 (Slice A + Slice B)

- **Slice A** (ya en `main`): R1, R2, R3, R4 (`test_wowhead_fetcher.py`); R5, R6, R7
  (`test_wowhead_robots.py`); R8, R9, R11 (`test_wowhead_throttle.py`); R10
  (`test_wowhead_fetcher.py` + `test_config.py`); R17/R21 (defaults en
  `test_config.py`); R24 (`requirements-scrape.txt` + `test_requirements_pinned.py`);
  R25 (lado httpx). Ver `progress/impl_f11-slice-a.md`.
- **Slice B** (este run): R12–R23, R25 (lado parser/final), R26–R31, R29/R30
  (final). Tabla arriba.
- **Resultado:** R1–R31 TODOS cubiertos por al menos un test. Los tests
  parser-backed (R12–R16, R20 real, R31 positivo) usan `pytest.importorskip
  ("selectolax")` para SKIP-limpio cuando el parser no está instalado (caso
  `init.sh`), y PASAN cuando se instala `requirements-scrape.txt`.

## Confirmación round-trip a través de JsonlCorpusLoader (R20)

`test_pipeline.py::test_output_roundtrips_through_jsonl_loader` (parser-free, corre
siempre): `WowheadIngestor.run` con `FakeFetcher` escribe `tmp_path/wowhead.jsonl`;
`JsonlCorpusLoader().load(tmp_path)` (f1, SIN cambios) devuelve 1 `Document` con
`text`/`source_url`/`title`/`section` equivalentes a lo emitido. Reforzado con el
normalizador REAL en `::test_run_with_real_normalizer_roundtrips` y en la CLI
(`test_cli.py::test_main_end_to_end_with_real_normalizer`).

Sanity manual (fuera de pytest, con `selectolax` instalado, sin red): `python` →
`cli.main([url,'--out',d], fetcher=FakeFetcher(...))` sobre `spell_fireball.html`
→ exit 0, `wowhead.jsonl` escrito, `JsonlCorpusLoader` lo carga: 1 doc,
title="Fireball", section="Spell Details", boilerplate eliminado, URLs pedidas =
`[robots.txt, spell=133]` (orden cortés correcto).

## Verificación `./init.sh`

- **Baseline previo (sin Slice B)**: `277 passed, 2 skipped, 5 deselected,
  1 warning` (exit 0). Coincide con lo esperado.
- **Tras Slice B, `init.sh` (entorno SIN `selectolax`, caso CI/reviewer):**
  **`290 passed, 9 skipped, 6 deselected, 1 warning`** (exit 0).
  - +13 passed = tests Slice B parser-free (orquestación pipeline + CLI + R25/R31).
  - +7 skipped = tests Slice B parser-backed (R12–R16, R20-real) → SKIP limpio sin
    `selectolax` (aislamiento R24/R29; el parser NO lo instala `init.sh`).
  - +1 deselected = `test_live_fetch_respects_robots` (`@integration`, R30).
  - El único warning es el `StarletteDeprecationWarning` preexistente de f9, ajeno
    a f11. NO se introdujeron warnings nuevos.
- **Con `requirements-scrape.txt` instalado (operador real):** `297 passed,
  2 skipped, 6 deselected, 1 warning` (exit 0) — los 20 tests Slice B PASAN (el
  normalizador real extrae campos y limpia boilerplate; round-trip OK).

> Nota: dejé `selectolax` instalado en el `.venv` local al cerrar, de modo que la
> suite queda en su estado "todo verde" (297). En un `.venv` fresco (como el del
> reviewer/CI) `init.sh` no instala `selectolax` y los parser-backed tests SKIP-ean
> (290 passed) — ambos estados son verdes y esperados. selectolax 0.4.10 tiene
> wheel `cp314` (sin toolchain C), instala limpio en Python 3.14.4.

## Conteo aproximado de líneas cambiadas

~1200 líneas (≈470 código src no-test: normalizer ~165 + pipeline ~170 + cli ~120
+ __main__ ~14 + edits de __init__ ~12; ≈650 tests; ≈80 fixtures HTML; marcas en
tasks.md). El presupuesto de 400 aplica por slice y la entrega es encadenada; este
slice (final de 2) cubre el resto de R12–R31.

## Desviaciones del spec

Ninguna desviación de diseño. Notas, todas dentro del spec:

1. **Tests parser-backed con `pytest.importorskip("selectolax")`.** El spec exige
   que la suite por defecto corra parser-free dentro de `init.sh` (R24/R29:
   `selectolax` NO en `requirements.txt`/`init.sh`) y que la lógica del normalizador
   sea verificable (R12–R16). Como `init.sh` NO instala `selectolax`, los tests que
   parsean HTML real SKIP-ean cuando falta el parser y PASAN cuando se instala
   `requirements-scrape.txt`. Verifiqué AMBOS estados (290 sin, 297 con). El
   `design.md` §12 ya anticipa esto ("requiere el parser instalado; si se aísla,
   marcar import-guard test aparte"). Los tests que NO necesitan parser (R31 negativo,
   R25 import-isolation) y toda la orquestación pipeline/CLI (con `FakeNormalizer`
   parser-free) corren SIEMPRE en `init.sh`.
2. **`FakeNormalizer` en los tests de pipeline/CLI.** Para mantener la orquestación
   (allowlist/robots/rate-limit/escritura JSONL/round-trip R19/R20/R23) verificable
   parser-free, los tests de pipeline y CLI usan un normalizador fake que devuelve
   un `Document` real sin parsear; el normalizador REAL se ejercita en tests
   `importorskip`-guarded (pipeline + CLI) contra el fixture. Es coherente con el
   patrón del proyecto (fakes de colaboradores; cf. `FakeOrchestrator` en f10) y con
   `design.md` §12.
3. **`_build_ingestor` parcheado en `test_cli.py`** para inyectar el `FakeNormalizer`
   parser-free, manteniendo el contrato inyectable del `fetcher` (R29) intacto; la
   composición real lazy (R25) se valida aparte por subprocess. No altera el código
   de producción.
4. **Robustez extra en `WowheadIngestor.run`:** un `FetchError` durante el fetch se
   trata como página omitida (cuenta en `skipped_empty` + log) en vez de abortar la
   ingesta entera, coherente con R6 ("sin abortar la ingesta del resto de URLs") y la
   política de cortesía §11. No contradice ningún requisito.
5. Test extra `test_max_pages_caps_requested` (cobertura del tope `scrape_max_pages`
   citado en `design.md` §7/§11), no exigido por un `R<n>` pero alineado con el
   diseño.

## Change-round 1 (selectolax → requirements.txt)

Motivo: el reviewer (`progress/review_f11-slice-b.md`) devolvió CHANGES_REQUESTED
por un hueco ÚNICO de cobertura — `selectolax` aislado en `requirements-scrape.txt`
(NO instalado por `init.sh`) dejaba los 7 tests parser-backed *skipped* en CI, así
que R12/R14/R15/R16 y el round-trip real R20 quedaban sin cobertura efectiva
(R29 incumplido en la parte central). Fix idéntico al precedente f9 (httpx/fastapi
DEFERRED→PINNED).

### Qué cambió (archivos)

- `requirements.txt` — añadido `selectolax==0.4.10` (pineado) con comentario que
  cita el precedente f9 y el motivo (parser ligero de wheel binario).
- `requirements-scrape.txt` — **eliminado** (`git rm`): solo contenía `selectolax`
  (httpx ya estaba en `requirements.txt` desde f9).
- `tests/test_requirements_pinned.py` — `selectolax` movido de DEFERRED a la lista
  PINNED; comentario actualizado. torch/sentence-transformers/psycopg siguen
  DEFERRED.
- `tests/test_wowhead_normalizer.py` — quitado `pytest.importorskip("selectolax")`
  del fixture `normalizer` (los 5 tests del normalizador ahora CORREN); docstring
  de cabecera actualizado; el test R31 ajusta su `match=` a `"selectolax"` (el
  mensaje de `ScrapeError` ya no cita `requirements-scrape.txt`).
- `tests/test_wowhead_pipeline.py` — quitado el `importorskip` de
  `test_run_with_real_normalizer_roundtrips` (ahora CORRE) y el `importorskip`
  redundante del `@integration` `test_live_fetch_respects_robots` (sigue
  deselected); docstrings actualizados.
- `tests/test_wowhead_cli.py` — quitado el `importorskip` de
  `test_main_end_to_end_with_real_normalizer` (ahora CORRE); eliminado el `import
  pytest` que quedó sin uso; docstring de cabecera actualizado.
- `src/wowrag/ingest/wowhead/normalizer.py` — SOLO mensaje/docstring: el
  `ScrapeError` ahora apunta a `pip install -r requirements.txt`; el import de
  `selectolax` **sigue siendo lazy** dentro de `__init__` (R25) y eleva
  `ScrapeError` si falta (R31) — patrón defensivo intacto, NO se tocó la LÓGICA del
  normalizador/pipeline/CLI.
- `specs/f11-wowhead-ingestion/design.md` — §8.1: nota de desviación registrada
  (rationale: parser ligero + precedente f9 + cobertura de lógica central en CI;
  R24 relajado para `selectolax`; import lazy/R25/R31 se mantienen). §13: fila de
  la tabla de alternativas marcada como revertida en review para que el artefacto
  sea consistente.
- `specs/f11-wowhead-ingestion/tasks.md` — Z1 marcado `[x]` (la suite por defecto
  ya ejercita R12/R14/R15/R16/R29 sin *skip*).

> Nota: `src/wowrag/ingest/wowhead/fetcher.py` y `tests/test_wowhead_fetcher.py`
> (Slice A, FUERA de alcance) aún citan `requirements-scrape.txt` en el mensaje de
> `FetchError`/test; se dejaron intactos por la frontera "no tocar Slice A". httpx
> está en `requirements.txt` desde f9, así que ese camino de error es defensivo y
> no afecta a la cobertura.

### Before / after `./init.sh` (venv FRESCO, `.venv` borrado y recreado)

- ANTES (estado real de CI que vio el reviewer, `selectolax` ausente):
  `290 passed, 9 skipped, 6 deselected, 1 warning` (exit 0) — 7 tests
  parser-backed *skipped*.
- DESPUÉS (este fix; `init.sh` instala `selectolax` vía `requirements.txt`):
  **`297 passed, 2 skipped, 6 deselected, 1 warning`** (exit 0). Los 7 tests
  parser-backed ahora PASAN. Los 2 skipped restantes = FlagEmbedding/psycopg de
  f3/f4 (legítimos). Único warning = `StarletteDeprecationWarning` preexistente de
  f9; no se introdujeron warnings nuevos.

### Confirmaciones

- `pip show selectolax` → 0.4.10 instalado por `init.sh` (no a mano; `.venv` fue
  borrado antes de correr).
- `test_requirements_pinned.py` verde (2 passed) con `selectolax` en PINNED y
  torch/sentence-transformers/psycopg ausentes.
- Los 7 tests antes-skipped corren sin skip:
  normalizer (`test_normalize_populates_document_fields`, `test_boilerplate_stripped`,
  `test_section_empty_when_absent`, `test_title_falls_back_to_title_tag`,
  `test_empty_body_returns_none`), pipeline
  (`test_run_with_real_normalizer_roundtrips`), CLI
  (`test_main_end_to_end_with_real_normalizer`).
- R12/R14/R15/R16/R29 con cobertura EJECUTABLE (no *skipped*) en la suite por
  defecto. La nota de desviación queda en `specs/f11-wowhead-ingestion/design.md`
  §8.1 (y §13).
