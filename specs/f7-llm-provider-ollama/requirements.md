# Requirements — f7-llm-provider-ollama

> Feature: `f7-llm-provider-ollama` — LLM provider abstraction + Ollama
> (local HTTP). Depends only on `f0-project-skeleton` (done).
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. La **interfaz `LLMProvider`** (Protocol swappable) en `src/wowrag/llm/base.py`:
   el punto de intercambio que toda implementación de modelo de lenguaje debe
   satisfacer (generación no-streaming + generación streaming opcional).
2. El **`LLMError`** — excepción de dominio de la capa LLM (driver/cliente HTTP
   ausente, Ollama inalcanzable, respuesta inválida).
3. La **implementación `OllamaLLM`** — respaldada por un Ollama local vía HTTP,
   con modelo configurable, import lazy del cliente HTTP (aislamiento de la
   dependencia de red, mismo espíritu que f3 con `FlagEmbedding` y f4 con
   `psycopg`).
4. El **`FakeLLMProvider`** — implementación determinista, sin red ni cliente
   HTTP, usable en todos los tests unitarios de f7 y aguas abajo (f8), de modo
   que f8 pueda intercambiar Fake↔Ollama por configuración.
5. La **configuración** vía `Settings`: f7 **reutiliza** los campos existentes
   `ollama_url` y `llm_model` (ya creados en f0), y los dota de tests de default
   + override (lección f3 R10 / f5).

### Fuera de alcance (explícito — frontera de f7)

f7 provee **solo** la abstracción `LLMProvider` + la implementación `OllamaLLM`
(HTTP local) + un `FakeLLMProvider` para tests. f7 **NO**:

- **Construye prompts ni inyecta persona/estilo** (system + user prompt,
  marcadores de cita, instrucción de grounding): diferido a **f6**
  (`PromptBuilder`). f7 recibe el prompt ya construido como entrada de texto.
- **Orquesta** retrieve → prompt → generate, **NO decide abstención**, **NO**
  ensambla la respuesta final con citas + metadata: diferido a **f8**
  (`RagOrchestrator`), que **consume** este `LLMProvider`.
- **Hace recuperación** (query → embedding → top-k → umbral): es f5
  (`Retriever`), ya hecho.
- Define el contrato de grounding de la respuesta (`Answer.abstained`, `sources`):
  es f8 / la capa de orquestación. La **abstención NO es responsabilidad de
  f7**: f7 solo genera texto a partir del prompt que recibe.
- No carga modelos en memoria ni los descarga: el modelo lo sirve el proceso
  Ollama externo; f7 solo habla HTTP con él.

> **Contrato hacia f8 (deliberado):** `LLMProvider.generate(prompt) -> str`
> es el contrato mínimo que f8 necesita para producir el cuerpo de la respuesta.
> El `generate_stream(prompt) -> Iterator[str]` opcional habilita streaming de
> tokens (Ollama lo soporta de forma nativa) para que f9 (FastAPI async-native)
> pueda exponer respuestas incrementales sin cambiar la interfaz. Ver `design.md`
> §3 para la justificación de la firma elegida (no-streaming primaria + streaming
> opcional).

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "LLMProvider interface with an Ollama implementation (local HTTP); model
> configurable; unit-testable via a fake provider."

| Fragmento del acceptance                          | Requisitos que lo cubren        |
|---------------------------------------------------|---------------------------------|
| LLMProvider interface                             | R1, R2, R3, R4                  |
| Ollama implementation (local HTTP)                | R5, R6, R7, R8, R9, R10, R11    |
| model configurable                                | R12, R13                        |
| unit-testable via a fake provider                 | R14, R15, R16, R17              |

(Requisitos transversales: excepción de dominio R18–R20; exports del paquete
R21.)

## Requisitos

### Interfaz `LLMProvider`

**R1** — El sistema DEBE definir una interfaz `LLMProvider` (Protocol) en
`src/wowrag/llm/base.py` que sirva como único punto de intercambio para las
implementaciones de modelo de lenguaje.

**R2** — El sistema DEBE definir en `LLMProvider` un método
`generate(prompt: str) -> str` que, dado un prompt no vacío, devuelva el texto
completo generado por el modelo como una única cadena.

**R3** — El sistema DEBE definir en `LLMProvider` un método
`generate_stream(prompt: str) -> Iterator[str]` que, dado un prompt no vacío,
produzca el texto generado en fragmentos (tokens/chunks) sucesivos, de modo que
la concatenación de todos los fragmentos sea equivalente al resultado de
`generate` para el mismo prompt e implementación determinista.

**R4** — El sistema DEBE definir en `LLMProvider` una propiedad de solo lectura
`model: str` que devuelva el nombre del modelo que la implementación concreta
usará para generar.

### Implementación `OllamaLLM` (local HTTP)

