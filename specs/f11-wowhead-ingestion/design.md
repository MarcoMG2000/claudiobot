# Design — f11-wowhead-ingestion

> CÓMO se construye la ingesta de wowhead. f11 es un **flujo offline de ingesta**
> que produce un corpus JSONL local; estructuralmente equivale a `index/`
> (compone varias piezas en un flujo offline) y a `eval/` (paquete propio fuera
> de las capas de paso), ver `docs/architecture.md` §6. Respeta las convenciones:
> interfaz/Protocol en `base.py` donde haya swap point, modelos pydantic ya
> existentes (`Document`), `from __future__ import annotations`, type hints,
> dependencia SOLO de interfaces, **imports pesados perezosos**, dependencias
> externas **aisladas** en su propio `requirements-*.txt`, tests con fakes +
> fixtures, lo que necesita red marcado `@pytest.mark.integration`.

## 0. Decisión de handoff: corpus JSONL local (RECOMENDADO)

f11 escribe un fichero `*.jsonl` que el `JsonlCorpusLoader` de f1 ya lee, en lugar
de pasar `Document`s en memoria al `IndexingPipeline` de f4.

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| **A. Escribir corpus JSONL** (elegida) | Reutiliza el camino existente sin tocarlo (f1 loader + f4 indexer); separa fetch (lento, con red, no-determinista) de indexado (caro, GPU/DB); el corpus es inspeccionable, cacheable y re-indexable sin re-escrapear; JSONL es el formato que f1 ya documentó como "salida natural del scraper" | Un paso intermedio en disco | **Elegida** |
| B. Emitir `Document`s en memoria al `IndexingPipeline` | Un paso menos | Acopla scraping a indexado (GPU/DB) en el mismo proceso; re-indexar exige re-escrapear; rompe la separación offline limpia | Descartada |

El formato es el mismo JSONL que f1 fijó (un `Document` por línea, campos `text`,
`source_url`, `title`, `section`). R20 exige round-trip: lo que f11 escribe, el
`JsonlCorpusLoader` lo carga sin cambios. El operador luego corre el indexado
existente sobre el directorio de salida — f11 NO lo invoca (separación de fases).

## 1. PR-size y slices encadenados

f11 introduce un paquete nuevo (fetcher + robots + rate-limit + normalizador +
pipeline + CLI) más sus tests y fixtures. Estimación:

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `ingest/wowhead/__init__.py` (re-exports) | ~20 |
| `ingest/wowhead/base.py` (`Fetcher` Protocol + `FetchError`/`ScrapeError`) | ~45 |
| `ingest/wowhead/fetcher.py` (`HttpxFetcher` lazy + `FakeFetcher`) | ~70 |
| `ingest/wowhead/robots.py` (`RobotsGate` con cache por host) | ~55 |
| `ingest/wowhead/throttle.py` (`RateLimiter` con reloj/sleep inyectables) | ~45 |
| `ingest/wowhead/normalizer.py` (HTML→`Document`, lazy parser) | ~110 |
| `ingest/wowhead/pipeline.py` (`WowheadIngestor.run` → escribe JSONL) | ~90 |
| `ingest/wowhead/cli.py` + `__main__.py` (argparse, composición perezosa) | ~85 |
| `config.py` (EDITAR: campos de scraper) | ~12 |
| `requirements-scrape.txt` | ~5 |
| `tests/fixtures/wowhead/*.html` (fixtures HTML) | ~ (datos) |
| `tests/test_wowhead_fetcher.py` | ~70 |
| `tests/test_wowhead_robots.py` | ~70 |
| `tests/test_wowhead_throttle.py` | ~55 |
| `tests/test_wowhead_normalizer.py` | ~110 |
| `tests/test_wowhead_pipeline.py` | ~110 |
| `tests/test_wowhead_cli.py` | ~70 |
| **Total estimado** | **~ >900 líneas — supera el presupuesto de 400.** |

