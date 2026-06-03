# Sesión actual

- **Feature en curso:** `f1-document-model-loader` (fase: `spec_ready` — esperando aprobación humana)
- **Inicio:** 2026-06-03
- **Agente:** leader → spec-author

F0 cerrada como `done` (26 tests, init.sh exit 0, reviewer APROBADO). F0 desbloquea F1 y F7; por orden del roadmap se eligió F1.

## Plan

Spec de `f1-document-model-loader` redactado (Kiro-style). Pendiente de aprobación humana antes de pasar a `in_progress` e implementación.

Decisiones de diseño del spec:
- Corpus en **JSONL** (un `Document` por línea). Descartados Markdown+frontmatter y JSON-array único.
- Modelo **`Document` pydantic** en `src/wowrag/models.py` (campo `text` + metadata `source_url`, `title`, `section`).
- `JsonlCorpusLoader` detrás de la interfaz swappable `CorpusLoader` (Protocol) en `src/wowrag/ingest/`.
- Scraping real de wowhead fuera de alcance (diferido a f11).
- 11 requisitos (R1..R11), 7 tasks (T1..T7; T5–T6 tests, T7 verificación).

## Bitácora

- F0 completada y cerrada esta sesión (implementer + reviewer).
- `spec-author` no estaba registrado como subagent_type en el harness; se delegó la redacción del spec a un agente `general-purpose` con el rol de `.claude/agents/spec-author.md` (no toca src/ ni tests/).

## Próximo paso

⏸ **PUERTA DE APROBACIÓN HUMANA.** El humano revisa `specs/f1-document-model-loader/{requirements,design,tasks}.md` y aprueba o pide cambios. Tras aprobación: leader cambia F1 a `in_progress` y lanza implementer.

## Riesgos anotados

- Python 3.14: posibles wheels ausentes para torch/sentence-transformers en
  features f3/f4; pinear Python compatible cuando llegue ese momento.
