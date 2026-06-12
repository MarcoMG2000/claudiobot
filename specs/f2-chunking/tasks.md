# Tasks — f2-chunking

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests usan datos en memoria o `tmp_path`; sin Postgres, Ollama ni
> red. La trazabilidad `R<n>` ↔ test es obligatoria (`docs/verification.md`);
> nombra o comenta cada test con su `R<n>`. NO marques la feature `done` ni
> edites `feature-list.json` (eso es del leader/reviewer).

## Implementación

- [x] **T1 — Modelo `Chunk` en `models.py`.** Añadir la clase `Chunk`
  (pydantic `BaseModel`) a `src/wowrag/models.py` después de `Document`, con
  los campos `chunk_id`, `text`, `source_url`, `title`, `section` (todos str,
  todos obligatorios) y un `field_validator` que rechace `text` vacío o solo
  espacios. Seguir el mismo patrón que `Document`.
  _(Cubre R1, R2, R3)_

- [x] **T2 — Parámetros de chunking en `Settings`.** Añadir `chunk_size: int =
  512` y `chunk_overlap: int = 64` a la clase `Settings` en
  `src/wowrag/config.py`. Nada más; la validación de la relación
  `overlap < size` vive en el constructor de `OverlapChunker`, no aquí.
  _(Cubre R9, R10)_

- [x] **T3 — Interfaz `Chunker`, excepción y `OverlapChunker`.** Crear
  `src/wowrag/ingest/chunking.py` con:
  - `ChunkingError(Exception)`.
  - `Chunker` Protocol con método `chunk(document: Document) -> list[Chunk]`.
  - `OverlapChunker.__init__(chunk_size, chunk_overlap)` que lanza
    `ChunkingError` si `chunk_overlap >= chunk_size`.
  - `OverlapChunker.chunk(document)` que divide el texto con ventana deslizante
    (`step = chunk_size - chunk_overlap`), copia `source_url`, `title`,
    `section` a cada `Chunk`, y asigna un `chunk_id` determinista via
    `sha256(f"{source_url}|{section}|{index}".encode())[:16]`.
  - Garantizar que un texto más corto que `chunk_size` produce exactamente 1
    chunk con todo el texto.
  _(Cubre R4, R5, R6, R7, R8, R11, R12, R13)_

- [x] **T4 — Re-exportar desde `ingest/__init__.py`.** Editar
  `src/wowrag/ingest/__init__.py` para importar y re-exportar `Chunker`,
  `ChunkingError`, `OverlapChunker` del nuevo módulo `chunking.py`. Actualizar
  `__all__`.
  _(Cubre R4, R5)_

## Tests

- [x] **T5 — Extender `tests/test_models.py` con casos de `Chunk`.**
  Añadir (sin borrar los tests existentes de `Document`):
  - `test_chunk_valid`: `Chunk(chunk_id=..., text=..., source_url=..., title=...,
    section=...)` se construye y conserva todos los campos. _(R1)_
  - `test_chunk_empty_text`: `Chunk(text="")` → `ValidationError` mencionando
    `text`. _(R2)_
  - `test_chunk_blank_text`: `Chunk(text="   ")` → `ValidationError`. _(R2)_
  - `test_chunk_json_roundtrip`: `Chunk.model_dump()` / `Chunk.model_validate()`
    produce el mismo objeto. _(R3)_

- [x] **T6 — Crear `tests/test_chunking.py`.** Un fichero de test por módulo.
  Casos mínimos (citar el `R<n>` en cada test o en su docstring):
  - `test_invalid_overlap_raises`: `OverlapChunker(size=100, overlap=100)` →
    `ChunkingError`. `OverlapChunker(size=100, overlap=110)` → `ChunkingError`.
    _(R11)_
  - `test_short_text_single_chunk`: texto de 10 chars, `chunk_size=512` →
    exactamente 1 chunk con todo el texto. _(R12)_
  - `test_text_equal_to_chunk_size`: texto de exactamente 512 chars,
    `chunk_size=512` → 1 chunk. _(R12, R13)_
  - `test_overlap_produces_multiple_chunks`: texto de 200 chars, `chunk_size=100`,
    `overlap=20` → 3 chunks; el segundo empieza en `char[80]`; el tercero en
    `char[160]`. _(R5, R13)_
  - `test_full_coverage`: verificar que la unión de todos los fragmentos de
    chunk cubre el texto original (sin huecos), es decir, que el texto se puede
    reconstruir sin fragmentos faltantes. _(R13)_
  - `test_metadata_preserved`: cada chunk resultante tiene `source_url`, `title`,
    `section` iguales a los del documento origen. _(R6)_
  - `test_chunk_id_stable`: procesar el mismo `Document` dos veces → los
    `chunk_id` son idénticos. _(R7, R8)_
  - `test_chunk_id_differs_across_documents`: dos `Document` con distinto
    `source_url` → distintos `chunk_id` para el chunk de índice 0. _(R7)_
  - `test_chunker_protocol_compatible`: `OverlapChunker` es usable como
    `Chunker` (asignación de tipo y llamada al método sin error). _(R4)_
  - `test_settings_chunk_params`: `Settings()` expone `chunk_size` y
    `chunk_overlap` como enteros; sus valores pueden pasarse al constructor de
    `OverlapChunker` sin error. _(R9, R10)_

## Cierre

- [x] **T7 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con
  la suite (no-integration) en verde. Debe incluir los 56 tests previos más
  todos los nuevos tests de f2 (T5 + T6). Sin `print()` de debug, sin TODOs
  sin contexto. Comprobar que todos los `R<n>` de `requirements.md` tienen al
  menos un test en `test_models.py` o `test_chunking.py`.
  _(Verificación integral; no añade requirements nuevos)_
