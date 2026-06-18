# Tasks — f11-wowhead-ingestion

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests del camino por defecto son unitarios con stdlib + fakes +
> fixtures HTML: un `FakeFetcher` (implementa el Protocol `Fetcher`), ficheros HTML
> de fixture y un reloj/`sleep` inyectables. Sin red, sin servicios reales. La
> trazabilidad `R<n>` ↔ test es obligatoria (`docs/verification.md`); nombra o
> comenta cada test con su `R<n>`.
>
> **Entrega: 2 slices encadenados** (ver `design.md` §1). Estimación total
> > 900 líneas, por encima del presupuesto de 400 → NO cabe en un PR único.
> - **Slice A** (transporte cortés: fetch + robots + rate-limit): T1–T6 + tests
>   T-A-tests. Cubre R1–R11, R24, R25 (lado httpx), R26–R28, R29, R30 (parcial).
> - **Slice B** (normalizador + pipeline + CLI): T7–T11 + tests T-B-tests. Cubre
>   R12–R23, R25 (lado parser), R31, R29/R30 (final). Depende de Slice A.
>
> Aplica la estrategia de entrega que indique el leader. f11 PRODUCE un corpus
> JSONL que CONSUMEN el `JsonlCorpusLoader` (f1) y el `IndexingPipeline` (f4) **sin
> cambios**; NO reimplementa f2–f8 ni modifica el esquema `Document` ni f1–f10. NO
> introduce HTTP (eso es f9) NI reordenado (f12). robots.txt, rate-limit y un
> User-Agent identificable son REQUISITOS, no extras.

---

## Slice A — fetch + robots + rate-limit (transporte cortés)

### Implementación

- [x] **T1 — Interfaz `Fetcher` + errores en `ingest/wowhead/base.py`.**
  Crear el subpaquete `src/wowrag/ingest/wowhead/` (con `__init__.py`) y
  `base.py` (ver `design.md` §3): jerarquía de errores `IngestError(Exception)` →
  `FetchError`, `ScrapeError`; `@dataclass(frozen=True) FetchResult(url, status_code,
  text)`; `Fetcher(Protocol)` con `get(self, url: str) -> FetchResult`. `from
  __future__ import annotations`, type hints.
  _(Cubre R1)_

- [x] **T2 — `HttpxFetcher` (lazy httpx) + `FakeFetcher` en `ingest/wowhead/fetcher.py`.**
  Crear `fetcher.py` (ver §4) con patrón EXACTO de `OllamaLLM`: `HttpxFetcher`
  importa `httpx` DENTRO de `__init__`; si falta → `FetchError` (no `ImportError`,
  R3); envía el header `User-Agent` recibido (R10); `get(url)` devuelve un
  `FetchResult`, elevando `FetchError` ante fallo de red. `FakeFetcher` (red-free,
  R4): mapa URL → `FetchResult`/`(status,text)` predefinido; registra las URLs
  solicitadas (para verificar que las prohibidas NUNCA se piden). NO importar httpx
  al tope del módulo (R25).
  _(Cubre R2, R3, R4, R10, R25 parcial)_

- [x] **T3 — `RobotsGate` en `ingest/wowhead/robots.py`.**
  Crear `robots.py` (ver §5) con `RobotsGate(user_agent, fetcher)` que use
  `urllib.robotparser.RobotFileParser` de la stdlib (sin dep nueva): `allowed(url)
  -> bool` obtiene `robots.txt` del host vía el MISMO `Fetcher`, lo parsea y
  responde `can_fetch(ua, url)` (R5); cachea un parser por host para no re-descargar
  (R7). Documentar la política de `robots.txt` inaccesible (permisivo + log, §11).
  _(Cubre R5, R6, R7)_

- [x] **T4 — `RateLimiter` en `ingest/wowhead/throttle.py`.**
  Crear `throttle.py` (ver §6) con `RateLimiter(min_interval_s, *, clock, sleep)`:
  `clock` y `sleep` INYECTABLES con defaults `time.monotonic`/`time.sleep` (R11);
  `acquire()` no espera en la primera llamada y, si han pasado < `min_interval_s`
  desde la anterior, llama a `sleep(diferencia)` (R8, R9). Sin estado global.
  _(Cubre R8, R9, R11)_

- [x] **T5 — Campos de scraper en `Settings` (`config.py`).**
  EDITAR `src/wowrag/config.py` añadiendo SOLO campos nuevos opcionales con default
  sano (sin tocar claves existentes; ver §7): `scrape_user_agent` (UA descriptivo
  con URL de contacto, R10), `scrape_min_interval_s: float = 1.0` (R8),
  `scrape_allowed_host: str = "www.wowhead.com"` (R17, R18), `scrape_max_pages: int`,
  `scrape_corpus_path: str = "data/corpus"` (directorio de salida, R21). NO
  modificar claves existentes ni exigir entorno para el camino por defecto.
  _(Cubre R8, R10, R17, R21 parcial)_

