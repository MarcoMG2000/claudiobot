# Design — f7-llm-provider-ollama

> CÓMO se construye la capa LLM (abstracción + Ollama local + fake). Respeta el
> layout de `docs/architecture.md` §6 y las convenciones del proyecto: interfaz
> en `base.py`, implementación real en módulo aparte, excepción de dominio,
> import lazy de la dependencia de red, `from __future__ import annotations`.
> Sigue el patrón ya establecido en f3 (`EmbeddingProvider` + `requirements-ml.txt`)
> y f4 (`VectorStore` + `requirements-pg.txt`).

## 0. Decisión de entrega: PR único (no slicing)

f7 es **pequeño y autocontenido**: una interfaz con dos métodos + una excepción
+ un fake stdlib + una implementación HTTP fina + 2 tests unitarios + 1 fichero
de tests de integración + 1 `requirements-llm.txt`. Estimación de líneas
cambiadas (código + tests + config):

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `llm/base.py` (Protocol + `LLMError`) | ~55 |
| `llm/fake.py` (`FakeLLMProvider`) | ~45 |
| `llm/ollama.py` (`OllamaLLM`, import lazy) | ~85 |
| `llm/__init__.py` (re-exports) | ~12 |
| `requirements-llm.txt` | ~6 |
| `tests/test_llm_interface.py` (contrato vía fake) | ~70 |
| `tests/test_llm_ollama.py` (`@pytest.mark.integration`) | ~80 |
| `tests/test_config.py` (editar: 1 test de override) | ~10 |
| **Total estimado** | **~360** |

~360 líneas está **por debajo** del presupuesto de ~400 líneas de un PR
revisable. **Decisión: PR único**, sin slices encadenados. (Contrasta con f4,
que sí se partió en 3 slices por superar el presupuesto). La numeración `R<n>`
es estable independientemente de esta decisión.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    config.py                  # NO se edita (ollama_url, llm_model ya existen en f0; R13)
    llm/
      __init__.py              # NUEVO — re-exportar interfaz, fake, ollama y excepción
      base.py                  # NUEVO — LLMProvider (Protocol) + LLMError
      fake.py                  # NUEVO — FakeLLMProvider (determinista, sin red)
      ollama.py                # NUEVO — OllamaLLM (import lazy del cliente HTTP)
requirements-llm.txt           # NUEVO — cliente HTTP; excluido de init.sh
tests/
  test_llm_interface.py        # NUEVO — contrato de LLMProvider vía FakeLLMProvider
  test_llm_ollama.py           # NUEVO — OllamaLLM (@pytest.mark.integration)
  test_config.py               # EDITAR — añadir test de override de ollama_url + llm_model