**Recomendación: 2 slices encadenados** (work-unit commits; la numeración `R<n>`
es estable e independiente del troceo). El leader aplica la estrategia de entrega
cacheada.

- **Slice A — fetch + robots + rate-limit (transporte cortés, ~400 líneas).**
  `ingest/wowhead/base.py`, `fetcher.py`, `robots.py`, `throttle.py`,
  `ingest/wowhead/__init__.py` (parcial), campos de `config.py` + sus tests
  (`test_wowhead_fetcher.py`, `test_wowhead_robots.py`, `test_wowhead_throttle.py`)
  + `requirements-scrape.txt`. Cubre R1–R11, R24, R25 (parcial, lado httpx), R29,
  R30 (parcial), R26–R28.
- **Slice B — normalizador + pipeline + CLI (~ resto).**
  `ingest/wowhead/normalizer.py`, `pipeline.py`, `cli.py`, `__main__.py`,
  completar `__init__.py`, fixtures HTML + `test_wowhead_normalizer.py`,
  `test_wowhead_pipeline.py`, `test_wowhead_cli.py`. Cubre R12–R23, R25 (lado
  parser), R31, R29/R30 (final). Depende de Slice A.

> Si el revisor exige estrictamente ≤400 y Slice B sigue siendo grande, el
> normalizador (R12–R16, R31) puede separarse a un sub-slice B1 y
> pipeline+CLI (R17–R23) a B2.

## 2. Archivos a tocar / crear

```
src/
  wowrag/
    config.py                       # EDITAR — campos de scraper (§7)
    ingest/
      wowhead/
        __init__.py                 # NUEVO — re-exporta Fetcher, HttpxFetcher, FakeFetcher,
                                    #         RobotsGate, RateLimiter, WowheadNormalizer,
                                    #         WowheadIngestor, errores
        base.py                     # NUEVO — Fetcher (Protocol) + FetchError/ScrapeError
        fetcher.py                  # NUEVO — HttpxFetcher (lazy httpx) + FakeFetcher
        robots.py                   # NUEVO — RobotsGate (urllib.robotparser, cache por host)
        throttle.py                 # NUEVO — RateLimiter (reloj/sleep inyectables)
        normalizer.py               # NUEVO — WowheadNormalizer (HTML -> Document, lazy parser)
        pipeline.py                 # NUEVO — WowheadIngestor (run -> escribe JSONL)
        cli.py                      # NUEVO — main(argv, fetcher=None) -> int
        __main__.py                 # NUEVO — `python -m wowrag.ingest.wowhead` -> cli.main()
requirements-scrape.txt             # NUEVO — dep de parsing HTML, pineada, fuera de init.sh
tests/
  fixtures/wowhead/
    spell_fireball.html             # NUEVO — fixture HTML representativo (con boilerplate)
    empty_body.html                 # NUEVO — fixture sin texto principal (R16)
  test_wowhead_fetcher.py           # NUEVO — Fetcher/HttpxFetcher(lazy)/FakeFetcher (R1-R4, R25)
  test_wowhead_robots.py            # NUEVO — RobotsGate allow/deny/cache (R5-R7)
  test_wowhead_throttle.py          # NUEVO — RateLimiter throttle con reloj fake (R8, R9, R11)
  test_wowhead_normalizer.py        # NUEVO — HTML->Document, boilerplate, secciones (R12-R16, R31)
  test_wowhead_pipeline.py          # NUEVO — run end-to-end con FakeFetcher -> JSONL round-trip (R17-R21, R23)
  test_wowhead_cli.py               # NUEVO — entrypoint inyectable, import-isolation (R22, R23, R25)
```

> Subpaquete `ingest/wowhead/` (no un módulo plano) para agrupar el flujo y aislar
> sus dependencias. Vive bajo `ingest/` porque es ingesta de corpus (su salida es
> el input del `JsonlCorpusLoader`, también en `ingest/`). `models.py` NO se toca:
> se IMPORTA `Document` de `wowrag.models`.

