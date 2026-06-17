# Implementation Report — f6-prompt-builder

**Status:** done (all tasks [x], scoped tests green)
**Date:** 2026-06-16

---

## Tasks completed

- [x] T1 — `Source` + `BuiltPrompt` added to `src/wowrag/models.py`; `__all__` updated.
- [x] T2 — `src/wowrag/generation/prompt_builder_base.py` created with `PromptBuilderError` and `PromptBuilder` Protocol.
- [x] T3 — `src/wowrag/generation/prompt_builder.py` created with `DefaultPromptBuilder`.
- [x] T4 — `src/wowrag/generation/__init__.py` updated with re-exports.
- [x] T5 — `tests/test_models_prompt.py` created (4 tests).
- [x] T6 — `tests/test_prompt_builder.py` created (16 tests).
- [x] Z1 — Scoped verification passed; write-set isolation confirmed.

---

## Files created / edited

| Path | Action |
|------|--------|
| `src/wowrag/models.py` | EDITED — added `Source`, `BuiltPrompt`, updated `__all__` |
| `src/wowrag/generation/prompt_builder_base.py` | NEW — `PromptBuilderError`, `PromptBuilder` Protocol |
| `src/wowrag/generation/prompt_builder.py` | NEW — `DefaultPromptBuilder` |
| `src/wowrag/generation/__init__.py` | EDITED — replaced placeholder with real re-exports |
| `tests/test_models_prompt.py` | NEW — 4 model tests |
| `tests/test_prompt_builder.py` | NEW — 16 builder tests |

Files NOT touched (write-set isolation respected):
- `src/wowrag/config.py` — not modified
- `src/wowrag/generation/base.py` — not created (reserved for f7)
- `tests/test_config.py` — not touched
- `progress/current.md`, `feature-list.json` — not touched

---

## R<n> → test traceability

| Requirement | Test(s) |
|-------------|---------|
| R1 — `BuiltPrompt` has `system: str`, `user: str` | `test_builtprompt_fields` (test_models_prompt.py) |
| R2 — `BuiltPrompt.sources: list[Source]` with `n/title/url` | `test_source_fields`, `test_builtprompt_fields` |
| R3 — `BuiltPrompt.system` non-empty | `test_system_and_user_nonempty` |
| R4 — `BuiltPrompt.user` non-empty | `test_system_and_user_nonempty` |
| R5 — `sources[n].n` matches `[n]` markers | `test_sources_match_markers` |
| R6 — `PromptBuilder` Protocol with `build()` signature | `test_exports_from_package` (import validates Protocol exists) |
| R7 — No LLM/DB/GPU/net dependency | `test_builder_depends_only_on_models` |
| R8 — Empty/whitespace query raises `PromptBuilderError` | `test_empty_query_raises` |
| R9 — Literal query in `user` | `test_user_contains_query` |
| R10 — `persona=None` uses `Settings.default_persona` | `test_default_persona_from_config` |
| R11 — Explicit persona overrides config | `test_explicit_persona_overrides_config` |
| R12 — `system_style` injected; persona change changes text | `test_persona_style_injected` |
| R13 — Solo-context grounding instruction | `test_grounding_instructions_present`, `test_grounding_independent_of_persona` |
| R14 — Declare-insufficient-evidence instruction | `test_grounding_instructions_present`, `test_grounding_independent_of_persona` |
| R15 — Cite-with-[n] instruction | `test_grounding_instructions_present`, `test_grounding_independent_of_persona` |
| R16 — Grounding persona-independent | `test_grounding_independent_of_persona` |
| R17 — Sequential `[1]..[N]` markers in `user` | `test_context_has_sequential_citation_markers` |
| R18 — `chunk.text`, `source_url`, `title` in context | `test_context_includes_chunk_text_and_url` |
| R19 — One `Source(n, url)` per `[n]` marker | `test_sources_match_markers` |
| R20 — Context only from `result.chunks` | `test_context_only_from_result` |
| R21 — Empty context → valid prompt, `sources=[]`, no exception | `test_empty_context_builds_valid_prompt` |
| R22 — `len(sources)` == chunks formatted | `test_sources_match_markers`, `test_builtprompt_accepts_empty_sources` |
| R23 — Uses `Settings.default_persona`, no new config field | `test_default_persona_from_config` |
| R24 — `PersonaNotFoundError` propagates | `test_missing_persona_propagates` |
| R25 — `PromptBuilderError(Exception)` defined | `test_empty_query_raises` |
| R26 — `PersonaNotFoundError` not masked as `PromptBuilderError` | `test_missing_persona_propagates` |
| R27 — Re-exports from `generation/__init__` and `models.__all__` | `test_exports_from_package`, `test_models_exported` |

---

## Scoped pytest result

Command:
```
.venv/Scripts/python.exe -m pytest tests/test_prompt_builder.py tests/test_models_prompt.py -q
```

Result: **20 passed in 0.15s**

Breakdown:
- `tests/test_models_prompt.py`: 4 passed
- `tests/test_prompt_builder.py`: 16 passed

---

## Spec deviations

None. Implementation follows design.md exactly:
- `generation/base.py` was NOT created (reserved for f7 as specified).
- `config.py` was NOT modified.
- Persona YAML files were NOT redefined.
- `_GROUNDING_INSTRUCTIONS` is a module-level constant (persona-independent, R16).
- `PersonaNotFoundError` propagates unmasked in all paths (R24, R26).