- [x] **T6 — `requirements-scrape.txt` + `__init__.py` parcial.**
  Crear `requirements-scrape.txt` (ver §8.1) con la dep de parsing HTML pineada
  (`selectolax==<ver>`), con cabecera que indique "NOT loaded by init.sh; install
  manually" igual que `requirements-ml/pg/llm.txt` (R24). Completar
  `ingest/wowhead/__init__.py` re-exportando lo de Slice A (`Fetcher`,
  `HttpxFetcher`, `FakeFetcher`, `RobotsGate`, `RateLimiter`, `FetchResult`,
  errores) sin importar nada que arrastre httpx/parser de forma eager (R25).
  _(Cubre R24, R25 parcial)_

### Tests (Slice A)

- [x] **T-A-tests — Tests del transporte cortés.**
  Crear (ver `design.md` §12), todos `not integration`, con `FakeFetcher`, reloj/
  sleep fake y `tmp_path` donde aplique:
  - `tests/test_wowhead_fetcher.py`: `FakeFetcher` mapea (R1, R4); httpx ausente →
    `FetchError` (R3); UA enviado con cliente mockeado/`MockTransport` sin red
    (R10); importar el módulo no importa httpx (R25).
  - `tests/test_wowhead_robots.py`: permite/omite según robots servido por
    `FakeFetcher` (R5, R6); URL prohibida NO aparece en las URLs solicitadas (R6);
    robots.txt pedido una vez por host (R7).
  - `tests/test_wowhead_throttle.py`: primera `acquire` sin espera (R8); segunda
    dentro del intervalo → `sleep` espía recibe la diferencia (R9); usa reloj
    inyectado, sin tiempo de pared (R11).
  _(Cubre los tests de R1–R11, R25 parcial; trazabilidad `R<n>` ↔ test)_

---

## Slice B — normalizador + pipeline + CLI

### Implementación

- [ ] **T7 — `WowheadNormalizer` en `ingest/wowhead/normalizer.py`.**
  Crear `normalizer.py` (ver §8): importar el parser (`selectolax`) DENTRO de
  `__init__`; si falta → `ScrapeError` (no `ImportError`, R31); `normalize(html,
  source_url) -> Document | None`: eliminar boilerplate (script/style/nav/header/
  footer/aside/ads por selectores CSS, constante de módulo) (R12), extraer texto
  principal normalizado (R12), `title` (R14), `section` o `""` (R15), `source_url`
  (R13); si no queda texto → `None` (R16). IMPORTA `Document` de `wowrag.models`;
  NO toca el esquema. No importar el parser al tope del módulo (R25).
  _(Cubre R12, R13, R14, R15, R16, R25 parcial, R31, R26)_

- [ ] **T8 — Fixtures HTML en `tests/fixtures/wowhead/`.**
  Crear `spell_fireball.html` (página de wowhead realista con boilerplate: nav,
  ads, script, header/footer, más un `<title>`/`<h1>`, un `<h2>` de sección y
  cuerpo de texto) y `empty_body.html` (sin texto principal tras limpiar). Datos de
  fixture deterministas para ejercitar el normalizador sin red.
  _(Soporte de R12–R16; sin requirements propios)_

- [ ] **T9 — `WowheadIngestor` + `IngestReport` en `ingest/wowhead/pipeline.py`.**
  Crear `pipeline.py` (ver §9): `IngestReport(BaseModel)` (counts: `requested`,
  `skipped_robots`, `skipped_allowlist`, `skipped_empty`, `documents_written`,
  `out_path`) LOCAL del subpaquete (NO en `models.py`). `WowheadIngestor(fetcher,
  robots, limiter, normalizer, *, allowed_host, max_pages)` con `run(seed_urls,
  out_dir) -> IngestReport`: por URL (hasta `max_pages`) aplica el orden ESTRICTO
  allowlist (R18) → robots (R5, R6) → `limiter.acquire()` (R8, R9) →
  `fetcher.get` → `normalizer.normalize`; `None` → skip+log (R16); escribe todos
  los `Document`s como JSONL (`doc.model_dump_json()+"\n"`, UTF-8) en
  `out_dir/wowhead.jsonl`, creando `out_dir` (R19). Una URL prohibida/foránea
  NUNCA llega a `fetcher.get`. Depende solo de interfaces/colaboradores inyectados
  (R29).
  _(Cubre R5, R6, R8, R9, R16, R17, R18, R19, R23 parcial, R27, R29)_