```

Notas:
- **`config.py` NO se modifica.** Los campos `ollama_url:
  str = "http://localhost:11434"` y `llm_model: str = "qwen2.5:7b-instruct"` ya
  existen desde f0 (verificado en `src/wowrag/config.py`). f7 los **reutiliza**
  (R13), igual que f4 reutilizó `postgres_dsn`/`embedding_dim`/`top_k` sin
  redefinirlos. Lo único que f7 añade en config es **cobertura de tests** del
  override por env (la lección de f3 R10 / f5: cada campo que la feature consume
  debe tener default-assert + env-override; `ollama_url`/`llm_model` ya están en
  `EXPECTED_DEFAULTS` de `test_config.py`, pero les falta el test de override —
  ver §9).
- **Layer placement: paquete `llm/` dedicado, NO dentro de `generation/`.**
  `docs/architecture.md` §6 dibuja `LLMProvider` dentro de `generation/` junto al
  `prompt_builder`. Sin embargo, la nota de cierre de §6 dice explícitamente que
  «el nombre exacto de módulos puede afinarse en cada spec». Se elige un paquete
  `llm/` separado para que la **capa de modelo de lenguaje** (un servicio externo
  detrás de una interfaz, como `embeddings/` y `store/`) quede al mismo nivel y
  con la misma forma que sus hermanas, y para no acoplar el `PromptBuilder` (f6,
  lógica propia que construye texto) con el cliente HTTP de Ollama (servicio
  externo). Esto es coherente con el patrón del proyecto «cada servicio externo
  vive detrás de una interfaz en el `base.py` de **su** paquete»
  (`docs/conventions.md`) y con la tabla de swap points de §4 que lista
  `LLMProvider → OllamaLLM` como un swap point de primer nivel. El directorio
  `generation/` actual es solo un placeholder de f0 (`"""Generation layer
  (placeholder)..."""`); f6 lo usará para `prompt_builder.py`. El revisor de
  arquitectura rechaza mezclar capas (p. ej. llamadas HTTP a Ollama fuera de su
  capa de servicio); un paquete `llm/` aislado mantiene esa separación limpia.
  (Mismo tipo de decisión documentada que en f4 §8, donde el `IndexingPipeline`
  fue a un módulo `index/` propio en vez de a `ingest/` o `rag/`.)
- `models.py` **NO se toca**: `generate` devuelve `str` plano; el modelo `Answer`
  (con `abstained`, `sources`, `metadata`) es de f8, no de f7.

## 2. Estrategia cliente HTTP / aislamiento de la dependencia de red (riesgo conocido)

### Diagnóstico del riesgo

Hablar con Ollama requiere un **cliente HTTP** y un **proceso Ollama vivo**
sirviendo un modelo local. Si el cliente HTTP se declara como dependencia base
en `requirements.txt`:

- Aumenta la superficie de instalación de `init.sh` para una dependencia que la
  suite unitaria NO necesita (todos los tests de lógica usan `FakeLLMProvider`).
- Acoplaría la suite base a una librería de red, contra la política de
  «solo lo necesario para la feature en curso, sin libs por si acaso»
  (`docs/architecture.md` §7).
- Ningún test puede ejercitar `OllamaLLM` de verdad sin un Ollama corriendo, así
  que la dependencia solo sirve para los tests `@pytest.mark.integration`, que
  `init.sh` excluye.

### Decisión adoptada: aislamiento total de la dependencia HTTP

**Estrategia elegida** (idéntica en espíritu a f3 y f4): _import lazy + extra
opcional separado + fake sin red para tests_.

1. **`requirements.txt` base** — no incluye el cliente HTTP. La suite completa
   corre sin él. **Importante:** `tests/test_requirements_pinned.py` mantiene una
   lista `DEFERRED` (`fastapi, uvicorn, torch, sentence-transformers, psycopg`).
   El cliente HTTP elegido (`httpx`) **no** está en esa lista, así que no la
   viola; aun así, f7 lo mantiene **fuera** de `requirements.txt` por la misma
   razón de aislamiento. (No se añade `httpx` a la lista `DEFERRED` para no
   ampliar el alcance de un test ajeno; basta con no declararlo en
   `requirements.txt`.)

2. **`requirements-llm.txt`** — fichero separado (no cargado por `init.sh`):
   ```
   # LLM HTTP client for OllamaLLM. NOT loaded by init.sh.
   # Install manually only when a local Ollama server is available and you want
   # to run OllamaLLM or its @integration tests:
   #   pip install -r requirements-llm.txt
   httpx>=0.27.0
   ```
   Se instala manualmente solo cuando hay un Ollama local disponible.

3. **Import lazy en `OllamaLLM`** — la importación de `httpx` ocurre **dentro del
   constructor**, no a nivel de módulo:
   ```python
   def __init__(self, ...):
       try:
           import httpx
       except ImportError as exc:
           raise LLMError(
               "HTTP client not installed. "
               "Install LLM dependencies: pip install -r requirements-llm.txt"
           ) from exc  # R9
       ...
   ```
   Esto hace que `from wowrag.llm import OllamaLLM` funcione sin `httpx`
   instalado (R8). Solo al instanciar la clase se exige la dependencia (R9).

4. **Tests de `OllamaLLM` marcados `@pytest.mark.integration`** — el
   `pyproject.toml` ya registra el mark `integration` («tests requiring live
   services (pgvector, Ollama)») e `init.sh` ejecuta `pytest -m "not
   integration"`, por lo que se omiten automáticamente (mismo patrón que f3 con
   bge-m3 y f4 con pgvector). El fichero usa `pytest.importorskip("httpx")` a
   nivel de módulo (como `test_store_pgvector.py` con `psycopg`) y las fixtures
   saltan si no hay un Ollama vivo configurado.

5. **`FakeLLMProvider`** — implementación 100% stdlib, determinista, sin red.
   Cubre TODOS los tests unitarios de f7 y queda disponible para f8.

### Por qué `httpx` y no `requests` ni el SDK `ollama`

- **`httpx`**: cliente HTTP moderno con API síncrona **y** asíncrona en la misma
  librería. El proyecto declara FastAPI async-native (f9) y «async-heavy»; elegir
  `httpx` deja la puerta abierta a un `AsyncOllamaLLM` o a métodos async en el
  futuro sin cambiar de dependencia. Su soporte de streaming
  (`client.stream(...)` con `iter_lines()`) encaja directamente con el NDJSON de
  Ollama (R7).
