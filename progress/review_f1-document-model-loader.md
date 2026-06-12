# Review — feature f1-document-model-loader

**Veredicto:** APPROVED

---

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `test_models.py::test_document_valid_all_fields`, `test_document_minimal_fields`
- R2: [x] cubierto por `test_models.py::test_document_text_empty_raises_validation_error`, `test_document_text_whitespace_only_raises_validation_error`, `test_document_text_tab_only_raises_validation_error`, `test_document_missing_source_url_raises_validation_error`, `test_document_missing_title_raises_validation_error`, `test_document_missing_text_raises_validation_error`
- R3: [x] cubierto por `test_models.py::test_document_section_defaults_to_empty_string`, `test_document_section_explicit_empty_string`, `test_document_minimal_fields`
- R4: [x] cubierto por `test_corpus_loader.py::test_jsonl_loader_satisfies_corpus_loader_protocol`, `test_corpus_loader_usable_via_interface`
- R5: [x] cubierto por `test_corpus_loader.py::test_jsonl_loader_satisfies_corpus_loader_protocol`, `test_corpus_loader_usable_via_interface`
- R6: [x] cubierto por `test_corpus_loader.py::test_load_single_file_single_document`, `test_load_multiple_records_in_single_file`, `test_load_multiple_files_sorted_order`, `test_load_metadata_preserved`
- R7: [x] cubierto por `test_corpus_loader.py::test_load_nonexistent_path_raises_corpus_not_found_error`, `test_load_file_path_raises_corpus_not_found_error`, `test_corpus_not_found_error_is_corpus_error`
- R8: [x] cubierto por `test_corpus_loader.py::test_load_invalid_json_line_raises_malformed_corpus_error`, `test_load_invalid_json_line_message_contains_filename`, `test_load_line_missing_text_field_raises_malformed_corpus_error`, `test_load_line_with_empty_text_raises_malformed_corpus_error`, `test_malformed_corpus_error_is_corpus_error`, `test_malformed_error_reports_correct_line_number`
- R9: [x] cubierto por `test_corpus_loader.py::test_load_empty_directory_returns_empty_list`, `test_load_directory_with_no_jsonl_files_returns_empty_list`
- R10: [x] cubierto por `test_corpus_loader.py::test_load_blank_lines_are_ignored`, `test_load_file_all_blank_lines_returns_empty_list`
- R11: [x] cubierto por `test_corpus_loader.py::test_loader_uses_no_network_fixtures` (implícito: todos los tests ejecutan offline sin fixtures de red)

Todos los R1..R11 tienen cobertura de test. Cada test lleva su `# R<n>` en comentario inline — trazabilidad completa.

---

## Tasks completas

- T1: [x] `src/wowrag/models.py` creado con `Document` pydantic + `field_validator` para `text`.
- T2: [x] `src/wowrag/ingest/base.py` creado con Protocol `CorpusLoader` + jerarquía `CorpusError / CorpusNotFoundError / MalformedCorpusError`.
- T3: [x] `src/wowrag/ingest/loader.py` creado con `JsonlCorpusLoader.load()` completo: glob ordenado, skip de blancos, excepciones encadenadas con fichero + nº línea.
- T4: [x] `src/wowrag/ingest/__init__.py` reemplazado con exports reales: `CorpusLoader`, `JsonlCorpusLoader`, `CorpusError`, `CorpusNotFoundError`, `MalformedCorpusError`.
- T5: [x] `tests/test_models.py` con 9 tests cubriendo R1, R2, R3.
- T6: [x] `tests/test_corpus_loader.py` con 21 tests cubriendo R4..R11.
- T7: [x] `./init.sh` ejecutado — exit 0, 56 passed in 0.18s.

---

## Checkpoints

