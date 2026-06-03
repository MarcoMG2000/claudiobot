# Requirements — f1-document-model-loader

> Feature: `f1-document-model-loader` — Document model + local corpus loader.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es verificable por
> al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. El **modelo de datos `Document`** (campo `text` + metadata `source_url`,
   `title`, `section`), consistente con el patrón pydantic de f0.
2. Un **loader de corpus local** que lee un directorio de ficheros y devuelve una
   colección de `Document`, detrás de una interfaz swappable (principio "every
   component behind a swappable interface" de `docs/architecture.md` §4).
3. El **formato de corpus soportado** (JSONL como formato principal; ver §Decisión
   de formato) y su validación.
4. El **manejo de errores** de E/S y de datos malformados.

### Fuera de alcance (explícito)

- **El scraping/fetch real de wowhead queda diferido a `f11-wowhead-ingestion`.**
  Esta feature NO realiza ninguna petición de red, ni parsea HTML, ni respeta
  robots/rate-limits. Solo lee un directorio de corpus **ya materializado** en
  disco local.
- Chunking (`f2-chunking`), embeddings, store, retrieval y generación: fuera.

## Decisión de formato

El formato de corpus principal es **JSONL** (un objeto JSON por línea, cada
objeto = un `Document`). Justificación:

- Cada línea mapea 1:1 a un `Document` con sus campos de metadata explícitos
  (`text`, `source_url`, `title`, `section`), sin ambigüedad de parsing.
- Es streamable línea a línea (escala a corpus grandes sin cargar todo en
  memoria) y es el formato natural de salida del futuro scraper (`f11`).
- Errores se aíslan por línea: una línea malformada no invalida el fichero
  entero (ver R8).

Alternativa descartada: Markdown + frontmatter (ver `design.md` §Alternativa
descartada).

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "A Document schema (text + metadata: source_url, title, section) and a loader
> that reads a local corpus directory. Real wowhead scraping is deferred to a
> later feature."

| Fragmento del acceptance                                   | Requisitos que lo cubren |
|------------------------------------------------------------|--------------------------|
| A Document schema (text + metadata: source_url,title,section) | R1, R2, R3            |
| a loader that reads a local corpus directory               | R4, R5, R6, R7           |
| (formato de fichero y validación — implícito en "loader")  | R6, R9, R10              |
| (manejo de errores — implícito en "loader")                | R7, R8                   |
| Real wowhead scraping is deferred to a later feature       | R11                      |

## Requisitos

### Modelo `Document`

**R1** — El sistema DEBE proveer un modelo `Document` con un campo obligatorio
`text` (str) y los campos de metadata `source_url` (str), `title` (str) y
`section` (str).

**R2** — SI se intenta construir un `Document` sin el campo `text` o con `text`
vacío tras recortar espacios, ENTONCES el sistema DEBE lanzar un error de
validación que identifique el campo `text`.

**R3** — El sistema DEBE permitir que el campo `section` sea opcional, tomando un
valor por defecto vacío (`""`) CUANDO no se proporcione, mientras que
`source_url` y `title` permanecen obligatorios.

### Interfaz del loader

**R4** — El sistema DEBE definir una interfaz `CorpusLoader` (Protocol o ABC) con
un método que, dada una ruta de directorio, devuelva una colección iterable de
`Document`.

**R5** — El sistema DEBE proveer una implementación concreta `JsonlCorpusLoader`
de `CorpusLoader` seleccionable como punto único de composición (sin acoplar el
resto del código a la implementación concreta).

### Lectura del directorio de corpus

**R6** — CUANDO se invoca el loader sobre un directorio que contiene uno o más
ficheros `.jsonl`, el sistema DEBE leer cada línea no vacía como un objeto JSON y
construir un `Document` por línea, devolviendo todos los `Document` resultantes.

**R7** — SI la ruta de corpus proporcionada al loader no existe o no es un
directorio, ENTONCES el sistema DEBE lanzar una excepción clara que identifique
la ruta solicitada.

**R8** — SI una línea de un fichero `.jsonl` no es JSON válido o no contiene los
campos obligatorios de `Document`, ENTONCES el sistema DEBE lanzar una excepción
clara que identifique el fichero y el número de línea infractor.

**R9** — CUANDO el directorio de corpus no contiene ningún fichero `.jsonl`, el
sistema DEBE devolver una colección vacía de `Document` sin lanzar excepción.

**R10** — El sistema DEBE ignorar las líneas en blanco (vacías o solo espacios)
de un fichero `.jsonl` sin contarlas como error ni producir `Document` por ellas.

### Determinismo y alcance diferido

**R11** — El sistema DEBE realizar la carga del corpus **sin** efectuar ninguna
petición de red ni acceso a servicios externos (el scraping real de wowhead se
difiere a `f11-wowhead-ingestion`).