## 3. Interfaz `Fetcher` (R1) + errores

`src/wowrag/ingest/wowhead/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class IngestError(Exception):
    """Base error for the wowhead ingest flow."""


class FetchError(IngestError):
    """Raised when an HTTP GET fails or the scrape dependency is missing."""


class ScrapeError(IngestError):
    """Raised when the HTML-parsing dependency is missing or HTML is unparsable."""


@dataclass(frozen=True)
class FetchResult:
    """Body text + status code of an HTTP GET."""

    url: str
    status_code: int
    text: str


class Fetcher(Protocol):
    """Swap point: HTTP GET a URL -> FetchResult. No robots/rate-limit here;
    those wrap the Fetcher in the pipeline (single responsibility)."""

    def get(self, url: str) -> FetchResult:
        ...
```

- `Fetcher` solo hace el GET. Robots y rate-limit son **colaboradores que
  envuelven** al `Fetcher` en la pipeline, no responsabilidades del `Fetcher`
  (separación de responsabilidades; el revisor rechaza HTTP+robots+throttle en una
  sola clase).
- `FetchError`/`ScrapeError` derivan de `IngestError` para captura por familia,
  igual que la jerarquía `CorpusError` de f1.

## 4. `HttpxFetcher` (R2, R3, R10) + `FakeFetcher` (R4)

`src/wowrag/ingest/wowhead/fetcher.py`. Patrón EXACTO de `OllamaLLM` (f7): `httpx`
se importa **dentro de `__init__`**; si falta, se eleva `FetchError` (no
`ImportError`).

```python
class HttpxFetcher:
    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        try:
            import httpx  # lazy import (R25)
        except ImportError as exc:
            raise FetchError(
                "HTTP client not installed. Install scrape deps: "
                "pip install -r requirements-scrape.txt"
            ) from exc  # R3
        self._httpx = httpx
        self._headers = {"User-Agent": user_agent}  # R10
        self._timeout = timeout

    def get(self, url: str) -> FetchResult:
        try:
            resp = self._httpx.get(url, headers=self._headers, timeout=self._timeout,
                                   follow_redirects=True)
        except Exception as exc:
            raise FetchError(f"GET failed for {url}: {exc}") from exc
        return FetchResult(url=str(resp.url), status_code=resp.status_code,
                           text=resp.text)
```

> Aunque `httpx` está pineado en `requirements.txt` desde f9, el subpaquete usa el
> mismo **import perezoso** para no acoplar la importabilidad del módulo a httpx y
> mantener el patrón uniforme (R25); el `FakeFetcher` cubre la suite por defecto.

`FakeFetcher` (red-free, R4): mapa `url -> FetchResult` (o `(status, text)`)
predefinido en el test; `get(url)` lo devuelve o eleva `FetchError`/404 según
configuración. Registra las URLs solicitadas para que los tests verifiquen que las
URLs prohibidas por robots NUNCA se piden (R5/R6).

## 5. `RobotsGate` — cumplimiento de robots.txt (R5, R6, R7)

`src/wowrag/ingest/wowhead/robots.py`. Usa **stdlib** `urllib.robotparser`
(`RobotFileParser`); SIN dependencia nueva.

```python
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser


class RobotsGate:
    """Decides if a URL may be fetched, per the host's robots.txt + UA.
    Caches one RobotFileParser per host (R7)."""

    def __init__(self, user_agent: str, fetcher: Fetcher) -> None:
        self._ua = user_agent
        self._fetcher = fetcher            # reuse the same Fetcher (UA, rate-limit upstream)
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        host = urlsplit(url)._replace(path="", query="", fragment="")
        rp = self._cache.get(host.netloc)
        if rp is None:
            rp = self._load(host)          # GET {scheme}://{host}/robots.txt via Fetcher
            self._cache[host.netloc] = rp  # R7: cache per host
        return rp.can_fetch(self._ua, url)  # R5
```

- `allowed(url)` se consulta **antes** de cada fetch real (R5). El `WowheadIngestor`
  omite la URL si `allowed` es `False` (R6).
