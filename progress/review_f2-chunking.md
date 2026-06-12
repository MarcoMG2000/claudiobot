# Review — feature f2-chunking

**Veredicto:** APPROVED

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `tests/test_models.py::test_chunk_valid`
- R2: [x] cubierto por `tests/test_models.py::test_chunk_empty_text`, `test_chunk_blank_text`
- R3: [x] cubierto por `tests/test_models.py::test_chunk_json_roundtrip`
- R4: [x] cubierto por `tests/test_chunking.py::test_chunker_protocol_compatible`
- R5: [x] cubierto por `tests/test_chunking.py::test_overlap_produces_multiple_chunks`
- R6: [x] cubierto por `tests/test_chunking.py::test_metadata_preserved`
- R7: [x] cubierto por `tests/test_chunking.py::test_chunk_id_stable`, `test_chunk_id_differs_across_documents`
- R8: [x] cubierto por `tests/test_chunking.py::test_chunk_id_stable`
- R9: [x] cubierto por `tests/test_chunking.py::test_settings_chunk_params`
- R10: [x] cubierto por `tests/test_chunking.py::test_settings_chunk_params`
- R11: [x] cubierto por `tests/test_chunking.py::test_invalid_overlap_equal_raises`, `test_invalid_overlap_greater_raises`
- R12: [x] cubierto por `tests/test_chunking.py::test_short_text_single_chunk`, `test_text_equal_to_chunk_size`
- R13: [x] cubierto por `tests/test_chunking.py::test_full_coverage`, `test_overlap_produces_multiple_chunks`, `test_text_equal_to_chunk_size`

Todos los R1–R13 tienen cobertura de test con referencia explícita al R# correspondiente.

## Tasks completas

- T1: [x] `Chunk` pydantic BaseModel con `field_validator` añadido en `src/wowrag/models.py`
- T2: [x] `chunk_size: int = 512` y `chunk_overlap: int = 64` añadidos a `Settings` en `src/wowrag/config.py`
- T3: [x] `src/wowrag/ingest/chunking.py` creado con `ChunkingError`, `Chunker` Protocol, `OverlapChunker` (incluyendo validación `overlap >= size`, derivación de `chunk_id` vía sha256, y lógica de ventana deslizante)
- T4: [x] `src/wowrag/ingest/__init__.py` actualizado — importa y re-exporta `Chunker`, `ChunkingError`, `OverlapChunker`; `__all__` actualizado
- T5: [x] `tests/test_models.py` extendido con `test_chunk_valid`, `test_chunk_empty_text`, `test_chunk_blank_text`, `test_chunk_json_roundtrip` (4 casos, tests previos de Document intactos)
- T6: [x] `tests/test_chunking.py` creado con 11 tests cubriendo R4–R13 (todos los casos mínimos de tasks.md y un caso extra `test_text_equal_to_chunk_size`)
- T7: [x] `./init.sh` termina con exit 0 — 71 passed (56 previos f0/f1 + 15 nuevos f2)

## Checkpoints

- C1: [x] Archivos base y docs existentes; `./init.sh` termina verde (exit 0)
- C2: [x] Exactamente una feature `in_progress` (`f2-chunking`); features `done` (f0, f1) con tests que pasan; `progress/current.md` presente
- C3: [x] `src/wowrag/` respeta separación por capas (chunker en `ingest/chunking.py` según `docs/architecture.md` §6); `Chunker` es Protocol (swap point); `requirements.txt` con versiones pineadas; sin `print()` de debug ni secretos
- C4: [x] Test por módulo nuevo (`test_chunking.py` para `ingest/chunking.py`); lógica testada en memoria sin servicios reales; `pytest -m "not integration"` → 71 tests verdes
- C5: [ ] No aplica a esta feature (abstención/grounding pertenece a f8-rag-orchestrator)
- C6: [x] `specs/f2-chunking/` contiene `requirements.md`, `design.md`, `tasks.md`; requisitos en EARS estricto; todas las tasks `[x]`; cada R1–R13 cubierto por al menos un test

## Notas de conformidad con design.md

- `Chunk` en `models.py`: conforme. Campos obligatorios `chunk_id`, `text`, `source_url`, `title`, `section`; `field_validator("text")` presente; `BaseModel` heredado.
- `Chunker` Protocol en `ingest/chunking.py`: conforme. Método `chunk(document: Document) -> list[Chunk]`.
- `ChunkingError`: conforme. Lanzado en `OverlapChunker.__init__` cuando `chunk_overlap >= chunk_size`.
- `chunk_id` determinista: conforme. `sha256(f"{source_url}|{section}|{index}".encode()).hexdigest()[:16]` — coincide exactamente con design §4 y §5.
- `Settings.chunk_size` / `Settings.chunk_overlap`: conforme. Defaults 512/64 sin valores mágicos en el código de producción.
- Re-exportación desde `ingest/__init__.py`: conforme. `__all__` actualizado.

## Desviación documentada (aceptada)

El implementer substituyó el bucle `range(0, max(1, len(text)), step)` del pseudocódigo de design §5 por un `while True` con break cuando `start + chunk_size >= len(text)`. La desviación está justificada en `progress/impl_f2-chunking.md`: el pseudocódigo producía 2 posiciones para texto de longitud exactamente igual a `chunk_size` (ej. texto=512, size=512, step=448 → [0, 448]), violando R12 y tasks T6. La implementación alternativa satisface R12 en ambos casos (`<` y `==`) sin alterar el comportamiento para textos más largos, como verifican los tests.

## Scope creep

Ninguno. Los archivos modificados son exactamente los indicados en design §1. Los 56 tests previos (f0/f1) permanecen intactos y en verde. `feature_list.json` tiene `f2-chunking` en `in_progress` (no marcada `done`, correcto — esa acción corresponde al leader/reviewer).
