# Tasks — f1-document-model-loader

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests usan `tmp_path`, sin servicios reales (sin Postgres, Ollama ni
> red). La trazabilidad `R<n>` ↔ test es obligatoria (`docs/verification.md`);
> nombra/comenta cada test con su `R<n>`. NO marques la feature `done` ni edites
> `feature-list.json` (eso es del leader/reviewer).

## Implementación

- [x] **T1 — Modelo `Document`.** Crear `src/wowrag/models.py` con el modelo
  pydantic `Document` (`text`, `source_url`, `title` obligatorios; `section: str
  = ""`) y un `field_validator` que rechace `text` vacío o solo espacios.
  _(Cubre R1, R2, R3)_

- [x] **T2 — Interfaz `CorpusLoader` y excepciones.** Crear
  `src/wowrag/ingest/base.py` con el `Protocol` `CorpusLoader`
  (`load(corpus_dir) -> list[Document]`) y las excepciones `CorpusError`,
  `CorpusNotFoundError`, `MalformedCorpusError` (design §3).
  _(Cubre R4, R7, R8)_

- [x] **T3 — Implementación `JsonlCorpusLoader`.** Crear
  `src/wowrag/ingest/loader.py` con `JsonlCorpusLoader.load(corpus_dir)` que:
  enumera `*.jsonl` de forma ordenada, construye un `Document` por línea no
  vacía, ignora líneas en blanco, lanza `CorpusNotFoundError` si la ruta no es
  directorio, y `MalformedCorpusError` (con fichero + nº de línea) ante JSON
  inválido o `Document` inválido. No usa red ni servicios.
  _(Cubre R5, R6, R7, R8, R9, R10, R11)_

- [x] **T4 — Exports del paquete `ingest`.** Reemplazar el placeholder
  `src/wowrag/ingest/__init__.py` para exportar `CorpusLoader`,
  `JsonlCorpusLoader`, `CorpusError`, `CorpusNotFoundError`,
  `MalformedCorpusError`. _(Cubre R5)_

## Tests (un fichero por módulo, `tmp_path`, sin servicios reales)

- [x] **T5 — `tests/test_models.py`.**
  - `Document(text=..., source_url=..., title=..., section=...)` válido se
    construye y conserva los campos (R1).
  - `Document` sin `section` → `section == ""` (R3).
  - `Document(text="")` y `Document(text="   ")` → `ValidationError` mencionando
    `text` (R2).
  - Falta de un campo obligatorio (`source_url`/`title`) → `ValidationError` (R2).
  _(Cubre R1, R2, R3)_

- [x] **T6 — `tests/test_corpus_loader.py`.**
  - Escribir uno o varios `.jsonl` válidos en `tmp_path`; `load` devuelve un
    `Document` por línea con la metadata correcta (R6).
  - Directorio sin ficheros `.jsonl` (o vacío) → `[]` (R9).
  - Fichero con líneas en blanco intercaladas → se ignoran, no producen
    `Document` (R10).
  - Ruta inexistente / fichero (no directorio) → `CorpusNotFoundError` cuyo
    mensaje contiene la ruta (R7).
  - Línea con JSON inválido → `MalformedCorpusError` cuyo mensaje contiene el nº
    de línea (R8).
  - Línea JSON válida pero sin `text` → `MalformedCorpusError` (R8).
  - `JsonlCorpusLoader` es usable a través del tipo `CorpusLoader` /
    `isinstance`-compatible con el `Protocol` (R4, R5).
  - El conjunto de tests pasa offline, sin fixtures de red ni servicios (R11).
  _(Cubre R4, R5, R6, R7, R8, R9, R10, R11)_

## Cierre

- [x] **T7 — Verificación.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite (no-integration) en verde, incluyendo los nuevos tests de f1.
  _(Verificación integral; no añade requirements nuevos)_