- `robots.txt` se obtiene a través del MISMO `Fetcher` (sujeto a UA y, en la
  pipeline, al rate-limit), parseando el cuerpo con `rp.parse(text.splitlines())`.
  Cachea un `RobotFileParser` por host (R7) — el segundo URL del mismo host NO
  vuelve a pedir robots.
- SI robots.txt no existe/da error → política **permisiva documentada** (tratar
  como "permitido"), registrada; alternativamente conservadora, ver §11. Tests
  fijan el comportamiento con `FakeFetcher`.

## 6. `RateLimiter` — throttling cortés (R8, R9, R11)

`src/wowrag/ingest/wowhead/throttle.py`. Reloj y `sleep` **inyectables** para
testear sin tiempo de pared (R11) — patrón "fake clock".

```python
from typing import Callable


class RateLimiter:
    """Enforces a minimum interval between successive acquire() calls (R8, R9)."""

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,   # injectable (R11)
        sleep: Callable[[float], None] = time.sleep,    # injectable (R11)
    ) -> None:
        self._min = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def acquire(self) -> None:
        now = self._clock()
        if self._last is not None:
            wait = self._min - (now - self._last)
            if wait > 0:
                self._sleep(wait)            # R9: throttle
        self._last = self._clock()
```

- `acquire()` se llama antes de cada GET real en la pipeline (R8). Si han pasado
  menos de `min_interval_s` desde el último, espera la diferencia (R9).
- Tests inyectan un reloj fake (lista de timestamps) y un `sleep` espía que
  registra las esperas, verificando el throttle sin dormir de verdad (R11).

## 7. Config: campos de scraper en `Settings` (R8, R10, R17, R21)

`src/wowrag/config.py` — EDITAR añadiendo SOLO campos nuevos opcionales con
default sano (sin tocar claves existentes; mismo criterio que f10 con
`eval_dataset_path`):

```python
scrape_user_agent: str = "wow-classic-rag-bot/0.1 (+https://github.com/.../wow-classic-rag)"  # R10
scrape_min_interval_s: float = 1.0          # rate limit entre peticiones (R8)
scrape_allowed_host: str = "www.wowhead.com"  # allowlist de host (R17, R18)
scrape_max_pages: int = 100                 # tope de páginas por ejecución (defensa)
scrape_corpus_path: str = "data/corpus"     # directorio de salida del JSONL (R21)
```

- Defaults conservadores y corteses (1 s entre peticiones, UA identificable con
  URL de contacto). El operador los endurece por entorno (`.env`).
- `scrape_corpus_path` es el **directorio** donde se escribe `wowhead.jsonl`, de
  modo que el `JsonlCorpusLoader` (que lee `*.jsonl` de un directorio) lo consuma
  directo (R20, R21).

## 8. `WowheadNormalizer` — HTML → `Document` (R12–R16, R31)

`src/wowrag/ingest/wowhead/normalizer.py`. La librería de parsing se importa
**perezosamente** dentro de `__init__` (R25); si falta, `ScrapeError` (R31).

### 8.1 Dependencia de parsing elegida: `selectolax`

| Candidata | Pros | Contras | Decisión |
|-----------|------|---------|----------|
| `beautifulsoup4` + `lxml` | Ubicua, API rica | Dos deps; lxml compila C; más pesada | Alternativa |
| **`selectolax`** | Una sola dep, wheels binarios (sin toolchain C), muy rápida, API CSS simple | Menos conocida | **Elegida** |

Decisión: **`selectolax`** (`pip install selectolax`) — una única dependencia con
wheels precompiladas, parser HTML rápido y selectores CSS suficientes para extraer
título, secciones y limpiar boilerplate. Importada lazy (R25). Si el implementer
prefiere `beautifulsoup4`+`lxml`, es aceptable siempre que se respeten R25/R31 y
los selectores cubran R12–R16.

