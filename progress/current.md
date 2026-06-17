# Sesión actual

- **Feature en curso:** ninguna — `f8-rag-orchestrator` cerrada `done` esta
  sesión. No hay feature en `in_progress`.
- **Última actualización:** 2026-06-17
- **Agente:** leader

Pipeline RAG completo a nivel librería: f0–f8 todas `done`. Suite total:
`./init.sh` exit 0, **187 passed + 3 skipped** (integración pgvector + bge_m3 +
real-Ollama, todos `@pytest.mark.integration`).

## Bitácora

- **f7 cerrada:** change-round R19 resuelto (test network-free con
  `monkeypatch` de `httpx`), `reviewer` APROBADO, `implementer` flipó `done`.
- **f6:** bookkeeping completado (entrada añadida a `history.md`).
- **f8 cerrada:** humano aprobó el spec ("aprobado") → leader flipó
  `in_progress` → `implementer` (Answer/AnswerMetadata en `models.py`;
  `RagOrchestrator`/`DefaultRagOrchestrator` en `rag/`; DI de f5+f6+f7;
  abstención por short-circuit de `below_threshold`, mensaje propio, nunca
  lanza) → `reviewer` APROBADO (sin rondas) → `implementer` flipó `done`.
  21 tests nuevos (166 → 187).

## Próximo paso — decisión del humano

Features dependency-ready (ambas `pending`, dependen de f8 ✅):

- **`f9-http-api`** — POST `/ask` → `{answer, sources, abstained, metadata}`,
  health endpoint, CORS para el futuro frontend, persona por request o config.
  Expone el `DefaultRagOrchestrator` de f8 vía FastAPI. Aquí probablemente
  entra el async/streaming diferido desde f7/f8.
- **`f10-evaluation-harness`** — dataset golden Q&A; métricas de hit-rate,
  faithfulness/groundedness, y abstención correcta en preguntas fuera de
  corpus; ejecutable como script/reporte.

`f11-wowhead-ingestion` y `f12-reranking` siguen diferidas `[LATER]`.

Regla `one_feature_at_a_time: true` → una sola feature a la vez. Al elegir, el
leader lanza spec-author (vía `general-purpose`) → `spec_ready` → ⏸ puerta de
aprobación humana.

## Riesgos / notas

- **Trabajo sin commitear (creciente):** el working tree acumula f5 + f6 + f7 +
  f8 (código, tests, specs, reports) sin commit; el último commit es f4
  (`7fe3e91`). Decidir si se commitea antes de seguir.
- Tests de integración reales (pgvector + bge_m3 + Ollama) siguen skipped:
  requieren Postgres+pgvector, FlagEmbedding/GPU y un Ollama vivo
  (`requirements-pg.txt` / `requirements-ml.txt` / `requirements-llm.txt`,
  `pytest -m integration`).
