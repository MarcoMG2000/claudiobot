# Tasks — f7-llm-provider-ollama

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Los tests unitarios usan solo stdlib + `FakeLLMProvider`; sin `httpx`,
> sin red, sin un Ollama vivo. La trazabilidad `R<n>` ↔ test es obligatoria
> (`docs/verification.md`); nombra o comenta cada test con su `R<n>`.
>
> **Entrega: PR único.** En `design.md` §0 la estimación (~360 líneas) está por
> debajo del presupuesto de ~400 líneas de un PR revisable; f7 NO se parte en
> slices. La numeración `R<n>` es estable.
>
> **Frontera de f7 (no cruzar):** f7 = abstracción `LLMProvider` + `OllamaLLM`
> (HTTP local) + `FakeLLMProvider`. f7 NO construye prompts/persona (f6), NO
> orquesta retrieve→prompt→generate ni decide abstención ni ensambla `Answer`
> con citas/metadata (f8), NO hace retrieval (f5). `generate` devuelve `str`
> plano; `models.py` NO se toca.
>
> NO marques la feature `done` ni edites `feature-list.json` (eso lo hacen el
> leader/reviewer tras validar la trazabilidad `R<n>` ↔ test).

## Implementación

- [x] **T1 — Interfaz `LLMProvider` y excepción `LLMError`.**
  Crear `src/wowrag/llm/base.py` con `from __future__ import annotations`:
  - `LLMError(Exception)` — excepción de dominio de la capa LLM (cliente HTTP
    ausente, Ollama inalcanzable, prompt vacío, respuesta inválida).
  - `LLMProvider` Protocol con:
    - propiedad de solo lectura `model: str` (sin red);
    - `generate(prompt: str) -> str` (texto completo);
    - `generate_stream(prompt: str) -> Iterator[str]` (fragmentos cuya
      concatenación == `generate`).
  - Docstrings con el contrato: prompt vacío → `LLMError` sin red; concatenación
    de fragmentos == `generate`; `model` no contacta a Ollama.
  _(Cubre R1, R2, R3, R4, R18)_

- [x] **T2 — `FakeLLMProvider` determinista, sin red.**
  Crear `src/wowrag/llm/fake.py` con `FakeLLMProvider` (solo stdlib, cero
  imports de red/`httpx`):
  - Constructor `__init__(self, model: str = "fake-llm", prefix: str = "ECHO: ")`;
    propiedad `model`.
  - `generate(prompt)`: prompt vacío/espacios → `LLMError`; en otro caso devuelve
    una cadena que es **función pura** del prompt + config (determinista).
  - `generate_stream(prompt)`: valida prompt (→ `LLMError`); produce fragmentos
    cuya **concatenación exacta** == `generate(prompt)` (byte-igual).
  _(Cubre R14, R15, R16, R17)_

- [x] **T3 — `OllamaLLM` con import lazy del cliente HTTP.**
  Crear `src/wowrag/llm/ollama.py` con `OllamaLLM`:
  - Constructor `__init__(self, model="qwen2.5:7b-instruct",
    base_url="http://localhost:11434", timeout=120.0)`; defaults coherentes con
    `Settings` (R12).
  - Import de `httpx` **dentro del constructor** (no a nivel de módulo); si falla
    → `LLMError` con mensaje de instalación (`requirements-llm.txt`). `import
    json` a nivel de módulo es stdlib y está permitido.
  - Propiedad `model` que devuelve el nombre configurado sin red.
  - `generate(prompt)`: valida prompt vacío (→ `LLMError`, sin red); POST a
    `{base_url}/api/generate` con `{model, prompt, stream: False}`;
    `raise_for_status()`; devuelve `data["response"]`; status de error o conexión
    fallida → `LLMError`; cuerpo no-JSON o sin `response` → `LLMError`.
  - `generate_stream(prompt)`: valida prompt; POST con `stream: True`; itera las
    líneas NDJSON, hace `yield obj["response"]` por línea con `response`, termina
    al ver `done=true`; errores de red/HTTP → `LLMError`.
  _(Cubre R5, R6, R7, R8, R9, R10, R11, R12, R19, R20)_

- [x] **T4 — Re-exportar desde `llm/__init__.py`.**
  Crear `src/wowrag/llm/__init__.py` con imports y `__all__` que exporten
  `LLMError`, `LLMProvider`, `FakeLLMProvider`, `OllamaLLM`. Verificar que
  `from wowrag.llm import OllamaLLM` funciona **sin `httpx` instalado** (el import
  de `httpx` es lazy dentro de `OllamaLLM.__init__`).
  _(Cubre R21; refuerza R8)_

- [x] **T5 — Crear `requirements-llm.txt`.**
  Crear `requirements-llm.txt` en la raíz con `httpx>=0.27.0` y un comentario que
  lo identifique como dependencia manual excluida de `init.sh` (espejo de
  `requirements-ml.txt` / `requirements-pg.txt`). NO añadir `httpx` a
  `requirements.txt` ni a la lista `DEFERRED` de `test_requirements_pinned.py`.
  _(Condición necesaria para R5, R8, R9; aísla la dependencia de red de la suite
  unitaria)_