> **Desviación registrada en review (change-round 1).** El plan original aislaba
> `selectolax` en `requirements-scrape.txt`, FUERA de `init.sh` (R24). El revisor
> de Slice B detectó que esto deja la lógica central de f11 (normalizador HTML →
> `Document`: R12/R14/R15, decisión de R16 y el round-trip real R20) **sin
> cobertura efectiva en CI**: los tests parser-backed quedaban *skipped* porque
> `init.sh` no instalaba el parser, incumpliendo R29 para la parte central. Por eso
> `selectolax==0.4.10` se **movió a `requirements.txt`** (pineado) y se eliminó
> `requirements-scrape.txt`. Razonamiento: (1) `selectolax` es un parser **ligero**
> de wheel binario (sin toolchain C, sin GPU/DB/servicio vivo), categóricamente
> distinto de torch/sentence-transformers/psycopg/Ollama —que siguen diferidos por
> su peso o por exigir servicios reales—; (2) **precedente f9**: httpx/fastapi/uvicorn
> se promovieron DEFERRED→PINNED por la misma razón (la suite por defecto ejercita
> la app vía TestClient); (3) `docs/verification.md` exige que cada `R<n>` tenga un
> test que **pase** (no *skipped*). El import **sigue siendo lazy** dentro de
> `WowheadNormalizer.__init__` (R25) y un parser ausente sigue elevando `ScrapeError`
> (R31): el patrón defensivo se mantiene aunque ahora sea dep por defecto. R24 queda
> **relajado** para `selectolax` (se reinterpreta: aislar lo *pesado*, no lo ligero
> que la suite por defecto necesita).

```python
class WowheadNormalizer:
    def __init__(self) -> None:
        try:
            from selectolax.parser import HTMLParser  # lazy import (R25)
        except ImportError as exc:
            raise ScrapeError(
                "HTML parser not installed. Install scrape deps: "
                "pip install -r requirements-scrape.txt"
            ) from exc  # R31
        self._HTMLParser = HTMLParser

    def normalize(self, html: str, source_url: str) -> Document | None:
        tree = self._HTMLParser(html)
        self._strip_boilerplate(tree)             # R12
        title = self._extract_title(tree)         # R14
        section = self._extract_section(tree)     # R15 ("" si no hay)
        text = self._extract_text(tree)           # R12
        if not text.strip():
            return None                           # R16: no emitir Document vacío
        return Document(text=text, source_url=source_url, title=title, section=section)
```

### 8.2 Estrategia de extracción (R12, R14, R15) y limpieza de boilerplate (R12, R16)

- **Boilerplate (R12):** eliminar nodos `script`, `style`, `nav`, `header`,
  `footer`, `aside`, y contenedores de anuncios/menús conocidos de wowhead por
  selector CSS (lista declarada como constante de módulo, ej. `#header`,
  `.ad`, `#nav`, `.menu`, `[role=navigation]`). Documentar que la lista es
  ajustable; los fixtures la ejercitan.
- **Texto principal (R12):** extraer el texto del contenedor principal de
  contenido de wowhead (ej. `#main-contents`/`.text`); fallback al `<body>`
  limpio. Normalizar espacios en blanco.
- **`title` (R14):** del `<title>` o `<h1>` de la página (preferir `<h1>` del
  contenido si existe; si no, `<title>`).
- **`section` (R15):** del encabezado de sub-sección visible (ej. primer `<h2>`
  del contenido); `""` si no hay (default de `Document.section`).
- **R16:** si tras limpiar no queda texto → devolver `None`; la pipeline lo omite
  y registra, evitando construir un `Document` con `text` vacío (que f1 rechaza).

## 9. `WowheadIngestor` — pipeline (R5–R9, R16, R17–R21, R23)

`src/wowrag/ingest/wowhead/pipeline.py`. Compone fetcher + robots + rate-limit +
normalizer; depende de la INTERFAZ `Fetcher` (inyectada) y de colaboradores
inyectados → testeable end-to-end con fakes (R29).

