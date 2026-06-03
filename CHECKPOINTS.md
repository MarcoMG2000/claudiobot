# CHECKPOINTS — Evaluación del estado final

> En sistemas multi-agente no se evalúa el camino, se evalúa el destino.
> Estos son los checkpoints objetivos para decidir si el proyecto está sano.

## C1 — El arnés está completo

- [x] Existen los archivos base: `AGENTS.md`, `init.sh`, `feature-list.json`,
      `progress/current.md`.
- [x] Existen los 4 docs: `docs/architecture.md`, `docs/conventions.md`,
      `docs/specs.md`, `docs/verification.md`.
- [ ] `./init.sh` termina con exit code 0.

## C2 — El estado es coherente

- [ ] Como mucho una feature en `in_progress` en `feature-list.json`.
- [ ] Toda feature `done` tiene tests asociados que pasan.
- [ ] `progress/current.md` está vacío o describe la sesión activa.

## C3 — El código respeta la arquitectura

- [ ] `src/wowrag/` respeta la separación por capas de `docs/architecture.md`
      (ingest / embeddings / store / retrieval / generation / rag / api).
- [ ] Cada servicio externo (embeddings, vector store, LLM) vive detrás de su
      interfaz; nada de SQL o HTTP a Ollama fuera de su capa.
- [ ] `requirements.txt` tiene versiones **pineadas** y solo lo necesario.
- [ ] No hay `print()` de debug, ni secretos en el repo, ni TODOs sin contexto.

## C4 — La verificación es real

- [ ] `tests/` tiene al menos un test por módulo de `src/wowrag/`.
- [ ] La lógica se testea con **fakes** (sin Postgres/Ollama/red); lo que
      necesita servicios reales está marcado `@pytest.mark.integration`.
- [ ] `pytest -m "not integration"` muestra > 0 tests y todos verdes.

## C5 — El contrato de grounding se respeta

- [ ] Existe y se testea la **abstención** por debajo del umbral de score.
- [ ] Las respuestas no-abstenidas devuelven **citas** (URLs de wowhead).
- [ ] El prompt enviado al LLM contiene **solo** el contexto recuperado.

## C6 — Spec Driven Development

- [ ] Toda feature con `"sdd": true` en `spec_ready`/`in_progress`/`done` tiene
      su carpeta `specs/<id>/` con `requirements.md`, `design.md`, `tasks.md`.
- [ ] `requirements.md` usa EARS estricto (ver `docs/specs.md`).
- [ ] Toda feature `done` con `"sdd": true` tiene todas sus tasks `[x]`.
- [ ] Cada `R<n>` de `requirements.md` está cubierto por al menos un test.

---

**Cómo usar este archivo:** el `reviewer` recorre cada checkbox, marca `[x]` o
`[ ]`, y rechaza el cierre si quedan boxes vacíos relevantes a la feature.
