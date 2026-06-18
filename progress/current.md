# Sesión actual

- **Feature en curso:** ninguna — `f11-wowhead-ingestion` cerrada `done`.
  Solo queda `f12-reranking` (`pending`, diferida `[LATER]`).
- **Última actualización:** 2026-06-18
- **Agente:** leader

f0–f11 `done`. Con f11 el sistema puede construir un corpus real de wowhead
(scraper respetuoso → JSONL → indexer f4 → retrieve → generate). Suite total:
`./init.sh` exit 0, **297 passed + 2 skipped + 6 deselected** (1 warning
preexistente de f9, third-party).
- 2 skipped: integración pgvector + bge_m3 (f3/f4).
- 6 deselected: 5 `@integration` de Ollama (f7) + 1 live-fetch de wowhead (f11).

## Bitácora

- f0–f10 cerradas y commiteadas (`4559ada`, `bb3429a`, `53130c4`, `060f7db`).
- **f11-wowhead-ingestion cerrada** en 2 slices encadenados:
  - Slice A (`016148a`): fetcher + robots + rate-limit.
  - Slice B (este commit): normalizer + pipeline + CLI; change-round que movió
    `selectolax` a `requirements.txt` (precedente f9) para cubrir la lógica
    core en CI. Ambos `reviewer` APROBADO; `implementer` flipó `f11 → done`.

## Próximo paso — solo queda `f12-reranking`

- **`f12-reranking`** (`pending`, `[LATER]`, depende de f5 ✅) — reranker
  cross-encoder que reordena el top-k del retriever antes de generar.
  Encaja entre f5 (retrieve) y f6/f8 (prompt/generate) como capa opcional
  swappable. Probablemente otra dep ML pesada (cross-encoder) aislada +
  `@integration`, con un fake para los tests unitarios.

Cuando el humano quiera, el leader lanza spec-author → `spec_ready` → ⏸ puerta
de aprobación humana.

## Riesgos / notas

- **Seguimiento menor (no bloqueante):** `src/wowrag/ingest/wowhead/fetcher.py:40`
  + `tests/test_wowhead_fetcher.py:121` aún citan `requirements-scrape.txt`
  (eliminado en el change-round) en el error-path de httpx-ausente — defensivo
  e inalcanzable. Alinear el hint con `requirements.txt` en una limpieza futura.
- Validación end-to-end REAL aún pendiente de ejecutarse: requiere
  `requirements-pg.txt` + `requirements-ml.txt` + `requirements-llm.txt`
  instalados, Postgres+pgvector, FlagEmbedding/GPU, Ollama vivo, y correr el
  scraper de f11 contra wowhead para generar el corpus. Todo el código está
  probado con fakes/fixtures; los tests `@integration` no se ejecutan en CI.
- Warning de Starlette/FastAPI (`test_api.py`): preexistente, third-party,
  candidato a silenciar con `filterwarnings`.