**R5** — El sistema DEBE proveer una implementación concreta `OllamaLLM` de
`LLMProvider` que genere texto invocando un servidor **Ollama local** a través
de su API HTTP (endpoint de generación `/api/generate`).

**R6** — CUANDO se llama a `OllamaLLM.generate(prompt)`, el sistema DEBE enviar
una petición HTTP POST a `{ollama_url}/api/generate` con el `model` configurado,
el `prompt` recibido y `stream=false`, y DEBE devolver el campo `response` del
cuerpo JSON de la respuesta como la cadena generada.

**R7** — CUANDO se llama a `OllamaLLM.generate_stream(prompt)`, el sistema DEBE
enviar la petición con `stream=true` y DEBE producir, en orden, el campo
`response` de cada línea JSON (NDJSON) que Ollama emite, terminando cuando la
línea con `done=true` se recibe.

**R8** — El sistema DEBE realizar la importación del cliente HTTP
**dentro del constructor o de los métodos** de `OllamaLLM`, no a nivel de módulo,
de modo que `src/wowrag/llm/ollama.py` sea importable sin el cliente HTTP
instalado.

**R9** — SI se intenta construir o usar `OllamaLLM` y el cliente HTTP no está
instalado, ENTONCES el sistema DEBE lanzar `LLMError` con un mensaje que indique
cómo instalar las dependencias de la capa LLM (`requirements-llm.txt`).

**R10** — SI el servidor Ollama es inalcanzable o responde con un código de
estado HTTP de error en `generate` o `generate_stream`, ENTONCES el sistema DEBE
lanzar `LLMError` identificando el fallo, sin enmascararlo como una cadena vacía.

**R11** — SI `generate` o `generate_stream` reciben un `prompt` vacío o compuesto
solo de espacios en blanco, ENTONCES el sistema DEBE lanzar `LLMError` sin
realizar ninguna petición de red.

### Modelo configurable

**R12** — El sistema DEBE que `OllamaLLM` acepte el nombre del modelo y la URL
base de Ollama como parámetros de construcción, con defaults coherentes con
`Settings` (`llm_model = "qwen2.5:7b-instruct"`, `ollama_url =
"http://localhost:11434"`), de modo que el modelo sea seleccionable sin cambiar
código.

**R13** — El sistema DEBE reutilizar los campos existentes `ollama_url` y
`llm_model` de `Settings` (`src/wowrag/config.py`) como única fuente de verdad
para la URL base y el nombre del modelo de `OllamaLLM`, sin redefinirlos, y
ambos DEBEN ser configurables desde entorno o `.env`.

### `FakeLLMProvider` (sin red, para tests)

**R14** — El sistema DEBE proveer una implementación `FakeLLMProvider` de
`LLMProvider` que genere texto de forma **determinista** a partir del prompt sin
importar ningún cliente HTTP ni realizar ninguna llamada de red, usable en todos
los tests unitarios (f7, f8) sin un Ollama vivo.

**R15** — CUANDO se llama a `FakeLLMProvider.generate(prompt)` con el mismo
prompt dos veces (en la misma instancia o entre instancias con la misma
configuración), el sistema DEBE devolver exactamente la misma cadena
(determinismo).

**R16** — CUANDO se llama a `FakeLLMProvider.generate_stream(prompt)`, el sistema
DEBE producir fragmentos cuya concatenación sea idéntica al valor que
`FakeLLMProvider.generate(prompt)` devuelve para el mismo prompt (paridad
stream/no-stream, espejo de R3).

**R17** — SI `FakeLLMProvider.generate` o `generate_stream` reciben un `prompt`
vacío o compuesto solo de espacios en blanco, ENTONCES el sistema DEBE lanzar
`LLMError` (paridad de contrato con `OllamaLLM`, R11).

### Excepción de dominio

**R18** — El sistema DEBE definir una excepción de dominio `LLMError(Exception)`
en `src/wowrag/llm/base.py` para todos los fallos de la capa LLM (cliente HTTP
ausente, Ollama inalcanzable, respuesta inválida, prompt vacío).

**R19** — SI la respuesta de Ollama no contiene un campo `response`
interpretable (cuerpo no-JSON o esquema inesperado), ENTONCES el sistema DEBE
lanzar `LLMError` identificando la condición, sin devolver una cadena vacía
silenciosa.

**R20** — El sistema DEBE que `OllamaLLM.model` devuelva el nombre del modelo
configurado sin realizar ninguna llamada de red (la propiedad no contacta a
Ollama).

### Exports del paquete

**R21** — El sistema DEBE re-exportar `LLMProvider`, `LLMError`,
`FakeLLMProvider` y `OllamaLLM` desde `src/wowrag/llm/__init__.py`, de modo que
los consumidores de la capa `llm` (f8) dependan del paquete, no de los módulos
internos.