- **`requests`**: solo síncrono; sin streaming async; obligaría a cambiar de
  librería para f9. Descartado.
- **SDK `ollama` oficial**: añade una capa de abstracción extra sobre el mismo
  HTTP y arrastra sus propias deps; el endpoint `/api/generate` es estable y
  trivial de invocar directamente. Mantener el cliente fino (HTTP plano) reduce
  superficie y deja el control del esquema de petición/respuesta en nuestras
  manos. Descartado para esta etapa.

## 3. Firma de `generate`: no-streaming primaria + streaming opcional (R2, R3)

### Decisión

`LLMProvider` expone **dos** métodos:

- `generate(prompt: str) -> str` — **contrato primario**. Bloquea hasta tener la
  respuesta completa y la devuelve como una sola cadena. Es lo que f8
  (`RagOrchestrator`) necesita para ensamblar el cuerpo de `Answer`: f8 decide
  abstención **antes** de llamar al LLM (si el score < umbral, ni siquiera
  genera), y cuando genera quiere el texto completo para empaquetarlo con citas y
  metadata. Un `str` es el tipo mínimo y más fácil de testear con un fake
  determinista.
- `generate_stream(prompt: str) -> Iterator[str]` — **contrato secundario,
  opcional para el consumidor**. Produce el texto en fragmentos. Ollama soporta
  streaming de tokens de forma nativa (NDJSON con `stream=true`); exponerlo en la
  interfaz permite que f9 (FastAPI async-native) sirva respuestas incrementales
  (SSE / chunked) sin tener que reescribir la interfaz más adelante. La
  invariante de paridad (la concatenación de los fragmentos == `generate`) está
  fijada en R3/R16 y es testeable con el fake sin red.

### Justificación frente al principio «async-heavy / streaming»

El proyecto declara streaming de tokens de Ollama y FastAPI async-native como
principios. Modelar **ambos** métodos desde f7 evita un cambio de interfaz
disruptivo cuando f9 quiera streaming. Aun así, la firma se mantiene **síncrona**
(`-> str` / `-> Iterator[str]`) en f7 por dos razones:

1. f8 (el primer consumidor) es lógica de orquestación que se testea con fakes;
   una interfaz síncrona es más simple de componer y verificar, y FastAPI puede
   envolver llamadas síncronas en un threadpool sin bloquear el event loop.
2. Introducir `async def` ahora obligaría a `pytest-asyncio` y a propagar
   `await` por f8 antes de que haya un consumidor async real (f9). Se difiere esa
   complejidad: cuando f9 la necesite, podrá añadir un método/implementación
   async **junto** a los síncronos sin romper a f8 (la interfaz es un Protocol,
   no una jerarquía rígida). Esta decisión queda registrada en la tabla de
   alternativas descartadas (§10).

### Contrato de los métodos

- `generate(prompt)` → `str` con el texto completo. `prompt` vacío/espacios →
  `LLMError` sin red (R11/R17). Ollama inalcanzable o status de error →
  `LLMError` (R10). Respuesta sin campo `response` → `LLMError` (R19).
- `generate_stream(prompt)` → `Iterator[str]`; cada `next()` cede un fragmento.
  Mismos errores que `generate`. La concatenación de los fragmentos == el texto
  completo (R3/R16).
- `model` → `str` (propiedad de solo lectura), sin red (R4/R20).

## 4. Interfaz `LLMProvider` y excepción (R1, R2, R3, R4, R18)

`src/wowrag/llm/base.py`:

```python
from __future__ import annotations

from typing import Iterator, Protocol


class LLMError(Exception):
    """Domain exception for LLM-layer failures.

    Raised for a missing HTTP client, an unreachable Ollama server, an
    invalid/empty prompt, or an unexpected response schema.
    """


class LLMProvider(Protocol):
    """Swap point: turns a prompt string into generated text.

    Concrete implementations: ``OllamaLLM`` (real, local HTTP) and
    ``FakeLLMProvider`` (deterministic, network-free, for tests). Callers
    (f8 RagOrchestrator) depend on this Protocol, never on a concrete
    implementation, so the backend is selected by config.
    """

    @property
    def model(self) -> str:
        """Name of the model this provider generates with. Read-only; no network."""
        ...

    def generate(self, prompt: str) -> str:
        """Generate the full completion for ``prompt`` as a single string.

        Raises ``LLMError`` on empty/whitespace prompt (no network call), an
        unreachable backend, or an unexpected response.
        """
        ...

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield the completion for ``prompt`` in successive text fragments.

        The concatenation of all yielded fragments equals ``generate(prompt)``
        for the same prompt and implementation. Same error contract as
        ``generate``.
        """
        ...
```

