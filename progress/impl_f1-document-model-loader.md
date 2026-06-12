# Informe de implementación — f1-document-model-loader

**Fecha:** 2026-06-12
**Estado:** implementación completa, todos los tests en verde

---

## Archivos creados

| Archivo | Descripción |
|---------|-------------|
| `src/wowrag/models.py` | Modelo pydantic `Document` (T1) |
| `src/wowrag/ingest/base.py` | Interfaz `CorpusLoader` (Protocol) + jerarquía de excepciones (T2) |
| `src/wowrag/ingest/loader.py` | Implementación `JsonlCorpusLoader` (T3) |
| `tests/test_models.py` | 9 tests para `Document` (T5) |
| `tests/test_corpus_loader.py` | 21 tests para `JsonlCorpusLoader` y la interfaz (T6) |

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `src/wowrag/ingest/__init__.py` | Reemplazado placeholder con exports reales: `CorpusLoader`, `JsonlCorpusLoader`, `CorpusError`, `CorpusNotFoundError`, `MalformedCorpusError` (T4) |
| `specs/f1-document-model-loader/tasks.md` | Marcadas T1..T7 como `[x]` |
| `progress/current.md` | Actualizado con estado in_progress y bitácora |

---

## Mapeo requisitos ↔ tests

| Requisito | Test(s) que lo cubren |
|-----------|----------------------|
| **R1** — Document con campos text, source_url, title, section | `test_models.py::test_document_valid_all_fields`, `test_document_minimal_fields` |
| **R2** — text vacío/blank o campos obligatorios ausentes → ValidationError | `test_models.py::test_document_text_empty_raises_validation_error`, `test_document_text_whitespace_only_raises_validation_error`, `test_document_text_tab_only_raises_validation_error`, `test_document_missing_source_url_raises_validation_error`, `test_document_missing_title_raises_validation_error`, `test_document_missing_text_raises_validation_error` |
| **R3** — section opcional, default "" | `test_models.py::test_document_section_defaults_to_empty_string`, `test_document_section_explicit_empty_string`, `test_document_minimal_fields` |
| **R4** — CorpusLoader Protocol existe | `test_corpus_loader.py::test_jsonl_loader_satisfies_corpus_loader_protocol`, `test_corpus_loader_usable_via_interface` |
| **R5** — JsonlCorpusLoader como implementación concreta detrás de la interfaz | `test_corpus_loader.py::test_jsonl_loader_satisfies_corpus_loader_protocol`, `test_corpus_loader_usable_via_interface` |
| **R6** — Carga *.jsonl, un Document por línea, metadata correcta | `test_corpus_loader.py::test_load_single_file_single_document`, `test_load_multiple_records_in_single_file`, `test_load_multiple_files_sorted_order`, `test_load_metadata_preserved` |
| **R7** — Ruta inexistente o no-directorio → CorpusNotFoundError con ruta | `test_corpus_loader.py::test_load_nonexistent_path_raises_corpus_not_found_error`, `test_load_file_path_raises_corpus_not_found_error`, `test_corpus_not_found_error_is_corpus_error` |
| **R8** — JSON inválido o Document inválido → MalformedCorpusError con fichero y nº línea | `test_corpus_loader.py::test_load_invalid_json_line_raises_malformed_corpus_error`, `test_load_invalid_json_line_message_contains_filename`, `test_load_line_missing_text_field_raises_malformed_corpus_error`, `test_load_line_with_empty_text_raises_malformed_corpus_error`, `test_malformed_corpus_error_is_corpus_error`, `test_malformed_error_reports_correct_line_number` |
| **R9** — Directorio sin *.jsonl → [] sin excepción | `test_corpus_loader.py::test_load_empty_directory_returns_empty_list`, `test_load_directory_with_no_jsonl_files_returns_empty_list` |
| **R10** — Líneas en blanco ignoradas | `test_corpus_loader.py::test_load_blank_lines_are_ignored`, `test_load_file_all_blank_lines_returns_empty_list` |
| **R11** — Sin peticiones de red ni servicios externos | `test_corpus_loader.py::test_loader_uses_no_network_fixtures` (implícito: todos los tests pasan offline) |

---

## Resultado de pytest

```
56 passed in 0.18s
```

- 26 tests preexistentes de f0: VERDE
- 9 tests nuevos en `test_models.py` (f1): VERDE
- 21 tests nuevos en `test_corpus_loader.py` (f1): VERDE
- `./init.sh` exit 0

---

## Desviaciones del spec

### Corrección menor en `loader.py` (no es desviación del spec)

El mensaje de `CorpusNotFoundError` en el diseño usaba `{root!r}` (repr de Path),
que en Windows produce `WindowsPath('C:/...')` con barras `/`, mientras que
`str(path)` en Windows produce barras `\`. El test R7 compara `str(missing)` con
el mensaje de error.

Se usó `{root}` (str de Path) en lugar de `{root!r}` para que el mensaje
contenga exactamente los mismos separadores que `str(missing)` en Windows.
El spec no especifica el formato exacto del mensaje, solo que "identifique la
ruta"; el mensaje final identifica la ruta correctamente en todas las plataformas.

### Resto

Ninguna. La implementación sigue el diseño del spec punto por punto:
- `Document` con `field_validator` exactamente como en design.md §2.
- `CorpusLoader` Protocol con `load(corpus_dir: str | Path) -> list[Document]` (design §3).
- `JsonlCorpusLoader` con la lógica de design §4 (sorted glob, líneas vacías ignoradas, excepciones encadenadas).
- Exports en `ingest/__init__.py` exactamente como design §5.
