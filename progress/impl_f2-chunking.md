# Implementation Report — f2-chunking

## Feature

`f2-chunking` — Chunking pipeline (Document → Chunk with sliding-window overlap).

## Status

Tests: GREEN — 71 passed (56 pre-existing f0+f1 + 15 new f2), 0 failed.

## Files Modified

| File | Action |
|------|--------|
| `src/wowrag/models.py` | EDITED — added `Chunk` pydantic model after `Document` |
| `src/wowrag/config.py` | EDITED — added `chunk_size: int = 512` and `chunk_overlap: int = 64` to `Settings` |
| `src/wowrag/ingest/chunking.py` | CREATED — `ChunkingError`, `Chunker` Protocol, `OverlapChunker` |
| `src/wowrag/ingest/__init__.py` | EDITED — re-exported `Chunker`, `ChunkingError`, `OverlapChunker`; updated `__all__` |
| `tests/test_models.py` | EDITED — added 4 Chunk tests (T5) |
| `tests/test_chunking.py` | CREATED — 11 tests covering R4–R13 (T6) |
| `specs/f2-chunking/tasks.md` | EDITED — all checkboxes marked [x] |

## Requirements → Test Map

| Req | Test(s) |
|-----|---------|
| R1 (Chunk fields) | `tests/test_models.py::test_chunk_valid` |
| R2 (text validation) | `tests/test_models.py::test_chunk_empty_text`, `test_chunk_blank_text` |
| R3 (BaseModel / JSON) | `tests/test_models.py::test_chunk_json_roundtrip` |
| R4 (Chunker Protocol) | `tests/test_chunking.py::test_chunker_protocol_compatible` |
| R5 (OverlapChunker sliding window) | `tests/test_chunking.py::test_overlap_produces_multiple_chunks` |
| R6 (metadata preserved) | `tests/test_chunking.py::test_metadata_preserved` |
| R7 (chunk_id deterministic) | `tests/test_chunking.py::test_chunk_id_stable`, `test_chunk_id_differs_across_documents` |
| R8 (same doc → same ids) | `tests/test_chunking.py::test_chunk_id_stable` |
| R9 (Settings.chunk_size) | `tests/test_chunking.py::test_settings_chunk_params` |
| R10 (Settings.chunk_overlap) | `tests/test_chunking.py::test_settings_chunk_params` |
| R11 (overlap >= size raises) | `tests/test_chunking.py::test_invalid_overlap_equal_raises`, `test_invalid_overlap_greater_raises` |
| R12 (short text → 1 chunk) | `tests/test_chunking.py::test_short_text_single_chunk`, `test_text_equal_to_chunk_size` |
| R13 (full coverage) | `tests/test_chunking.py::test_full_coverage`, `test_overlap_produces_multiple_chunks`, `test_text_equal_to_chunk_size` |

## Deviations from spec

### Algorithm fix — `OverlapChunker.chunk()` (minor, within spec intent)

The design's pseudocode used `range(0, max(1, len(text)), step)` to generate start positions. For text of length exactly equal to `chunk_size`, this produced 2 positions (e.g., text=512, size=512, step=448 → positions [0, 448]), which contradicted tasks.md T6 and design §7 ("text exactly equal to chunk_size → 1 chunk").

The implementation replaces the list-of-positions loop with a `while True` loop that breaks as soon as `start + chunk_size >= len(text)`. This:
- Satisfies R12 for both `text_len < chunk_size` and `text_len == chunk_size`.
- Does NOT change behavior for `text_len > chunk_size` (all multi-chunk cases tested and passing).
- Is consistent with design §5's intent: "Garantizar que un texto más corto que chunk_size produce exactamente 1 chunk con todo el texto" — by extension, equal length also produces 1 chunk since no additional material exists beyond the first window.

No new requirements were introduced. The fix is purely algorithmic within the bounds of the approved spec.

## pytest output

```
71 passed in 1.47s
```
