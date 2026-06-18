# Requirements — f11-wowhead-ingestion

> Feature: `f11-wowhead-ingestion` — `[LATER]` Wowhead ingestion / scraper.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es verificable por
> al menos un test (ver `docs/verification.md`). Depende de
> `f1-document-model-loader` (`done`).

## Alcance

Esta feature establece la **única** parte del sistema que toca un servicio de red
externo real (wowhead). Su trabajo es: **fetch → normalizar → emitir `Document`s →
escribir un corpus JSONL local** que el loader de f1 (`JsonlCorpusLoader`) y el
indexador de f4 (`IndexingPipeline`) **ya** consumen sin cambios. Hasta que f11 se
ejecute de verdad, el resto del sistema solo se ha validado con fakes; f11 es lo
que habilita un corpus end-to-end real.

f11 trata la **ética/compliance** (robots.txt, rate-limit, User-Agent
identificable) y la **testabilidad sin red** como requisitos de primera clase, no
como extras opcionales.

### Componentes que f11 introduce

1. Una **abstracción `Fetcher`** (Protocol) para HTTP GET, con implementación real
   (lazy `httpx`) y un **fake** para tests sin red.
2. **Cumplimiento de `robots.txt`** antes de cada petición (stdlib
   `urllib.robotparser`; sin dependencia nueva).
3. **Rate limiting** configurable (intervalo mínimo entre peticiones) y
   **User-Agent identificable**; política de cortesía documentada.
4. Un **normalizador HTML → `Document`** que parsea HTML de wowhead a los campos
   del esquema f1 (`text`, `source_url`, `title`, `section`), aislando la
   dependencia de parsing en `requirements-scrape.txt` con import perezoso.
5. Una **pipeline/entrypoint de ingesta** (CLI `python -m wowrag.ingest.wowhead`)
   que, dada una semilla, hace fetch (robots + rate-limited) → normaliza → emite
   `Document`s → escribe un corpus JSONL.

### Fuera de alcance (explícito)

- f11 **no** reimplementa chunking (f2), embeddings (f3), vector store / indexado
  (f4), retrieval (f5) ni generación (f6–f8). Produce `Document`s en el esquema f1
  y alimenta el **pipeline existente** (R19, R20). **No modifica el esquema
  `Document`** ni la lógica de f1–f10 (R26, R27).
- f11 **no** reordena (eso es f12) y **no** añade ningún endpoint HTTP (eso es
  territorio de f9) (R28).
- f11 **no** descubre wowhead recursivamente sin control: el seed/allowlist y los
  límites de páginas/profundidad son explícitos y configurables (R17, R18).
- Respetar robots, rate-limit e identificarse con un User-Agent descriptivo son
  **requisitos**, no opciones (R5–R11).

## Decisión de handoff: corpus JSONL local (no `Document`s en memoria)

El handoff por defecto es **escribir un corpus JSONL en disco** que el
`JsonlCorpusLoader` de f1 ya lee, en vez de pasar `Document`s en memoria
directamente al `IndexingPipeline`. Justificación en `design.md` §0; los
requisitos R19–R21 fijan el contrato del fichero.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Deferred. Fetches and normalizes wowhead content into the Document schema,
> respecting robots/rate limits."

| Fragmento del acceptance                         | Requisitos que lo cubren        |
|--------------------------------------------------|---------------------------------|
| Fetches … wowhead content                        | R1, R2, R3, R4                  |
| normalizes … into the Document schema            | R12, R13, R14, R15, R16         |
| respecting robots                                | R5, R6, R7                      |
| / rate limits                                    | R8, R9, R10, R11                |
| (handoff al pipeline existente — implícito)      | R19, R20, R21                   |
| (entrypoint ejecutable — implícito en "Fetches") | R17, R18, R22, R23              |
| (Deferred / aislado y testeable — implícito)     | R24, R25, R29, R30, R31         |

## Requisitos

### Abstracción `Fetcher` (Protocol) + fake

**R1** — El sistema DEBE definir una interfaz `Fetcher` (Protocol o ABC) con una
operación que, dada una URL, devuelva el cuerpo de la respuesta HTTP como texto
junto con su código de estado.

**R2** — El sistema DEBE proveer una implementación concreta `HttpxFetcher` de
`Fetcher` que realice el GET real mediante `httpx`, seleccionable como punto único
de composición (sin acoplar el resto del código a la implementación concreta).

**R3** — SI `httpx` no está instalado CUANDO se instancia `HttpxFetcher`, ENTONCES
el sistema DEBE lanzar una excepción de dominio clara que indique instalar
`requirements-scrape.txt`, y NO un `ImportError` crudo.

**R4** — El sistema DEBE proveer un `FakeFetcher` que devuelva respuestas
predefinidas (mapa URL → (texto, estado)) sin realizar ninguna petición de red,
para uso en tests.

### Cumplimiento de robots.txt

**R5** — ANTES de solicitar cualquier URL, el sistema DEBE comprobar el permiso de
fetch consultando el `robots.txt` del host (vía `urllib.robotparser` de la stdlib)
usando el User-Agent configurado.

**R6** — SI `robots.txt` no permite el fetch de una URL para el User-Agent
configurado, ENTONCES el sistema DEBE omitir esa URL sin solicitarla y registrar
el motivo, sin abortar la ingesta del resto de URLs.

