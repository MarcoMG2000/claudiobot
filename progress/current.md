# Sesión actual

- **Feature en curso:** `f0-project-skeleton` (fase: spec)
- **Inicio:** 2026-06-03
- **Agente:** leader

## Plan

Arranque del proyecto wow-classic-rag (RAG autoalojado sobre wowhead).
Decisiones de stack tomadas con el humano:
- LLM: solo local (Ollama, `qwen2.5:7b-instruct`).
- Vector store: PostgreSQL + pgvector.
- Idioma: multilingüe (embeddings `bge-m3`).
- Hardware: GPU disponible.

Fundamentos del arnés ya escritos por el leader (fuera de src/tests):
`feature-list.json` (roadmap F0–F12), `docs/{architecture,conventions,specs,verification}.md`,
`CHECKPOINTS.md` re-orientado, `init.sh` creado y verde (exit 0).

## Bitácora

- Repo encontrado como template SDD vacío (era "portfolio"); reconfigurado al proyecto.
- Regla stdlib-only del template eliminada: este proyecto usa deps pineadas.
- `init.sh` ejecutado: exit 0. Python del sistema = 3.14.4.

## Próximo paso

Lanzar `spec_author` para `f0-project-skeleton` → quedará en `spec_ready` →
**pausa para aprobación humana**.

## Riesgos anotados

- Python 3.14: posibles wheels ausentes para torch/sentence-transformers en
  features f3/f4; pinear Python compatible cuando llegue ese momento.
