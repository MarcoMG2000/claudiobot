# Requirements — f8-rag-orchestrator

> Feature: `f8-rag-orchestrator` — RAG orchestrator + abstention logic. Une
> `retrieve → prompt → generate`; se abstiene con un mensaje claro cuando la
> recuperación queda por debajo del umbral; devuelve respuesta + citas + metadata
> (modelo, persona, scores).
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. El modelo **`Answer`** en `src/wowrag/models.py` — la respuesta estructurada
   final del pipeline RAG: texto de respuesta, citas (`sources: list[Source]`),
   bandera `abstained: bool` y `metadata` (modelo, persona, scores). Es el tipo de
   retorno que f9 (HTTP API) serializará a JSON.
2. La **interfaz `RagOrchestrator`** (Protocol swappable) y la **excepción de
   dominio `OrchestratorError`** en `src/wowrag/rag/base.py`: el punto de
   intercambio que toda implementación de orquestador debe satisfacer.
3. La **implementación `DefaultRagOrchestrator`** en
   `src/wowrag/rag/orchestrator.py` — que COMPONE, por inyección de dependencias,
   un `Retriever` (f5), un `PromptBuilder` (f6) y un `LLMProvider` (f7), aplicando
   la lógica de short-circuit de abstención. Testeable con fakes/stubs de las tres
   dependencias (sin Postgres, sin GPU, sin Ollama, sin red).
4. La **lógica de abstención** (propiedad nº1 del proyecto): cuando la señal
   `RetrievalResult.below_threshold` es `true`, el orquestador NO llama al LLM,
   pone `abstained = true` y devuelve un **mensaje de abstención claro**.
5. El **mensaje de abstención** — f8 lo OWNS (f5 solo expuso la señal `bool`).
6. La **reutilización** de la configuración existente de `Settings`
   (`top_k`, `score_threshold`, `default_persona`, `ollama_url`, `llm_model`) y de
   las personas de f0. f8 NO redefine config ni reimplementa f5/f6/f7.

> **`Answer` diferido a f8:** el docstring de `models.py` ya anticipa `Answer`
> ("``Answer`` will be added by a later feature"). f8 es esa feature. `models.py`
> SÍ se toca en f8 (añade `Answer`), igual que f5 añadió `RetrievalResult` y f6
> añadió `BuiltPrompt`.

### Fuera de alcance (explícito)

f8 es **nivel librería**: orquesta el pipeline y produce un `Answer`. NO expone
HTTP, NO escrapea, NO reordena. Concretamente, queda fuera de alcance:

- **HTTP API / FastAPI** (`POST /ask`, `/health`, CORS, persona por petición en el
  body): **f9** — f9 envolverá el `RagOrchestrator` y serializará `Answer` a JSON.
- **Streaming / async** (`generate_stream`, endpoints async): diferido a **f9**.
  f8 es **síncrono** y usa solo `LLMProvider.generate` (f7).
- **Eval harness** (golden Q&A, faithfulness, hit-rate, abstención correcta como
  métrica): **f10** — f10 invocará al orquestador como sujeto de prueba.
- **Scraping de wowhead**: **f11**.
- **Reranking** (reordenar top-k antes de generar): **f12**, se intercalará entre
  `retrieve` y `build`.
- **Reimplementar** recuperación (f5), prompt building (f6) o el provider LLM (f7):
  f8 los CONSUME por interfaz, no los reescribe.
- **Producir el mensaje de abstención en f5/f6/f7**: f5 solo expuso la señal
  `below_threshold`; f6 deja `sources=[]` con contexto vacío pero NO abstiene; f7
  no decide nada. El mensaje y el short-circuit son de f8.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Ties retrieve -> prompt -> generate; abstains with a clear message when
> retrieval is below threshold; returns answer + source citations + metadata
> (model, persona, scores)."

| Fragmento del acceptance                              | Requisitos que lo cubren            |
|-------------------------------------------------------|-------------------------------------|
| Ties retrieve -> prompt -> generate                   | R8, R9, R10, R11, R12, R13          |
| abstains with a clear message                         | R14, R15, R16, R17, R18             |
| when retrieval is below threshold                     | R14, R15                            |
| returns answer                                        | R1, R2, R13                         |
| + source citations                                    | R3, R12, R19, R20                   |
| + metadata (model, persona, scores)                   | R4, R5, R6, R7, R21                  |

(Requisitos transversales: interfaz `RagOrchestrator` R8, R22; composición por DI
R9, R23; excepción de dominio / entrada inválida R24, R25; reutilización de config
R26; exports R27.)

## Requisitos

### Modelo `Answer` (respuesta estructurada final)

**R1** — El sistema DEBE definir un modelo `Answer` en `src/wowrag/models.py` con
al menos los campos `answer: str`, `sources: list[Source]`, `abstained: bool` y
`metadata` (un objeto/diccionario de metadata de respuesta).

**R2** — El sistema DEBE que, en una respuesta **no-abstenida**, `Answer.answer`
contenga exactamente el texto devuelto por `LLMProvider.generate`, sin recortar ni
reescribir el contenido del LLM.

**R3** — El sistema DEBE que `Answer.sources` reutilice el tipo `Source` de f6
(`{n, title, url}`), de modo que las citas tengan el mismo formato estable que
produce el `PromptBuilder`.

**R4** — El sistema DEBE que la `metadata` de `Answer` incluya el nombre del
**modelo** LLM (el valor de `LLMProvider.model`).

**R5** — El sistema DEBE que la `metadata` de `Answer` incluya el nombre de la
**persona** efectivamente usada para construir el prompt.

**R6** — El sistema DEBE que la `metadata` de `Answer` incluya el **`max_score`**
de la recuperación (el mejor score, o `0.0` si no hubo chunks).

