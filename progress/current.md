# Sesión actual

- **Feature en curso:** `f11-wowhead-ingestion` (`in_progress`) — entrega en
  2 slices encadenados; **Slice A cerrado y aprobado**, Slice B pendiente.
- **Última actualización:** 2026-06-18
- **Agente:** leader

f0–f10 `done`. f11 en curso. Suite total tras Slice A: `./init.sh` exit 0,
**277 passed + 2 skipped + 5 deselected** (+21 tests de Slice A; 1 warning =
`StarletteDeprecationWarning` preexistente de f9 `test_api.py`, third-party,
benigno).

## Bitácora

- f0–f9 commiteadas (`4559ada` backlog f5–f8, `bb3429a` f9); f10 en 2 slices
  (`53130c4`, `060f7db`).
- **f11 aprobado** ("aprobado f11", entrega 2 slices encadenados). Leader
  flipó `spec_ready` → `in_progress`.
- **f11 Slice A** (fetcher + robots + rate-limit) — `implementer` → `reviewer`
  APROBADO. Subpaquete `src/wowrag/ingest/wowhead/`: `base.py` (`Fetcher`
  Protocol + errores + `FetchResult`), `fetcher.py` (`HttpxFetcher` lazy +
  `FakeFetcher` que registra URLs pedidas), `robots.py` (`RobotsGate`, stdlib
  `urllib.robotparser`, consultado ANTES de fetch, cache por host),
  `throttle.py` (`RateLimiter`, clock inyectable). 5 campos `scrape_*` en
  `config.py`. Tests prueban que una URL disallowed NUNCA se pide y que el
  rate-limit se aplica con fake clock. ~793 líneas (~388 src, ~405 tests).

## Próximo paso — Slice B de f11

- **Slice B**: `normalizer.py` (HTML→`Document` con `selectolax`, dep aislada
  en `requirements-scrape.txt`, import perezoso → `ScrapeError`),
  `pipeline.py` (fetch robots+rate-limited → normaliza → escribe corpus
  `wowhead.jsonl`), `cli.py`/`__main__.py` (`python -m wowrag.ingest.wowhead`,
  `main(argv, fetcher=None)` inyectable). Reqs restantes (normalización,
  pipeline, CLI, round-trip por `JsonlCorpusLoader`). Tests con fixtures HTML
  + `FakeFetcher`, cero red; fetch real `@integration`.
- Tras Slice B: `reviewer` (puerta final) → `implementer` flipa `f11 → done`
  → leader mueve resumen a `history.md`.

Después de f11 solo queda **`f12-reranking`** (`pending`, depende de f5).

## Riesgos / notas

- f11 desbloquea la validación end-to-end con corpus real; hasta cerrarlo todo
  sigue probado con fakes (sin red, sin Ollama/pgvector/bge-m3 vivos).
- `selectolax` (Slice B) será la primera dep de scraping; aislada en
  `requirements-scrape.txt`, fuera de init.sh, import perezoso.
- Warning de Starlette/FastAPI (`test_api.py`) es preexistente y third-party;
  candidato a silenciar con `filterwarnings` más adelante, no bloqueante.
