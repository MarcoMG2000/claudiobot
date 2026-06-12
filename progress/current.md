# Sesión actual

- **Feature en curso:** ninguna — `f2-chunking` cerrada como `done`
- **Última actualización:** 2026-06-12
- **Agente:** leader

F1 y F2 cerradas esta sesión (spec aprobado → implementer → reviewer APROBADO en ambas). Suite total: 71 tests verdes (26 f0 + 30 f1 + 15 f2), `./init.sh` exit 0.

## Bitácora

- F1 cerrada y commiteada (`e22b143`): `Document` pydantic + `JsonlCorpusLoader`. Informes en `progress/{impl,review}_f1-document-model-loader.md`.
- Humano aprobó spec de F2 (puerta de aprobación superada).
- Implementer F2: modelo `Chunk` en `src/wowrag/models.py`, `Chunker` Protocol + `OverlapChunker` + `ChunkingError` en `src/wowrag/ingest/chunking.py`, `chunk_size`/`chunk_overlap` en `Settings`. Informe en `progress/impl_f2-chunking.md`.
- Reviewer F2: trazabilidad R1..R13 ↔ tests OK, tasks T1..T7 completas, APROBADO. Informe en `progress/review_f2-chunking.md`.
- F2 marcada `done` en `feature-list.json`.

## Próximo paso

Siguiente feature por orden de roadmap: **`f3-embeddings-provider`** (status `pending`, depende de f2 ✅). Flujo: leader lanza spec-author → `spec_ready` → ⏸ aprobación humana → implementer → reviewer.

Alternativa desbloqueada: `f7-llm-provider-ollama` (depende solo de f0).

## Riesgos anotados

- Python 3.14: posibles wheels ausentes para torch/sentence-transformers en
  **f3** (sentence-transformers/FlagEmbedding) y f4; el spec de f3 debe
  abordar esto (pinear Python compatible o aislar la dependencia GPU detrás
  de la interfaz con fake provider para tests).