**R7** — CUANDO el `robots.txt` de un host ya ha sido obtenido durante una
ejecución, el sistema DEBE reutilizar el resultado cacheado para las siguientes
URLs del mismo host en lugar de volver a descargarlo.

### Rate limiting y User-Agent

**R8** — El sistema DEBE imponer un intervalo mínimo configurable entre peticiones
HTTP sucesivas (rate limit), tomando el valor de `Settings`.

**R9** — CUANDO dos peticiones consecutivas ocurren con menos del intervalo
mínimo configurado entre ellas, el sistema DEBE esperar (throttle) hasta cumplir
ese intervalo antes de emitir la segunda petición.

**R10** — El sistema DEBE enviar en cada petición un encabezado `User-Agent`
descriptivo e identificable, tomado de `Settings`, que permita a wowhead reconocer
al cliente.

**R11** — El componente de rate limiting DEBE recibir su fuente de tiempo y de
espera por inyección (reloj/`sleep` inyectables) de modo que su lógica sea
verificable en tests sin tiempo de pared real.

### Normalización HTML → `Document`

**R12** — CUANDO se le entrega el HTML de una página de wowhead, el sistema DEBE
producir un `Document` (esquema f1) cuyo `text` sea el contenido textual principal
de la página con el boilerplate (navegación, anuncios, pies, scripts) eliminado.

**R13** — El sistema DEBE poblar `source_url` del `Document` con la URL canónica de
la página de la que procede el contenido.

**R14** — El sistema DEBE poblar `title` del `Document` con el título legible de la
página de wowhead extraído del HTML.

**R15** — El sistema DEBE poblar `section` del `Document` con el encabezado de
sub-sección correspondiente cuando exista, y con cadena vacía (`""`) CUANDO la
página no aporte una sub-sección.

**R16** — SI el HTML no contiene texto principal extraíble tras eliminar el
boilerplate, ENTONCES el sistema DEBE omitir esa página sin emitir un `Document`
de `text` vacío (que violaría la validación de f1) y registrar la omisión.

### Pipeline de ingesta y CLI

**R17** — El sistema DEBE aceptar una o varias URLs semilla (o una lista de URLs)
como entrada de la ingesta, restringidas a un host/allowlist de wowhead
configurable.

**R18** — SI una URL de entrada queda fuera del host/allowlist de wowhead
configurado, ENTONCES el sistema DEBE rechazarla u omitirla sin solicitarla.

**R19** — CUANDO la ingesta procesa las URLs permitidas, el sistema DEBE escribir
los `Document`s normalizados en un fichero de corpus `.jsonl` (un objeto JSON por
línea, con los campos de `Document`) en una ruta de salida configurable.

**R20** — El corpus `.jsonl` emitido por f11 DEBE ser cargable sin cambios por el
`JsonlCorpusLoader` de f1, devolviendo `Document`s equivalentes a los emitidos.

**R21** — El sistema DEBE tomar la ruta de salida del corpus por defecto desde
`Settings` cuando no se especifique por argumento, sin exigir variables de entorno
para el resto del camino por defecto.

**R22** — El sistema DEBE exponer un entrypoint ejecutable
`python -m wowrag.ingest.wowhead` que ejecute la ingesta de extremo a extremo
(fetch con robots + rate-limit → normalizar → escribir corpus) y devuelva un
código de salida 0 en caso de éxito.

**R23** — CUANDO la ingesta termina, el sistema DEBE emitir por stdout un resumen
con, al menos, el número de URLs solicitadas, omitidas por robots/allowlist y
`Document`s escritos.

### Aislamiento de dependencias e importabilidad

**R24** — El sistema DEBE declarar la dependencia de parsing de HTML en un fichero
`requirements-scrape.txt` independiente, **NO** en `requirements.txt` ni instalado
por `init.sh`, con versión pineada.

**R25** — Importar cualquier módulo de `wowrag.ingest.wowhead` NO DEBE importar de
forma eager ni la librería de parsing de HTML ni `httpx`; ambas se importan de
forma perezosa solo al instanciar la implementación real correspondiente.

**R31** — SI la librería de parsing de HTML no está instalada CUANDO se instancia
el normalizador real, ENTONCES el sistema DEBE lanzar una excepción de dominio
clara que indique instalar `requirements-scrape.txt`, y NO un `ImportError` crudo.

### Testabilidad

**R29** — La lógica de f11 (robots, rate-limit, normalización, pipeline)
DEBE ser testeable con `FakeFetcher`, ficheros HTML de fixture, un reloj/`sleep`
inyectables y `tmp_path`, sin realizar ninguna petición de red, de modo que toda
la suite por defecto de f11 corra dentro de `./init.sh` (`not integration`).

**R30** — DONDE un test ejerza un fetch real contra wowhead vivo, ese test DEBE
estar marcado `@pytest.mark.integration` para quedar excluido de la suite por
defecto.

### Alcance diferido / no-regresión

**R26** — El sistema NO DEBE modificar el esquema `Document` de f1 ni las
interfaces/lógica de f1–f10; f11 las CONSUME tal cual.

**R27** — El sistema NO DEBE reimplementar chunking (f2), embeddings (f3),
vector store / indexado (f4), retrieval (f5) ni generación (f6–f8); el corpus
emitido alimenta el pipeline existente.

**R28** — El sistema NO DEBE añadir ningún endpoint HTTP (f9) ni lógica de
reordenado (f12) como parte de f11.