Contrato del Protocol:
- `model` propiedad de solo lectura, sin red (R4, R20).
- `generate` → `str` completo; prompt vacío → `LLMError` (R2, R11).
- `generate_stream` → `Iterator[str]`; concatenación == `generate` (R3).
- Todos los fallos de la capa son `LLMError` (R18).

## 5. `FakeLLMProvider` (R14, R15, R16, R17)

`src/wowrag/llm/fake.py` — sin imports de red, solo stdlib:

```python
from __future__ import annotations

from typing import Iterator

from wowrag.llm.base import LLMError


class FakeLLMProvider:
    """Deterministic, network-free LLM provider for unit tests.

    The completion is a pure function of the prompt (and the configured
    ``model``/``prefix``), so the same prompt always yields the same output
    across instances and sessions. Zero HTTP, zero network. Used by f7 tests
    and by f8 to swap Fake<->Ollama by config.
    """

    def __init__(
        self, model: str = "fake-llm", prefix: str = "ECHO: "
    ) -> None:
        self._model = model
        self._prefix = prefix

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise LLMError("prompt is empty or whitespace-only.")  # R17
        # Deterministic: output is a pure function of the prompt (R15).
        return f"{self._prefix}{prompt.strip()}"

    def generate_stream(self, prompt: str) -> Iterator[str]:
        # Parity with generate: concatenation of fragments == generate(prompt) (R16).
        full = self.generate(prompt)  # validates prompt (R17) and is deterministic
        for token in full.split(" "):
            yield token + " " if token != full.split(" ")[-1] else token
```

Propiedades:
- Determinista: la salida es función pura del prompt + config (R15).
- Sin red, sin `httpx`: stdlib únicamente (R14).
- Paridad stream/no-stream por construcción: `generate_stream` trocea el
  resultado de `generate`, así que la concatenación coincide (R16). _(El
  implementer debe garantizar que la concatenación exacta de los fragmentos sea
  byte-igual a `generate(prompt)`; el troceo por espacios es ilustrativo — un
  troceo por longitud fija también es válido mientras se preserve la
  concatenación.)_
- Prompt vacío/espacios → `LLMError`, sin red, en ambos métodos (R17),
  paridad de contrato con `OllamaLLM` (R11).

## 6. `OllamaLLM` con import lazy (R5–R13, R19, R20)

`src/wowrag/llm/ollama.py`:

```python
from __future__ import annotations

import json
from typing import Iterator

from wowrag.llm.base import LLMError


class OllamaLLM:
    """Real LLMProvider backed by a local Ollama server over HTTP.

    The httpx import happens inside __init__, so this module is importable
    without httpx installed (R8). Only instantiation requires the dependency (R9).
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        try:
            import httpx  # lazy import (R8)
        except ImportError as exc:
            raise LLMError(
                "HTTP client not installed. "
                "Install LLM dependencies: pip install -r requirements-llm.txt"
            ) from exc  # R9
        self._httpx = httpx
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model  # R20: no network

    def generate(self, prompt: str) -> str:
        self._validate(prompt)  # R11
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        try:
            resp = self._httpx.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except Exception as exc:  # connection error or HTTP error status
            raise LLMError(f"Ollama generate failed: {exc}") from exc  # R10
        try:
            data = resp.json()
            return data["response"]  # R6
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(
                f"Unexpected Ollama response schema: {exc}"
            ) from exc  # R19

    def generate_stream(self, prompt: str) -> Iterator[str]:
        self._validate(prompt)  # R11
        payload = {"model": self._model, "prompt": prompt, "stream": True}
        try:
            with self._httpx.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():  # NDJSON, one JSON per line
                    if not line:
                        continue
                    obj = json.loads(line)
                    if "response" in obj:
                        yield obj["response"]  # R7
                    if obj.get("done"):
                        break
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Ollama stream failed: {exc}") from exc  # R10

    @staticmethod
    def _validate(prompt: str) -> None:
        if not prompt or not prompt.strip():
            raise LLMError("prompt is empty or whitespace-only.")  # R11
```