```python
class WowheadIngestor:
    def __init__(
        self,
        fetcher: Fetcher,
        robots: RobotsGate,
        limiter: RateLimiter,
        normalizer: WowheadNormalizer,
        *,
        allowed_host: str,
        max_pages: int,
    ) -> None: ...

    def run(self, seed_urls: list[str], out_dir: str | Path) -> IngestReport:
        # Para cada URL (hasta max_pages):
        #   1. allowlist: descartar si host != allowed_host (R18)
        #   2. robots: si not robots.allowed(url) -> skip + log (R5, R6)
        #   3. limiter.acquire()  (R8, R9)
        #   4. result = fetcher.get(url)  (R10 via fetcher headers)
        #   5. doc = normalizer.normalize(result.text, result.url)  (R12-R15)
        #   6. si doc is None -> skip + log (R16); si no -> append a la lista
        # Escribe todos los docs como JSONL en out_dir/wowhead.jsonl (R19)
        # Devuelve IngestReport (counts) (R23)
```

- **Orden estricto** allowlist → robots → rate-limit → fetch → normalize, de modo
  que una URL prohibida por allowlist/robots **nunca** llega a `fetcher.get`
  (verificable porque `FakeFetcher` registra las URLs solicitadas) (R6, R18).
- **Escritura JSONL (R19):** por cada `Document`, `out.write(doc.model_dump_json()
  + "\n")` en `out_dir/wowhead.jsonl`, UTF-8. Crea `out_dir` si no existe. El
  fichero resultante es exactamente el formato que `JsonlCorpusLoader` lee (R20).
- **`IngestReport`** (modelo pydantic local del subpaquete, NO en `models.py`):
  `requested`, `skipped_robots`, `skipped_allowlist`, `skipped_empty`,
  `documents_written`, `out_path`. La CLI lo imprime (R23).

## 10. CLI / entrypoint: `python -m wowrag.ingest.wowhead` (R22, R23, R25)

`src/wowrag/ingest/wowhead/cli.py` + `__main__.py`. Patrón EXACTO de
`wowrag.eval` (f10): `__main__.py` → `raise SystemExit(main())`; `main` con
colaboradores **inyectables** para tests; composición real **perezosa**.

```python
# __main__.py
from wowrag.ingest.wowhead.cli import main
raise SystemExit(main())
```

```python
# cli.py (esquema)
def main(argv: list[str] | None = None, fetcher: Fetcher | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m wowrag.ingest.wowhead")
    parser.add_argument("urls", nargs="+", help="seed wowhead URL(s)")     # R17
    parser.add_argument("--out", type=Path, default=None,
                        help="output corpus dir (default: Settings.scrape_corpus_path)")  # R21
    args = parser.parse_args(argv)

    settings = Settings()                         # lazy: dentro de main
    out_dir = args.out or Path(settings.scrape_corpus_path)
    f = fetcher if fetcher is not None else _build_fetcher(settings)  # lazy real fetcher
    ingestor = _build_ingestor(f, settings)       # robots + limiter + normalizer
    report = ingestor.run(args.urls, out_dir)
    print(_format_summary(report))                # R23
    return 0
```

- **Inyectable (R29):** `main(argv, fetcher=fake)` permite a `test_wowhead_cli.py`
  pasar un `FakeFetcher` y NUNCA construir el `HttpxFetcher` real ni tocar red.
- **Composición perezosa (R25):** `_build_fetcher`/`_build_ingestor` instancian
  `HttpxFetcher` y `WowheadNormalizer` (que hacen su import lazy de httpx/parser)
  SOLO al ejecutarse sin inyección. Importar `wowrag.ingest.wowhead.cli` no
  arrastra httpx ni el parser (R25).
- **Resumen stdout (R23):** imprime los counts del `IngestReport`.

## 11. Política de cortesía / ética (documentada — requisito, no extra)

f11 es la única feature que contacta un servicio de terceros; la política es
explícita:

1. **robots.txt primero (R5–R7):** ninguna URL se solicita sin comprobar
   `robots.txt` del host para el User-Agent configurado. Las URLs prohibidas se
   omiten, no se fuerzan.
2. **Rate limit por defecto cortés (R8, R9):** ≥ 1 s entre peticiones (default),
   configurable al alza. Una sola conexión secuencial (sin paralelismo agresivo).
3. **User-Agent identificable (R10):** descriptivo y con URL de contacto, para que
   wowhead pueda identificar/contactar al cliente.
4. **Allowlist de host (R17, R18):** solo se escrapea el host de wowhead
   configurado; nada de seguir enlaces fuera de dominio.
5. **Tope de páginas (`scrape_max_pages`):** defensa contra ejecuciones
   descontroladas.
6. **Cache de robots por host (R7):** evita re-descargar robots.txt repetidamente.
7. **robots.txt inaccesible:** por defecto **permisivo y registrado** (se asume
   permitido si el host no publica robots o devuelve error), documentado aquí;
   el operador puede endurecerlo. Alternativa conservadora (asumir prohibido)
   considerada y descartada por defecto para no bloquear hosts sin robots.

## 12. Estrategia de tests (todos network-free; corren con `init.sh`)

Trazabilidad `R<n>` ↔ test obligatoria (comenta cada test con su `R<n>`). Fakes y
fixtures, `tmp_path` para salida; **nada de red** salvo los `@integration`.

- **`FakeFetcher`** (implementa `Fetcher`): mapa URL → `FetchResult`; registra las
  URLs solicitadas. Vive en el test/`conftest`, no en `src/`.
- **Fixtures HTML** en `tests/fixtures/wowhead/`: una página de wowhead realista
  con boilerplate (`spell_fireball.html`) y una sin texto principal
  (`empty_body.html`).
- **Reloj/sleep fake** para `RateLimiter`.

- `tests/test_wowhead_fetcher.py`:
  - `test_fetcher_protocol` / `test_fake_fetcher_returns_mapped` (R1, R4).
  - `test_httpx_fetcher_missing_dep_raises_fetcherror`: simula ausencia de httpx
    → `FetchError` (no `ImportError`) (R3).
  - `test_httpx_fetcher_sets_user_agent`: el header UA se envía (R10) (con cliente
    httpx mockeado/`MockTransport`, sin red).
  - `test_import_module_is_lazy`: importar el módulo no importa httpx (R25).
- `tests/test_wowhead_robots.py`:
  - `test_allows_when_robots_permits` / `test_skips_when_disallowed` con
    `FakeFetcher` sirviendo un robots.txt (R5, R6).
  - `test_disallowed_url_never_fetched`: la URL prohibida NO aparece en las URLs
    solicitadas del `FakeFetcher` (R6).
  - `test_robots_cached_per_host`: dos URLs del mismo host → robots.txt pedido una
    sola vez (R7).
- `tests/test_wowhead_throttle.py`:
  - `test_first_acquire_no_wait` (R8).
  - `test_second_acquire_within_interval_sleeps`: reloj fake → `sleep` espía
    recibe la diferencia correcta (R9).
  - `test_acquire_uses_injected_clock`: sin tiempo de pared real (R11).
- `tests/test_wowhead_normalizer.py` (requiere el parser instalado; si se aísla,
  marcar import-guard test aparte):
  - `test_normalize_populates_document_fields`: `text`/`source_url`/`title`/
    `section` poblados desde el fixture (R12, R13, R14, R15).
  - `test_boilerplate_stripped`: nav/ads/script no aparecen en `text` (R12).
  - `test_section_empty_when_absent`: `section == ""` (R15).
  - `test_empty_body_returns_none`: fixture sin texto → `None` (R16).
  - `test_missing_parser_raises_scrapeerror`: sin la dep → `ScrapeError` (R31).
  - `test_import_module_is_lazy`: importar el módulo no importa el parser (R25).
