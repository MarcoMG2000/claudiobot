# Sesión actual

- **Feature en curso:** ninguna — `f10-evaluation-harness` cerrada `done`.
  Todas las features no-diferidas (`f0`–`f10`) están `done`.
- **Última actualización:** 2026-06-17
- **Agente:** leader

Sistema RAG completo (ingesta offline + servicio online + API HTTP + harness
de evaluación). Suite total: `./init.sh` exit 0, **256 passed + 2 skipped +
5 deselected**.
- 2 skipped: ficheros de integración pgvector + bge_m3.
- 5 deselected: tests `@integration` de Ollama (`test_llm_ollama.py`),
  excluidos por `-m "not integration"`.

## Bitácora

- f0–f9 cerradas y commiteadas (`4559ada` backlog f5–f8, `bb3429a` f9).
- **f10-evaluation-harness cerrada** en 2 slices encadenados:
  - Slice A (`53130c4`): dataset + métricas + runner.
  - Slice B (este commit): CLI `python -m wowrag.eval` + `EvalReport` JSON +
    composición perezosa del orquestador real.
  - Ambos `reviewer` APROBADO; `implementer` flipó `f10 → done`.

## Próximo paso — solo quedan features diferidas `[LATER]`

- **`f11-wowhead-ingestion`** (`pending`, depende de f1) — scraper real de
  wowhead → schema `Document`, respetando robots/rate-limits. **Desbloquea la
  validación end-to-end con corpus real** (hasta ahora el path online solo se
  ha probado con fakes).
- **`f12-reranking`** (`pending`, depende de f5) — reranker cross-encoder para
  mejorar el orden del top-k antes de generar.

Ambas marcadas `[LATER]` en el roadmap. Cuando el humano quiera arrancar una,
el leader lanza spec-author → `spec_ready` → ⏸ puerta de aprobación humana.

## Riesgos / notas

- El path online (retrieve→prompt→generate) y el harness de evaluación solo se
  han validado con **fakes**: no hay corpus real de wowhead (f11) ni
  Ollama/pgvector/bge-m3 vivos en CI (tests `@integration`). La primera
  ejecución real requerirá `requirements-pg.txt` + `requirements-ml.txt` +
  `requirements-llm.txt`, un Postgres+pgvector, FlagEmbedding/GPU y un Ollama
  vivo, más un corpus indexado.