Notas de implementación (para el implementer):
- El endpoint es `POST {base_url}/api/generate`. `stream=false` → un único JSON
  con `response` (R6); `stream=true` → NDJSON, una línea JSON por token con
  `response`, y una línea final con `done=true` (R7).
- `raise_for_status()` convierte un status HTTP de error en excepción → `LLMError`
  (R10). Una conexión rechazada (Ollama caído) también es `Exception` de `httpx`
  → `LLMError` (R10).
- El campo `response` ausente o cuerpo no-JSON → `LLMError` (R19), nunca cadena
  vacía silenciosa (alineado con `docs/conventions.md`: los fallos de
  infraestructura son excepciones claras, no respuestas vacías).
- `model` no contacta a Ollama (R20). La validación de prompt vacío ocurre
  **antes** de cualquier petición (R11).
- El `import json` a nivel de módulo es stdlib y NO viola el aislamiento (R8 solo
  exige que `httpx` sea lazy; el módulo debe importarse sin `httpx`).

## 7. Configuración: reutilizar `ollama_url` y `llm_model` (R12, R13)

`src/wowrag/config.py` **NO se modifica**. Ya existen desde f0:

```python
ollama_url: str = "http://localhost:11434"
llm_model: str = "qwen2.5:7b-instruct"
```

f7 los **reutiliza** (R13) — igual que f4 reutilizó `postgres_dsn`/`embedding_dim`
sin redefinirlos. Punto de composición sugerido (factory, NO obligatorio en f7;
lo consumirá f8 al cablear el orquestador):

```python
def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or Settings()
    return OllamaLLM(model=s.llm_model, base_url=s.ollama_url)
```

Este helper NO se crea en f7; se documenta como contrato de uso esperado para f8.

> Cada campo de `Settings` que la feature consume DEBE tener test de default-assert
> **y** de env-override (lección f3 R10, reforzada en f5). `ollama_url` y
> `llm_model` ya tienen el default-assert vía `EXPECTED_DEFAULTS` en
> `test_config.py`, pero **les falta el test de override por env**; f7 lo añade
> (ver §9 / tasks T7).

## 8. Exports del paquete `llm` (R21)

`src/wowrag/llm/__init__.py`:

```python
from wowrag.llm.base import LLMError, LLMProvider
from wowrag.llm.fake import FakeLLMProvider
from wowrag.llm.ollama import OllamaLLM

__all__ = [
    "LLMError",
    "LLMProvider",
    "FakeLLMProvider",
    "OllamaLLM",
]
```

Como el import de `httpx` en `OllamaLLM` es lazy (dentro de `__init__`), este
`from wowrag.llm import OllamaLLM` funciona sin `httpx` instalado (R8, R21).

## 9. Estrategia de tests

### Tests unitarios (sin red, sin `httpx`) — corren con `init.sh`

- `test_llm_interface.py`: contrato de `LLMProvider` usando `FakeLLMProvider`
  como implementación concreta (cero deps de red):
  - `test_generate_returns_string`: `fake.generate("hola mundo")` → `str` no
    vacío. _(R2)_
  - `test_generate_deterministic`: mismo prompt dos veces → misma cadena (misma
    instancia y entre instancias con misma config). _(R15)_
  - `test_stream_concatenation_equals_generate`: `"".join(fake.generate_stream(p))
    == fake.generate(p)`. _(R3, R16)_
  - `test_model_property`: `FakeLLMProvider(model="m").model == "m"` sin red. _(R4)_
  - `test_fake_satisfies_protocol`: `FakeLLMProvider` asignable a `LLMProvider`
    (Protocol estructural). _(R1)_
  - `test_empty_prompt_raises`: `fake.generate("")` y `fake.generate("   ")` →
    `LLMError`. _(R17, R11 por paridad)_
  - `test_stream_empty_prompt_raises`: `list(fake.generate_stream(""))` →
    `LLMError`. _(R17)_
  - `test_ollama_module_importable_without_httpx`: `import wowrag.llm.ollama` no
    lanza `ImportError` aunque `httpx` no esté instalado. _(R8)_
  - `test_ollama_instantiation_raises_without_httpx`: `OllamaLLM()` lanza
    `LLMError` (no `ImportError`) cuando `httpx` falta. _(R9)_
    _(Skip/condicional: si `httpx` está instalado en el entorno, este caso no
    aplica; usar `pytest.importorskip` inverso o `monkeypatch` del import. El
    implementer puede simular la ausencia con `monkeypatch.setitem(sys.modules,
    "httpx", None)` o marcar el test para entornos sin `httpx`.)_