- `tests/test_wowhead_pipeline.py`:
  - `test_run_writes_jsonl`: `WowheadIngestor.run` con `FakeFetcher` → escribe
    `out_dir/wowhead.jsonl` (R19).
  - `test_output_roundtrips_through_jsonl_loader`: cargar el fichero escrito con
    `JsonlCorpusLoader` devuelve `Document`s equivalentes (R20) — **prueba clave
    del handoff**.
  - `test_disallowed_and_off_allowlist_skipped`: URLs prohibidas/foráneas no se
    escriben ni se solicitan (R6, R18).
  - `test_empty_document_skipped`: página sin texto no genera línea (R16).
  - `test_report_counts`: el `IngestReport` refleja requested/skipped/written
    (R23).
- `tests/test_wowhead_cli.py`:
  - `test_main_runs_with_injected_fetcher`: `main([url], fetcher=fake)` retorna 0 y
    escribe el corpus en `tmp_path` (R22).
  - `test_main_prints_summary`: stdout con los counts (R23).
  - `test_cli_uses_settings_out_default`: sin `--out`, usa
    `Settings.scrape_corpus_path` (R21).
  - `test_import_cli_is_network_free`: `import wowrag.ingest.wowhead.cli` no importa
    httpx ni el parser (R25).
- **Integración (`@pytest.mark.integration`, fuera de `init.sh`)** (R30):
  - `test_live_fetch_respects_robots`: un fetch real contra wowhead vivo,
    comprobando robots + UA; excluido por defecto.

## 13. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Pasar `Document`s en memoria al `IndexingPipeline` (sin JSONL) | Acopla scraping (red, lento) a indexado (GPU/DB); re-indexar exigiría re-escrapear; rompe la separación offline. JSONL reutiliza el camino f1+f4 sin tocarlo (§0) |
| ~~Poner el parser HTML en `requirements.txt` / `init.sh`~~ (decisión revertida en review) | Plan original: aislar en `requirements-scrape.txt` para no engordar `init.sh`. **Revertido en change-round 1** (ver §8.1): aislarlo dejaba la lógica central de f11 sin cobertura efectiva en CI (tests parser-backed *skipped*, R29 incumplido). `selectolax` es ligero (wheel binario, sin toolchain C) y, como httpx/fastapi en f9, lo necesita la suite por defecto → va en `requirements.txt` pineado, con import lazy + `ScrapeError` (R25, R31). El aislamiento sigue valiendo para lo PESADO (torch/sentence-transformers/psycopg/Ollama) |
| `Fetcher` que también hace robots + rate-limit | Mezcla responsabilidades; el revisor rechaza HTTP+robots+throttle en una clase. Robots y rate-limit son colaboradores que envuelven al `Fetcher` en la pipeline (§3, §9) |
| Implementar el chequeo de robots a mano (parseo propio) | `urllib.robotparser` de la stdlib ya lo hace correctamente y sin dependencia nueva (R5) |
| `requests` como cliente HTTP | `httpx` ya está pineado (f9) y es el cliente del proyecto; añadir `requests` duplicaría dependencias (§4) |
| `beautifulsoup4`+`lxml` por defecto | Dos dependencias y compilación C de lxml; `selectolax` es una sola dep con wheels binarios y más rápida. BS4 queda como alternativa aceptable si se respetan R24/R25/R31 (§8.1) |
| Rate-limit con `time.sleep`/`time.monotonic` hardcodeados | No testeable sin tiempo de pared; el reloj y el sleep se inyectan (R11) (§6) |
| f11 invoca el `IndexingPipeline` al final | Mezcla fases (fetch vs index, GPU/DB). f11 solo produce el corpus; el indexado se corre aparte sobre el directorio de salida (§0) |
| Crawling recursivo sin allowlist ni tope | Riesgo ético/operacional; el seed/allowlist y `scrape_max_pages` lo acotan (R17, R18) |
| Añadir endpoint HTTP de ingesta | HTTP es f9; f11 es script/librería offline (R28) |