**R7** — El sistema DEBE que la `metadata` de `Answer` incluya los **scores por
fuente** de los chunks recuperados (alineados con las citas `[n]`), además de
`max_score`.

### Interfaz `RagOrchestrator`

**R8** — El sistema DEBE definir una interfaz `RagOrchestrator` (Protocol) en
`src/wowrag/rag/base.py` con un método `answer(query: str, persona: Persona | None
= None) -> Answer`, como único punto de intercambio para las implementaciones de
orquestador.

**R9** — El sistema DEBE que toda implementación de `RagOrchestrator` dependa solo
de las interfaces `Retriever`, `PromptBuilder` y `LLMProvider` (no de
implementaciones concretas), de modo que sea construible e invocable en tests con
fakes/stubs de las tres, sin Postgres, sin GPU, sin Ollama, sin red.

### Flujo feliz: retrieve → prompt → generate

**R10** — CUANDO `answer` recibe una `query` no vacía, el sistema DEBE primero
llamar a `Retriever.retrieve(query)` para obtener un `RetrievalResult`.

**R11** — MIENTRAS `RetrievalResult.below_threshold` es `false`, el sistema DEBE
llamar a `PromptBuilder.build(query, result, persona)` para obtener un
`BuiltPrompt`, pasando la persona resuelta.

**R12** — CUANDO ha construido el `BuiltPrompt`, el sistema DEBE componer su
`system` y su `user` en un único prompt string y llamar a
`LLMProvider.generate(prompt)` exactamente una vez para obtener el texto de
respuesta.

**R13** — CUANDO `LLMProvider.generate` devuelve texto, el sistema DEBE construir y
devolver un `Answer` con `abstained = false`, `answer` = ese texto, `sources` =
`BuiltPrompt.sources` y la metadata correspondiente (modelo, persona, scores).

### Abstención (short-circuit del LLM) — propiedad nº1

**R14** — SI `RetrievalResult.below_threshold` es `true`, ENTONCES el sistema DEBE
abstenerse: NO llamar al `PromptBuilder` ni al `LLMProvider`, y devolver un
`Answer` con `abstained = true`.

**R15** — CUANDO el sistema se abstiene, el `Answer.answer` DEBE contener un
**mensaje de abstención claro** indicando que no hay evidencia suficiente en los
documentos para responder con seguridad (p. ej. "No hay evidencia suficiente en
los documentos para responder con seguridad.").

**R16** — CUANDO el sistema se abstiene, el `Answer.sources` DEBE ser una lista
vacía (`[]`), porque no se ha usado contexto para fundamentar una respuesta.

**R17** — CUANDO el sistema se abstiene, la `metadata` del `Answer` DEBE seguir
incluyendo el `max_score` de la recuperación (típicamente por debajo del umbral) y
el nombre de la persona resuelta, para diagnóstico.

**R18** — El sistema DEBE que el mensaje de abstención sea propio de f8 (no
delegado a f5/f6/f7); la decisión de abstener se toma a partir de la señal
`below_threshold` de f5, sin recalcular el umbral.

### Citas siempre presentes en respuestas fundamentadas

**R19** — CUANDO el sistema NO se abstiene, el `Answer.sources` DEBE contener al
menos una `Source` siempre que el `BuiltPrompt` haya numerado al menos una fuente
(es decir, las respuestas fundamentadas devuelven citas).

**R20** — El sistema DEBE que las `Source` devueltas en `Answer.sources` sean
exactamente las `sources` del `BuiltPrompt` producido por f6 (mismo `n`, `title`,
`url`), sin reconstruirlas ni reordenarlas.

### Metadata de scores

**R21** — El sistema DEBE derivar los scores de la metadata (`max_score` y scores
por fuente) del `RetrievalResult` devuelto por f5, sin recalcularlos ni
re-embeber.

### Composición y reutilización

**R22** — El sistema DEBE que `DefaultRagOrchestrator` reciba sus tres
dependencias (`Retriever`, `PromptBuilder`, `LLMProvider`) por inyección en el
constructor, y opcionalmente un `Settings`, sin instanciar internamente ninguna
implementación concreta de red/DB/ML.

**R23** — CUANDO `answer` se llama sin `persona` (o con `persona = None`), el
sistema DEBE resolver la persona efectiva de forma consistente con f6 (delegando
en `PromptBuilder.build`, que cae a `Settings.default_persona`), y reportar en la
metadata el nombre de esa persona resuelta.

### Excepción de dominio y entrada inválida

**R24** — El sistema DEBE definir una excepción de dominio
`OrchestratorError(Exception)` en `src/wowrag/rag/base.py` para los fallos de
entrada del orquestador (query vacía).

**R25** — SI `answer` recibe una `query` vacía o compuesta solo de espacios en
blanco, ENTONCES el sistema DEBE lanzar `OrchestratorError` sin llamar al
`Retriever`, al `PromptBuilder` ni al `LLMProvider`.

**R26** — El sistema DEBE NO enmascarar errores de infraestructura propagados por
las capas inferiores: si el `Retriever` lanza (p. ej. `RetrieverError`,
`EmbeddingError`, `VectorStoreError`) o el `LLMProvider` lanza `LLMError`, el
orquestador DEBE dejar propagar esa excepción tal cual (no convertirla en un
`Answer` vacío ni silenciarla, salvo la abstención que es respuesta válida).

### Exports del paquete

**R27** — El sistema DEBE re-exportar `RagOrchestrator`, `OrchestratorError` y la
implementación concreta `DefaultRagOrchestrator` desde
`src/wowrag/rag/__init__.py`, y re-exportar `Answer` desde `src/wowrag/models.py`
(vía su `__all__`), de modo que los consumidores (f9) dependan del paquete/módulo
de modelos, no de los módulos internos.
