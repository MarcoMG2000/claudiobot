# Sesión actual

- **Feature en curso:** ninguna — `f9-http-api` cerrada `done` esta sesión.
  No hay feature en `in_progress`.
- **Última actualización:** 2026-06-17
- **Agente:** leader

Servicio RAG API-first completo end-to-end: **f0–f9 todas `done`**. Suite
total: `./init.sh` exit 0, **210 passed + 2 skipped + 5 deselected**.
- 2 skipped: ficheros de integración pgvector + bge_m3.
- 5 deselected: tests `@integration` de `test_llm_ollama.py` (colectables al
  estar `httpx` instalado, excluidos por `-m "not integration"`; no tocan un
  Ollama vivo).

## Bitácora

- **f7** cerrada (change-round R19 resuelto), **f6** bookkeeping completado,
  **f8** cerrada (orquestador + abstención). Backlog **f5–f8 commiteado** en
  `4559ada`.
- **f9-http-api cerrada:** humano aprobó ("aprobado f9") → leader flipó
  `in_progress` → `implementer` (FastAPI `src/wowrag/api/`: `/ask` + `/health`,
  CORS configurable, DI con `dependency_overrides` para `TestClient`, errores
  422/400/503; `fastapi`/`uvicorn`/`httpx` pineados a `requirements.txt` y
  movidos a `PINNED` en `test_requirements_pinned.py`) → `reviewer` APROBADO
  (sin rondas) → `implementer` flipó `done`. 23 tests nuevos (187 → 210).

## Próximo paso — decisión del humano

Feature dependency-ready (`pending`, depende de f8 ✅):

- **`f10-evaluation-harness`** — dataset golden Q&A; métricas de retrieval
  hit-rate, faithfulness/groundedness, y abstención correcta en preguntas
  fuera de corpus; ejecutable como script/reporte.

`f11-wowhead-ingestion` y `f12-reranking` siguen diferidas `[LATER]` (f11 =
scraper real de wowhead; f12 = reranker cross-encoder).

Regla `one_feature_at_a_time: true`. Al elegir, el leader lanza spec-author
(vía `general-purpose`) → `spec_ready` → ⏸ puerta de aprobación humana.

## Riesgos / notas

- Tests de integración reales (pgvector + bge_m3 + Ollama) siguen sin
  ejecutarse: requieren Postgres+pgvector, FlagEmbedding/GPU y un Ollama vivo
  (`requirements-pg.txt` / `requirements-ml.txt`, `pytest -m integration`).
  Hasta f11 no hay corpus real de wowhead → el path online end-to-end solo se
  ha validado con fakes.
- f10 cierra el bucle de calidad (mide faithfulness/abstención del servicio f8
  ya expuesto por f9).