## Tests

- [x] **T6 — `tests/test_llm_interface.py`** (contrato vía `FakeLLMProvider`,
  sin red). Casos mínimos (citar `R<n>`):
  - `test_generate_returns_string`: `fake.generate("hola mundo")` → `str` no
    vacío. _(R2)_
  - `test_generate_deterministic`: mismo prompt dos veces (misma instancia y
    entre dos instancias con misma config) → misma cadena. _(R15)_
  - `test_stream_concatenation_equals_generate`:
    `"".join(fake.generate_stream(p)) == fake.generate(p)`. _(R3, R16)_
  - `test_model_property`: `FakeLLMProvider(model="m").model == "m"`. _(R4)_
  - `test_fake_satisfies_protocol`: `FakeLLMProvider` asignable a `LLMProvider`
    (Protocol estructural). _(R1)_
  - `test_empty_prompt_raises`: `fake.generate("")` y `fake.generate("   ")` →
    `LLMError`. _(R17)_
  - `test_stream_empty_prompt_raises`: `list(fake.generate_stream(""))` →
    `LLMError`. _(R17)_
  - `test_ollama_module_importable_without_httpx`: `import wowrag.llm.ollama` no
    lanza `ImportError` (módulo importable sin `httpx`). _(R8)_
  - `test_ollama_instantiation_raises_without_httpx`: simular ausencia de `httpx`
    (p. ej. `monkeypatch.setitem(sys.modules, "httpx", None)`) y comprobar que
    `OllamaLLM()` lanza `LLMError` (no `ImportError`). _(R9)_

- [x] **T7 — `tests/test_config.py`** (editar, añadir 1 caso).
  `ollama_url` y `llm_model` ya están en `EXPECTED_DEFAULTS` (default-assert
  cubierto). Añadir:
  - `test_ollama_url_and_llm_model_overridable_from_env`: `monkeypatch.setenv`
    `OLLAMA_URL` y `LLM_MODEL`; `Settings(_env_file=None)` los refleja. _(R13)_
  (Recordar que el fixture `_clear_env` itera `EXPECTED_DEFAULTS`, que ya
  incluye ambas claves; no hace falta tocar el fixture.)

- [x] **T8 — `tests/test_llm_ollama.py`** (integración).
  Crear el fichero con `pytest.importorskip("httpx")` a nivel de módulo y
  `@pytest.mark.integration` en cada test (se excluyen automáticamente por
  `init.sh`). Fixtures que saltan si no hay un Ollama configurado/alcanzable.
  Casos mínimos (requieren `httpx`; algunos requieren Ollama vivo):
  - `test_generate_roundtrip`: `OllamaLLM(...).generate("Say hi in one word")` →
    `str` no vacío. _(R5, R6)_
  - `test_generate_stream_roundtrip`: `generate_stream(...)` produce ≥ 1
    fragmento; su concatenación es no vacía. _(R7)_
  - `test_model_property_no_network`: `OllamaLLM(model="m").model == "m"` sin
    contactar el servidor. _(R20)_
  - `test_unreachable_server_raises`: `OllamaLLM(base_url="http://127.0.0.1:1")
    .generate("x")` → `LLMError`. _(R10)_
  - `test_empty_prompt_no_request`: `OllamaLLM().generate("")` → `LLMError` sin
    abrir conexión. _(R11)_
  - `test_invalid_response_schema_raises`: respuesta sin campo `response` (mock
    de `httpx` o servidor de prueba) → `LLMError`. _(R19)_

## Cierre

- [x] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde (tests previos + T6, T7). Los tests de T8
  deben existir en disco y estar marcados `@pytest.mark.integration` (+ module
  `importorskip("httpx")`); no tienen que pasar en `init.sh`. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R21) tienen al menos un test
    (unitario o de integración).
  - `from wowrag.llm import LLMProvider, LLMError, FakeLLMProvider, OllamaLLM`
    funciona **sin `httpx` instalado**; `import wowrag.llm.ollama` no lanza
    `ImportError`; instanciar `OllamaLLM` sin `httpx` → `LLMError` (no
    `ImportError`).
  - **Frontera de f7 mantenida:** no hay construcción de prompts/persona (f6), ni
    orquestación retrieve→prompt→generate / abstención / ensamblado de `Answer`
    con citas (f8), ni retrieval (f5) en el código de f7. `generate` devuelve
    `str`; `models.py` NO fue modificado.
  - **Sin red ni imports pesados en el camino core:** ningún módulo de `src/` (ni
    test unitario) importa `httpx` a nivel de módulo; `init.sh` corre sin `httpx`
    instalado.
  - `requirements-llm.txt` existe pero NO está referenciado en `requirements.txt`
    ni en `init.sh`; `test_requirements_pinned.py` sigue verde (`httpx` no
    aparece en `requirements.txt`).
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json`. El cambio de estado y el cierre los hacen el leader /
> reviewer tras validar la trazabilidad `R<n>` ↔ test. Tu trabajo termina cuando
> todas las tasks `[x]` y `./init.sh` pasa en verde.
