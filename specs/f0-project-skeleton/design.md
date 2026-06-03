# Design — f0-project-skeleton

> CÓMO se construye el esqueleto. Respeta el layout de `docs/architecture.md` §6
> y las convenciones de `docs/conventions.md`. No implementa lógica de capas
> posteriores.

## 1. Archivos a crear

### Esqueleto del paquete (R1, R2)

Según el layout de `docs/architecture.md` §6. En f0 todos los módulos de capa son
**placeholders importables** (solo `__init__.py`, sin lógica):

```
src/
  wowrag/
    __init__.py          # exporta Settings, Persona, load_persona, __version__
    config.py            # Settings (pydantic-settings) + factory de persona por defecto
    personas/
      __init__.py        # Persona + load_persona (loader YAML)
      simple.yaml
      orc.yaml
      troll.yaml
    ingest/__init__.py        # placeholder
    embeddings/__init__.py    # placeholder
    store/__init__.py         # placeholder
    retrieval/__init__.py     # placeholder
    generation/__init__.py    # placeholder
    rag/__init__.py           # placeholder
    api/__init__.py           # placeholder
```

> Nota: `models.py` y los módulos internos (`loader.py`, `chunking.py`,
> `base.py`, etc.) del layout de arquitectura **se difieren** a sus features
> respectivas (f1+). f0 solo garantiza que los subpaquetes existen y son
> importables.

### Ficheros de soporte en la raíz

- `requirements.txt` (R13)
- `.gitignore` (R14)
- `.env.example` (R14)

`init.sh` ya existe y no se toca; debe seguir verde tras crear `requirements.txt`
(R13/R14 lo mantienen verde porque las deps pineadas instalan sin conflicto).

## 2. Contrato de `Settings` (R3–R6)

`src/wowrag/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_dsn: str = "postgresql://wowrag:wowrag@localhost:5432/wowrag"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    top_k: int = 5
    score_threshold: float = 0.30
    default_persona: str = "simple"
```

Notas de contrato:
- Defaults sensatos alineados con `docs/architecture.md` §2 (qwen2.5:7b-instruct,
  bge-m3, dim 1024 típica de bge-m3).
- `env_file=".env"` cubre R6; pydantic-settings da prioridad a la variable de
  entorno real sobre el `.env` (cubre R4 + R6 sin conflicto).
- `extra="ignore"` para que campos futuros en `.env.example` no rompan f0.

### Resolución de persona por defecto (R12)

En `config.py`, un helper explícito (punto único de composición, según
`docs/conventions.md` §"Patrón de abstracción"):

```python
def default_persona(settings: Settings | None = None) -> Persona:
    settings = settings or Settings()
    return load_persona(settings.default_persona)
```

## 3. Contrato de `Persona` y loader (R7–R11)

`src/wowrag/personas/__init__.py`:

```python
from pydantic import BaseModel

class Persona(BaseModel):
    name: str
    system_style: str
    language: str | None = None

class PersonaNotFoundError(Exception):
    """Persona solicitada inexistente. Mensaje incluye el nombre pedido."""

def load_persona(name: str) -> Persona:
    """Carga <name>.yaml del directorio de personas. Lanza
    PersonaNotFoundError si no existe."""
```

Comportamiento del loader:
- Resuelve la ruta como `Path(__file__).parent / f"{name}.yaml"`.
- Lee con `yaml.safe_load` y construye `Persona(**data)`.
- SI el fichero no existe → `raise PersonaNotFoundError(f"...: {name!r}...")`
  (R9). El mensaje DEBE contener el `name` solicitado.

### Ficheros de persona (R10, R11)

`simple.yaml`:
```yaml
name: simple
system_style: "Responde de forma clara, concisa y neutra."
language: es
```

`orc.yaml` (R11 — incluye "Zug zug"):
```yaml
name: orc
system_style: "Habla como un orco de Horda: directo, gutural, con interjecciones tipo 'Zug zug!' y 'Lok'tar'. Mantén la respuesta correcta."
language: es
```

`troll.yaml`:
```yaml
name: troll
system_style: "Habla como un troll de WoW: cadencioso, con 'mon' y 'ya'. Mantén la respuesta correcta."
language: es
```

## 4. Exports de `wowrag/__init__.py` (R1)

```python
from wowrag.config import Settings, default_persona
from wowrag.personas import Persona, PersonaNotFoundError, load_persona

__version__ = "0.0.0"
__all__ = ["Settings", "Persona", "PersonaNotFoundError",
           "load_persona", "default_persona", "__version__"]
```

## 5. `requirements.txt` (R13)

Solo lo necesario para f0, versiones pineadas con `==`:

```
pydantic-settings==<x.y.z>
pyyaml==<x.y.z>
pytest==<x.y.z>
```

`pydantic` entra como dependencia transitiva de `pydantic-settings`; no se pinea
por separado a menos que el implementer detecte la necesidad. **No** se incluyen
fastapi/uvicorn/torch/sentence-transformers/psycopg (diferidas).

## 6. `.gitignore` y `.env.example` (R14)

`.gitignore` mínimo:
```
.env
.venv/
__pycache__/
*.pyc
```

`.env.example` documenta los campos de R5 con placeholders no-secretos
(mismos defaults que `Settings`, salvo credenciales que se dejan como ejemplo).

## 7. Excepciones definidas

- `PersonaNotFoundError(Exception)` — única excepción nueva (R9). La abstención y
  errores de capas posteriores no aplican en f0.

## 8. Riesgo registrado para features futuras (no f0)

> **Python 3.14 / wheels de ML.** El entorno puede ejecutarse sobre Python 3.14.
> `torch` y `sentence-transformers` (necesarios en `f3-embeddings-provider`)
> pueden no tener wheels binarios para 3.14 en el momento de implementarlas,
> causando fallos de compilación al instalar. f0 **no** usa ML, así que no se ve
> afectada; pero el implementer de f3 debe verificar disponibilidad de wheels o
> fijar un Python compatible (3.11–3.12) en el entorno antes de añadir esas
> dependencias. Se anota aquí para no bloquear features futuras por sorpresa.

## 9. Alternativa descartada

- **Personas en código (módulos Python) en vez de YAML.** Descartada: viola
  `docs/conventions.md` §Configuración ("Personas/estilos en ficheros de datos,
  no en código") y rompe el objetivo de personas swappable por fichero. Se usa
  YAML cargado por el loader.
- **Pinear `pydantic` explícito además de `pydantic-settings`.** Descartado en
  f0 para mantener `requirements.txt` mínimo; `pydantic-settings` arrastra
  `pydantic` con su propio rango. Se reconsiderará si surge un conflicto.