- `test_config.py` (editar): `ollama_url` y `llm_model` ya están en
  `EXPECTED_DEFAULTS` (default-assert cubierto). Añadir:
  - `test_ollama_url_and_llm_model_overridable_from_env`: `monkeypatch.setenv`
    `OLLAMA_URL` y `LLM_MODEL` → `Settings` los refleja. _(R13)_

### Tests de integración (requieren Ollama vivo + `httpx`) — `@pytest.mark.integration`

- `test_llm_ollama.py`: `pytest.importorskip("httpx")` a nivel de módulo (como
  `test_store_pgvector.py` con `psycopg`); fixtures que saltan si no hay un Ollama
  configurado (p. ej. variable `WOWRAG_OLLAMA_URL` o un health-check fallido).
  Cada test `@pytest.mark.integration` (excluido por `init.sh`). Casos mínimos:
  - `test_generate_roundtrip`: `OllamaLLM(...).generate("Say hi in one word")` →
    `str` no vacío. _(R5, R6)_
  - `test_generate_stream_roundtrip`: `generate_stream` produce ≥ 1 fragmento y
    su concatenación es no vacía. _(R7)_
  - `test_model_property_no_network`: `OllamaLLM(model="m").model == "m"` sin
    contactar el servidor. _(R20)_
  - `test_unreachable_server_raises`: `OllamaLLM(base_url="http://127.0.0.1:1")
    .generate("x")` → `LLMError`. _(R10)_ _(no requiere Ollama vivo, pero vive
    aquí porque requiere `httpx`)_
  - `test_empty_prompt_no_request`: `OllamaLLM().generate("")` → `LLMError` sin
    abrir conexión. _(R11)_

Estos tests se excluyen automáticamente por `pytest -m "not integration"` tal
como establece `init.sh` y el mark registrado en `pyproject.toml`.

## 10. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Import a nivel de módulo de `httpx` en `ollama.py` | Rompe el aislamiento; `import wowrag.llm.ollama` fallaría sin `httpx`. Viola el patrón lazy de f3/f4 (R8) |
| `httpx`/cliente HTTP en `requirements.txt` base | Acopla la suite unitaria a una lib de red que el fake no necesita; contra la política de deps mínimas (`architecture.md` §7) |
| Colocar `LLMProvider` en `generation/` (literal §6) | `generation/` queda para el `PromptBuilder` (f6, lógica propia); mezclar el cliente HTTP de un servicio externo con la construcción de prompts cruza capas. Un paquete `llm/` propio iguala a `embeddings/`/`store/` |
| Solo `generate` (sin `generate_stream`) | El proyecto declara streaming de tokens de Ollama y FastAPI async-native; omitir el streaming forzaría un cambio de interfaz disruptivo en f9 |
| Solo `generate_stream` (sin `generate`) | f8 quiere el texto completo para ensamblar `Answer`; obligar a consumir un iterador siempre complica el orquestador y el fake determinista |
| Interfaz `async def generate(...)` desde f7 | Sin consumidor async real hasta f9; introduciría `pytest-asyncio` y propagaría `await` por f8 prematuramente. El Protocol permite añadir variantes async después sin romper a f8 |
| SDK `ollama` oficial en vez de HTTP plano | Capa extra + deps propias sobre un endpoint estable y trivial; el cliente fino reduce superficie y deja el control del esquema |
| `requests` en vez de `httpx` | Solo síncrono, sin streaming async; obligaría a cambiar de lib para f9 (async-native) |
| `ABC` en lugar de `Protocol` | Inconsistente con `EmbeddingProvider`/`VectorStore`/`CorpusLoader`/`Chunker`; Protocol no requiere herencia y permite que el fake satisfaga el contrato estructuralmente |
| `FakeLLMProvider` con salida aleatoria | No determinista → tests no reproducibles entre sesiones; el fake debe ser función pura del prompt (R15) |
| Modelar abstención / `Answer` / citas en f7 | Es f8 (orquestación). f7 expone el contrato mínimo `generate(prompt) -> str`; acoplar el tipo de respuesta de presentación aquí adelantaría f8 |
| Añadir `httpx` a la lista `DEFERRED` de `test_requirements_pinned.py` | Amplía el alcance de un test ajeno sin necesidad; basta con no declarar `httpx` en `requirements.txt`. Mantener f7 acotado |
| Redefinir `ollama_url`/`llm_model` en `Settings` | Ya existen desde f0; redefinirlos duplica fuentes de verdad (R13) |
