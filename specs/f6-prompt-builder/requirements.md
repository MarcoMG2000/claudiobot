# Requirements — f6-prompt-builder

> Feature: `f6-prompt-builder` — Prompt builder (system+user prompt que inyecta
> persona/estilo y grounding estricto; formatea el contexto recuperado con
> marcadores de cita; persona seleccionada por config).
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).
> Depende de: f5 (done) — consume `RetrievedChunk` / `RetrievalResult`.

## Alcance

Esta feature establece:

1. La **interfaz `PromptBuilder`** (Protocol swappable) en
   `src/wowrag/generation/prompt_builder_base.py`: el punto de intercambio que toda
   implementación de constructor de prompt debe satisfacer.
2. Un modelo de salida **`BuiltPrompt`** que transporta el par de cadenas
   `system` + `user` (y las `sources` numeradas que el prompt cita), para que f8
   pase ambas al `LLMProvider` (f7) y devuelva las citas en la respuesta.
3. La **excepción de dominio `PromptBuilderError`** para entrada inválida del
   constructor (p. ej. pregunta vacía).
4. La **implementación concreta `DefaultPromptBuilder`** que, a partir de una
   `query` y un `RetrievalResult` (de f5) más una `Persona` (de f0), produce un
   `BuiltPrompt`:
   - inyecta el `system_style` de la persona en el prompt de sistema;
   - inyecta instrucciones de **grounding estricto** (responder solo con el
     contexto; citar siempre; declarar falta de evidencia si el contexto no
     respalda);
   - formatea los `RetrievedChunk` recuperados con **marcadores de cita**
     numerados (`[1]`, `[2]`, …) ligados a cada fuente de wowhead.
5. La **selección de persona por config**: la persona por defecto se resuelve vía
   `Settings.default_persona` reutilizando el helper `default_persona()` de f0,
   con posibilidad de override explícito por llamada (para el `persona` por
   petición de f9).
6. La **reutilización** del sistema de personas de f0 (`Persona`, `load_persona`,
   `default_persona`) y del campo de configuración existente `default_persona` de
   `Settings` — sin redefinir personas ni añadir campos de config nuevos.

> **`RetrievedChunk` / `RetrievalResult` vienen de f5** (`src/wowrag/models.py`).
> f6 los CONSUME para formatear el contexto citable; NO los redefine. Cada
> `RetrievedChunk` ya expone `source_url`, `title`, `section` y su `chunk.text`.

### Fuera de alcance (explícito — frontera crítica)

f6 **solo construye la(s) cadena(s) de prompt**. Concretamente, queda fuera de
alcance:

- **Llamar a cualquier LLM / Ollama**: **f7** (`LLMProvider` + `OllamaLLM`). f6 no
  envía el prompt a ningún modelo.
- **Orquestar retrieve → prompt → generate**, producir el **mensaje de abstención**
  y la **respuesta final** (`Answer`): **f8** — f8 CONSUME el `BuiltPrompt` de f6 y
  la señal `below_threshold` de f5 (cuando `below_threshold` es `true`, f8 se
  abstiene **sin** construir/usar prompt de generación; f6 no toma esa decisión).
- **Recuperación** (query → embedding → top-k → scores): **f5** — f6 recibe el
  `RetrievalResult` ya construido.
- **Reranking** del top-k antes de generar: **f12**.
- **Scraping de wowhead**: **f11**.
- **HTTP API / FastAPI / selección de persona por petición HTTP**: **f9** — f6
  acepta un override de persona por argumento, pero no expone endpoint ni parsea
  el body de la petición.

> **Señal vs prompt (frontera con f8).** f5 expone `below_threshold`; f8 decide
> abstenerse. f6 construye el prompt de generación cuando se le pide; NO consulta
> `below_threshold` para decidir abstención, NI emite el texto "No hay evidencia
> suficiente…" (eso es f8). f6 SÍ instruye al LLM, dentro del prompt, a declarar
> falta de evidencia si el contexto no respalda la respuesta (instrucción de
> grounding), lo cual es distinto del short-circuit de abstención de f8.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Builds a system+user prompt injecting persona/style (simple, Orc, Troll, ...)
> and strict grounding instructions; formats retrieved context with citation
> markers; persona selected by config."

