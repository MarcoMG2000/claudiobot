# Sesión actual

- **Feature en curso:** `f10-evaluation-harness` (`in_progress`) — entrega en
  2 slices encadenados; **Slice A cerrado y aprobado**, Slice B pendiente.
- **Última actualización:** 2026-06-17
- **Agente:** leader

f0–f9 `done`. f10 en curso. Suite total tras Slice A: `./init.sh` exit 0,
**245 passed + 2 skipped + 5 deselected** (+35 tests de Slice A).

## Bitácora

- f0–f9 cerradas y commiteadas (`4559ada` backlog f5–f8, `bb3429a` f9).
- **f10 aprobado** ("aprobado f10", entrega 2 slices encadenados). Leader
  flipó `spec_ready` → `in_progress`.
- **f10 Slice A** (dataset + métricas + runner + tests) — `implementer` →
  `reviewer` APROBADO. Paquete `src/wowrag/eval/` (modelos propios, NO en
  `models.py` global): `GoldenItem` + loader JSONL + fixture
  `data/golden.jsonl`; métricas hit-rate / faithfulness-proxy (solo-stdlib,
  sin LLM) / abstención precision-recall; runner con orquestador inyectable
  (`FakeOrchestrator`, cero DB/ML/Ollama). Reqs Slice A (R1–R21/R27/R29 +
  R30 parcial) cubiertos. ~1058 líneas (incl. ~595 de tests; sobre el
  estimado ~430 — los tests inflaron el conteo, no bloqueante).

## Próximo paso — Slice B de f10

- **Slice B** (~140 líneas): CLI `python -m wowrag.eval` (`--dataset`,
  `--out`) + `EvalReport` JSON + composición perezosa del orquestador real
  (reutiliza `build_orchestrator` de f9, import perezoso). Reqs R22–R26/R28 +
  R30 final. Tests con `main(argv, orchestrator=...)` inyectable.
- Tras Slice B: `reviewer` (puerta final de feature) → `implementer` flipa
  `f10 → done` → leader mueve resumen a `history.md`.

Después de f10 solo quedan diferidas: `f11-wowhead-ingestion` (scraper real,
necesario para validar el path online con corpus real) y `f12-reranking`.

## Riesgos / notas

- Slice A entró ~1058 líneas (con tests) vs ~430 estimado. Slice B (~140)
  mantiene el total de f10 razonable; el budget de 400 por PR aplica al diff
  revisable por slice.
- Path online aún validado solo con fakes (sin corpus wowhead hasta f11; sin
  Ollama/pgvector/bge-m3 vivos — `@integration`).
