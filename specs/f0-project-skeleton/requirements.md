# Requirements — f0-project-skeleton

> Feature: `f0-project-skeleton` — Project skeleton & configuration system.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es verificable por
> al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece **solo el esqueleto importable** del paquete `wowrag`, el
sistema de configuración (`pydantic-settings`), el sistema de personas swappable
cargadas desde ficheros YAML, y las dependencias pineadas mínimas. **No** se
implementa la lógica de ninguna capa posterior (ingest, embeddings, store,
retrieval, generation, rag, api): esos subpaquetes existen como placeholders
importables únicamente.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "src/ package layout exists; pydantic-settings loads config from env + files;
> persona/style configs are loadable and swappable; requirements.txt is pinned;
> init.sh sets up venv, installs deps, runs pytest green."

| Fragmento del acceptance                              | Requisitos que lo cubren |
|-------------------------------------------------------|--------------------------|
| src/ package layout exists                            | R1, R2                   |
| pydantic-settings loads config from env + files       | R3, R4, R5, R6           |
| persona/style configs are loadable and swappable      | R7, R8, R9, R10, R11     |
| requirements.txt is pinned                            | R12                      |
| init.sh sets up venv, installs deps, runs pytest green| R13, R14                 |

## Requisitos

### Estructura e importabilidad del paquete

**R1** — El sistema DEBE exponer el paquete `wowrag` de forma que `import wowrag`
tenga éxito sin lanzar ninguna excepción.

**R2** — El sistema DEBE exponer los subpaquetes placeholder `wowrag.ingest`,
`wowrag.embeddings`, `wowrag.store`, `wowrag.retrieval`, `wowrag.generation`,
`wowrag.rag` y `wowrag.api` de forma que cada uno pueda importarse sin lanzar
ninguna excepción.

### Configuración (`pydantic-settings`)

**R3** — El sistema DEBE proveer una clase `Settings` que, al instanciarse sin
argumentos y sin variables de entorno presentes, devuelva valores por defecto
para todos sus campos sin lanzar ninguna excepción.

**R4** — CUANDO una variable de entorno correspondiente a un campo de `Settings`
está definida, el sistema DEBE tomar el valor de esa variable de entorno en
lugar del valor por defecto al instanciar `Settings`.

**R5** — El sistema DEBE exponer en `Settings` los campos `postgres_dsn`,
`ollama_url`, `llm_model`, `embedding_model`, `embedding_dim`, `top_k`,
`score_threshold` y `default_persona`, cada uno con un valor por defecto
sensato.

**R6** — DONDE exista un fichero `.env` legible en el directorio de trabajo, el
sistema DEBE leer de él los valores de los campos de `Settings` que no estén ya
definidos como variables de entorno.

### Personas swappable

**R7** — El sistema DEBE proveer un modelo `Persona` con al menos los campos
`name` (str), `system_style` (str) y `language` (str opcional).

**R8** — El sistema DEBE proveer un cargador que, dado el nombre de una persona
existente, devuelva una instancia de `Persona` cargada desde su fichero YAML en
`src/wowrag/personas/`.

**R9** — SI se solicita al cargador una persona cuyo nombre no corresponde a
ningún fichero de persona, ENTONCES el sistema DEBE lanzar una excepción clara
que identifique el nombre solicitado.

**R10** — El sistema DEBE incluir los ficheros de persona `simple`, `orc` y
`troll` en `src/wowrag/personas/`, cada uno definiendo al menos `name` y
`system_style`.

**R11** — CUANDO se carga la persona `orc`, el sistema DEBE devolver una
`Persona` cuyo `system_style` refleje un estilo orco (incluyendo el rasgo
"Zug zug").

### Selección de persona por defecto

**R12** — El sistema DEBE permitir resolver la persona por defecto leyendo el
campo `default_persona` de `Settings` y cargándola mediante el cargador de R8.

### Dependencias

**R13** — El sistema DEBE proveer un `requirements.txt` en la raíz cuyas líneas
de dependencia fijen una versión exacta (operador `==`) para cada una de
`pydantic-settings`, `pyyaml` y `pytest`, y que no contenga las dependencias
diferidas a features posteriores (`fastapi`, `uvicorn`, `torch`,
`sentence-transformers`, `psycopg`).

### Entorno y secretos

**R14** — El sistema DEBE proveer un `.gitignore` que ignore `.env`, `.venv` y
`__pycache__`, y un `.env.example` que documente los campos de configuración de
R5 sin contener secretos reales.