- [ ] **T10 — CLI `ingest/wowhead/cli.py` + `__main__.py` (composición perezosa).**
  Crear `cli.py` con `main(argv=None, fetcher=None) -> int` (ver §10): `argparse`
  con `urls` (nargs="+", R17) y `--out` (default `None` → `Settings.scrape_corpus_path`,
  R21); construye `Settings()` lazy dentro de `main`; usa el `fetcher` inyectado o
  `_build_fetcher`/`_build_ingestor` (que instancian `HttpxFetcher`/
  `WowheadNormalizer` con sus imports lazy) SOLO si no se inyecta; corre
  `ingestor.run(urls, out_dir)`; imprime el resumen del `IngestReport` por stdout
  (R23); retorna 0 en éxito (R22). Crear `__main__.py` con
  `raise SystemExit(main())` para que `python -m wowrag.ingest.wowhead` funcione
  (R22). Cero imports pesados al tope del módulo (R25).
  _(Cubre R21 final, R22, R23 final, R25 final)_

- [ ] **T11 — Finalizar exports de `ingest/wowhead/__init__.py`.**
  Asegurar que `__init__.py` re-exporta el conjunto público final (lo de Slice A +
  `WowheadNormalizer`, `WowheadIngestor`, `IngestReport`) con `__all__`, SIN que
  `import wowrag.ingest.wowhead` arrastre httpx ni el parser de forma eager
  (mantener la importabilidad libre de deps pesadas, R25).
  _(Cubre R25 final)_

### Tests (Slice B)

- [ ] **T-B-tests — Tests del normalizador, la pipeline y la CLI.**
  Crear (ver §12), `not integration`, con `FakeFetcher`, fixtures HTML y `tmp_path`:
  - `tests/test_wowhead_normalizer.py`: campos `text/source_url/title/section`
    poblados desde el fixture (R12, R13, R14, R15); boilerplate (nav/ads/script)
    ausente del `text` (R12); `section == ""` sin sub-sección (R15); fixture sin
    texto → `None` (R16); parser ausente → `ScrapeError` (R31); importar el módulo
    no importa el parser (R25).
  - `tests/test_wowhead_pipeline.py`: `run` escribe `out_dir/wowhead.jsonl` (R19);
    **round-trip clave**: cargar el fichero con `JsonlCorpusLoader` (f1) devuelve
    `Document`s equivalentes (R20); URLs prohibidas/foráneas no se escriben ni se
    solicitan (R6, R18); página sin texto no genera línea (R16); `IngestReport`
    refleja los counts (R23).
  - `tests/test_wowhead_cli.py`: `main([url], fetcher=fake)` retorna 0 y escribe el
    corpus en `tmp_path` (R22); stdout con los counts (R23); sin `--out` usa
    `Settings.scrape_corpus_path` (R21); `import wowrag.ingest.wowhead.cli` no
    importa httpx ni el parser (R25).
  - **Integración** (`@pytest.mark.integration`, EXCLUIDO de `init.sh`, R30): un
    `test_live_fetch_respects_robots` que haga un fetch real contra wowhead vivo
    comprobando robots + UA.
  _(Cubre los tests de R12–R23, R25 final, R30, R31; trazabilidad `R<n>` ↔ test)_

---

## Cierre

- [ ] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R31) tienen al menos un test.
  - Importar `wowrag.ingest.wowhead` y sus submódulos NO arrastra `httpx` ni la
    librería de parsing HTML (imports perezosos, R25); el parser vive SOLO en
    `requirements-scrape.txt` y NO en `requirements.txt` (sigue pasando
    `test_requirements_pinned.py`) (R24).
  - Toda la lógica (fetcher, robots, rate-limit, normalizador, pipeline, CLI) corre
    con `FakeFetcher`, fixtures HTML y reloj/sleep fake, sin red (R29); el único
    test que toca wowhead vivo está marcado `@pytest.mark.integration` y queda
    fuera de `init.sh` (R30).
  - robots.txt se consulta ANTES de cada fetch, las URLs prohibidas/foráneas NUNCA
    se solicitan, el rate-limit espera el intervalo configurado y cada petición
    lleva el User-Agent de `Settings` (R5–R11, R17, R18).
  - El corpus `wowhead.jsonl` emitido es cargable sin cambios por el
    `JsonlCorpusLoader` de f1 y produce `Document`s equivalentes (round-trip, R20).
  - f11 NO modifica el esquema `Document` ni f1–f10, NO reimplementa f2–f8, NO
    añade HTTP (f9) ni reordenado (f12) (R26, R27, R28); `config.py` solo gana
    campos nuevos opcionales con default sano.
  - No quedan `print()` de debug (salvo el resumen intencional de la CLI por
    stdout), ni secretos, ni TODOs sin contexto.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json` (salvo lo que ya hizo el spec-author: `pending` →
> `spec_ready`). El cambio a `in_progress` requiere aprobación humana; el cierre
> (`done`) lo hacen el leader / reviewer tras validar la trazabilidad `R<n>` ↔
> test. Tu trabajo termina cuando todas las tasks `[x]` y `./init.sh` pasa en verde.