| Fragmento del acceptance                                      | Requisitos que lo cubren        |
|---------------------------------------------------------------|---------------------------------|
| Builds a system+user prompt                                   | R1, R2, R3, R8, R9              |
| injecting persona/style (simple, Orc, Troll, ...)             | R10, R11, R12                   |
| and strict grounding instructions                             | R13, R14, R15, R16              |
| formats retrieved context with citation markers               | R17, R18, R19, R20, R21, R22    |
| persona selected by config                                    | R10, R23, R24                   |

(Requisitos transversales: interfaz `PromptBuilder` R6, R7; modelo `BuiltPrompt`
R1–R5; excepción de dominio R25, R26; entrada inválida R8; exports R27.)

## Requisitos

### Modelo `BuiltPrompt` (salida del constructor)

**R1** — El sistema DEBE definir un modelo `BuiltPrompt` en
`src/wowrag/models.py` con al menos los campos `system: str` (prompt de sistema) y
`user: str` (prompt de usuario).

**R2** — El sistema DEBE que `BuiltPrompt` incluya un campo
`sources: list[Source]`, donde cada `Source` lleva el número de cita `n: int`, el
`title: str` y la `url: str` de la fuente referenciada en el prompt.

**R3** — El sistema DEBE que `BuiltPrompt.system` sea una cadena no vacía tras la
construcción (contiene, como mínimo, el estilo de persona y las instrucciones de
grounding).

**R4** — El sistema DEBE que `BuiltPrompt.user` sea una cadena no vacía tras la
construcción (contiene, como mínimo, la pregunta del usuario y el bloque de
contexto formateado o la indicación explícita de contexto vacío).

**R5** — El sistema DEBE que la numeración de las fuentes en `BuiltPrompt.sources`
(`n = 1, 2, …`) coincida exactamente con los marcadores de cita (`[1], [2], …`)
emitidos en el bloque de contexto del `user` prompt.

### Interfaz `PromptBuilder`

**R6** — El sistema DEBE definir una interfaz `PromptBuilder` (Protocol) en
`src/wowrag/generation/prompt_builder_base.py` con un método
`build(query: str, result: RetrievalResult, persona: Persona | None = None) -> BuiltPrompt`,
como único punto de intercambio para las implementaciones de constructor de prompt.

**R7** — El sistema DEBE que toda implementación de `PromptBuilder` dependa solo de
los tipos `RetrievalResult` / `RetrievedChunk` (de `wowrag.models`), `Persona` (de
`wowrag.personas`) y `Settings` (de `wowrag.config`), sin llamar a ningún
`LLMProvider`, `Retriever`, `VectorStore` ni `EmbeddingProvider`, de modo que sea
construible e invocable en tests sin red, sin GPU y sin Postgres.

### Entrada de la pregunta (query)

**R8** — SI `build` recibe una `query` vacía o compuesta solo de espacios en
blanco, ENTONCES el sistema DEBE lanzar `PromptBuilderError` sin construir el
prompt.

**R9** — CUANDO `build` recibe una `query` no vacía, el sistema DEBE incluir esa
`query` (su texto literal) dentro de `BuiltPrompt.user`.

### Inyección de persona/estilo (seleccionada por config)

**R10** — CUANDO `build` se llama sin `persona` (o con `persona = None`), el
sistema DEBE resolver la persona por defecto desde `Settings.default_persona`
mediante el helper `default_persona()` de f0, y usar su `system_style`.

**R11** — CUANDO `build` se llama con una `Persona` explícita, el sistema DEBE usar
esa persona (ignorando `Settings.default_persona`), de modo que f9 pueda pasar una
persona por petición.

**R12** — El sistema DEBE incluir el `system_style` de la persona resuelta dentro
de `BuiltPrompt.system`, de modo que cambiar de persona (`simple`, `orc`, `troll`,
…) cambie el texto de estilo del prompt de sistema sin tocar código.

