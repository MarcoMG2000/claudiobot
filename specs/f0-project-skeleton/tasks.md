# Tasks — f0-project-skeleton

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests usan `tmp_path`/imports en memoria, sin servicios reales
> (sin Postgres, Ollama ni red). Recuerda: la trazabilidad `R<n>` ↔ test es
> obligatoria (`docs/verification.md`); nombra/comenta cada test con su `R<n>`.

## Implementación

- [ ] **T1 — Esqueleto de subpaquetes placeholder.** Crear `src/wowrag/__init__.py`
  y los `__init__.py` vacíos (con docstring breve) de los subpaquetes
  `ingest`, `embeddings`, `store`, `retrieval`, `generation`, `rag`, `api`.
  _(Cubre R1, R2)_

- [ ] **T2 — `Settings` con pydantic-settings.** Crear `src/wowrag/config.py`
  con la clase `Settings` (campos y defaults de design §2), `env_file=".env"`,
  `extra="ignore"`. _(Cubre R3, R4, R5, R6)_

- [ ] **T3 — Modelo `Persona`, error y loader.** Crear
  `src/wowrag/personas/__init__.py` con `Persona` (R7), `PersonaNotFoundError`
  y `load_persona(name)` que lee `<name>.yaml` del directorio y lanza el error
  claro si no existe. _(Cubre R7, R8, R9)_

- [ ] **T4 — Ficheros de persona.** Crear `simple.yaml`, `orc.yaml`
  (con rasgo "Zug zug") y `troll.yaml` en `src/wowrag/personas/` con al menos
  `name` y `system_style`. _(Cubre R10, R11)_

- [ ] **T5 — Persona por defecto.** Añadir `default_persona(settings=None)` en
  `config.py` que resuelve la persona vía `Settings.default_persona` +
  `load_persona`. Actualizar exports en `wowrag/__init__.py`.
  _(Cubre R12, R1)_

- [ ] **T6 — `requirements.txt` pineado.** Crear `requirements.txt` con
  `pydantic-settings`, `pyyaml`, `pytest` pineados con `==` y sin las deps
  diferidas. _(Cubre R13)_

- [ ] **T7 — `.gitignore` y `.env.example`.** Crear `.gitignore` (ignora `.env`,
  `.venv`, `__pycache__`) y `.env.example` documentando los campos de R5 sin
  secretos reales. _(Cubre R14)_

## Tests (un fichero por módulo, sin servicios reales)

- [ ] **T8 — `tests/test_package_imports.py`.** Importa `wowrag` y cada
  subpaquete placeholder; afirma que no lanzan. _(Cubre R1, R2)_

- [ ] **T9 — `tests/test_config.py`.**
  - `Settings()` sin entorno devuelve los defaults esperados (R3, R5).
  - Con `monkeypatch.setenv(...)` para un campo (p. ej. `TOP_K`), `Settings()`
    toma el valor del entorno (R4).
  - Con un `.env` escrito en `tmp_path` (usando `chdir` o `_env_file`), los
    valores se leen del fichero (R6).
  _(Cubre R3, R4, R5, R6)_

- [ ] **T10 — `tests/test_personas.py`.**
  - `load_persona("simple")` devuelve una `Persona` con `name` y `system_style`
    (R7, R8, R10).
  - `load_persona("orc").system_style` contiene "Zug zug" (R11).
  - `load_persona("simple")`, `("orc")`, `("troll")` todas cargan (R10).
  - `load_persona("nope")` lanza `PersonaNotFoundError` y el mensaje contiene
    `"nope"` (R9).
  - `default_persona()` con `default_persona="orc"` devuelve la persona orc
    (R12) — inyectando un `Settings` o vía `monkeypatch.setenv`.
  _(Cubre R7, R8, R9, R10, R11, R12)_

- [ ] **T11 — `tests/test_requirements_pinned.py`.** Lee `requirements.txt`;
  afirma que `pydantic-settings`, `pyyaml` y `pytest` aparecen pineados con
  `==`, y que `fastapi`/`uvicorn`/`torch`/`sentence-transformers`/`psycopg`
  NO aparecen. _(Cubre R13)_

- [ ] **T12 — `tests/test_repo_hygiene.py`.** Afirma que `.gitignore` contiene
  `.env`, `.venv` y `__pycache__`, y que existe `.env.example` que menciona los
  campos de R5. _(Cubre R14)_

## Cierre

- [ ] **T13 — Verificación.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite (no-integration) en verde. _(Cubre R13, R14 + integración del conjunto)_