- C1: [x] Archivos base del arnés presentes (`AGENTS.md`, `init.sh`, `feature-list.json`, `progress/current.md`). Los 4 docs en `docs/`. `./init.sh` termina con exit 0.
- C2: [x] Exactamente una feature `in_progress` en `feature-list.json` (f1-document-model-loader). `progress/current.md` describe la sesión activa.
- C3: [x] `src/wowrag/` respeta la separación por capas: `models.py` en la raíz del paquete (capa de datos), `ingest/` con `base.py` (interfaz) + `loader.py` (implementación). Sin SQL, HTTP ni red fuera de su capa. Sin `print()` de debug. Sin secretos en el repo.
- C4: [x] Un fichero de test por módulo: `test_models.py` para `models.py`, `test_corpus_loader.py` para `ingest/`. Todos los tests usan `tmp_path` — sin Postgres, Ollama ni red. `pytest -m "not integration"` pasa 56 tests en verde.
- C5: [ ] No aplicable a f1. La abstención, citas y grounding son responsabilidad de features posteriores (f8-rag-orchestrator). f1 solo establece el modelo `Document` y el loader.
- C6: [x] `specs/f1-document-model-loader/` tiene `requirements.md`, `design.md`, `tasks.md`. `requirements.md` usa EARS estricto. Todas las tasks T1..T7 marcadas `[x]`. Cada R1..R11 cubierto por al menos un test.

Nota sobre C5: los checkpoints de grounding/abstención/citas de `CHECKPOINTS.md` §C5 son del sistema completo y no son requisitos de f1. Se deja como `[ ]` porque f1 no los puede ni debe satisfacer; no es motivo de rechazo.

---

## Conformidad con design.md

Verificado punto por punto:

1. **`src/wowrag/models.py`** — `Document(BaseModel)` con `text`, `source_url`, `title` obligatorios y `section: str = ""`. `field_validator("text")` rechaza blancos. Idéntico al diseño §2. Sin desviaciones.

2. **`src/wowrag/ingest/base.py`** — `CorpusLoader(Protocol)` con `load(corpus_dir: str | Path) -> list[Document]`. Jerarquía `CorpusError → CorpusNotFoundError / MalformedCorpusError`. Exactamente como diseño §3.

3. **`src/wowrag/ingest/loader.py`** — `JsonlCorpusLoader.load()` hace: `sorted(root.glob("*.jsonl"))`, skip de líneas vacías, `json.loads` + `Document(**obj)`, dos `except` separados (`json.JSONDecodeError` y `ValidationError|TypeError`) con `raise ... from exc`. La única desviación documentada es usar `{root}` en lugar de `{root!r}` en el mensaje de `CorpusNotFoundError` para compatibilidad con separadores Windows — el spec no prescribe el formato exacto del mensaje, solo que "identifique la ruta", lo cual se cumple.

4. **`src/wowrag/ingest/__init__.py`** — Exports exactamente como diseño §5.

5. **Sin scope creep** — No se crearon módulos, clases ni funciones fuera del alcance de f1. No hay chunking, embeddings, store, retrieval ni generación.

---

## Conformidad con docs/conventions.md

- Type hints obligatorios: presentes en todas las funciones públicas.
- `logging` estándar con `logger = logging.getLogger(__name__)` en `loader.py`. Sin `print()`.
- Docstrings breves en módulos y funciones públicas. Comentarios solo donde no es obvio (comentario `# R10` inline en `loader.py` línea 68).
- Nombres: `snake_case` en módulos/funciones, `PascalCase` en clases. Interfaces describen capacidad (`CorpusLoader`), implementación nombra la tecnología (`JsonlCorpusLoader`).
- `CorpusLoader` en `ingest/base.py` (interfaz en `base.py` del paquete), implementación en `loader.py` aparte — patrón de abstracción cumplido.
- Tests con `tmp_path` — sin escribir en el repo, sin servicios reales.

---

## Resultado de ./init.sh

```
==> wow-classic-rag :: init
==> Python: Python 3.14.4
==> Instalando dependencias
==> Ejecutando pytest (no integration)
56 passed in 0.18s
==> init OK
```

Exit code: 0. Todos los tests verdes.