### Instrucciones de grounding estricto

**R13** — El sistema DEBE incluir en `BuiltPrompt.system` una instrucción explícita
de que el modelo responda **únicamente** a partir del contexto proporcionado y no
use conocimiento externo.

**R14** — El sistema DEBE incluir en `BuiltPrompt.system` una instrucción explícita
de que, SI el contexto proporcionado no contiene evidencia suficiente para
responder, el modelo DEBE declararlo en lugar de inventar (no alucinar).

**R15** — El sistema DEBE incluir en `BuiltPrompt.system` una instrucción explícita
de que toda afirmación de la respuesta cite sus fuentes mediante los marcadores
numerados (`[1]`, `[2]`, …) del contexto.

**R16** — El sistema DEBE que las instrucciones de grounding (R13, R14, R15) sean
independientes de la persona: cambiar de persona NO elimina ni debilita ninguna de
las tres instrucciones de grounding del `system` prompt.

### Formato del contexto recuperado con marcadores de cita

**R17** — CUANDO `result.chunks` contiene al menos un `RetrievedChunk`, el sistema
DEBE formatear cada chunk en el bloque de contexto del `user` prompt precedido por
un marcador de cita numerado y secuencial empezando en `[1]`, en el mismo orden de
`result.chunks` (score descendente).

**R18** — El sistema DEBE incluir, para cada `RetrievedChunk` formateado, su
`chunk.text` y su `source_url` de wowhead (y, donde esté disponible, su `title`),
asociados a su marcador de cita, de modo que el LLM disponga de la URL para citar.

**R19** — El sistema DEBE que, para cada marcador de cita `[n]` del bloque de
contexto, exista exactamente una entrada `Source(n=n, title=…, url=…)` en
`BuiltPrompt.sources` con la misma `url` (`source_url`) del `RetrievedChunk`
correspondiente.

**R20** — El sistema DEBE NO incluir en el prompt ningún texto, hecho o fuente que
no provenga de los `RetrievedChunk` de `result` (solo-contexto): el bloque de
contexto se deriva exclusivamente de `result.chunks`.

**R21** — CUANDO `result.chunks` está vacío, el sistema DEBE construir igualmente un
`BuiltPrompt` válido cuyo `user` indique explícitamente que no hay contexto
disponible y cuyo `sources` sea una lista vacía, sin lanzar excepción (la decisión
de abstención corresponde a f8, no a f6).

**R22** — El sistema DEBE que el número de entradas en `BuiltPrompt.sources` sea
igual al número de `RetrievedChunk` formateados en el bloque de contexto (una
fuente por chunk citado; cero si el contexto está vacío).

### Selección de persona por configuración

**R23** — El sistema DEBE resolver la persona por defecto a través del campo de
configuración existente `Settings.default_persona` (sin añadir un campo de config
nuevo para la persona).

**R24** — SI la persona configurada en `Settings.default_persona` no existe (no hay
fichero YAML correspondiente), ENTONCES el sistema DEBE dejar propagar
`PersonaNotFoundError` del loader de f0 tal cual, sin enmascararla como un prompt
vacío.

### Excepción de dominio

**R25** — El sistema DEBE definir una excepción de dominio
`PromptBuilderError(Exception)` en
`src/wowrag/generation/prompt_builder_base.py` para los fallos de entrada del
constructor (query vacía).

**R26** — El sistema DEBE NO enmascarar `PersonaNotFoundError` (de la carga de
persona de f0) como `PromptBuilderError` ni como un prompt vacío: ese error de
configuración DEBE propagarse tal cual (coherente con R24).

### Exports del paquete

**R27** — El sistema DEBE re-exportar `PromptBuilder`, `PromptBuilderError` y la
implementación concreta `DefaultPromptBuilder` desde
`src/wowrag/generation/__init__.py`, y re-exportar `BuiltPrompt` y `Source` desde
`src/wowrag/models.py` (vía su `__all__`), de modo que los consumidores (f8/f9)
dependan del paquete/módulo de modelos, no de los módulos internos.
