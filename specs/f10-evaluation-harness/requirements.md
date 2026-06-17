# Requirements — f10-evaluation-harness

> Feature: `f10-evaluation-harness` — Evaluation harness (golden Q&A,
> faithfulness, abstention). Define un **dataset dorado** de preguntas, calcula
> **métricas** (hit-rate de recuperación, faithfulness/groundedness de la
> respuesta, abstención correcta sobre preguntas fuera-de-corpus) y produce un
> **reporte ejecutable** (script + artefacto). f10 EVALÚA el pipeline; consume el
> `RagOrchestrator` de f8 por su interfaz y NO reimplementa recuperación,
> prompting ni generación.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. Un **esquema de dataset dorado** (modelos pydantic en `src/wowrag/eval/`): cada
   item lleva una `question`, las `expected_urls` esperadas (para hit-rate), un
   flag `in_corpus: bool` (preguntas fuera-de-corpus deben abstenerse) y una
   `reference_answer` opcional (para faithfulness). Un **fixture commiteado**
   pequeño (`src/wowrag/eval/data/golden.jsonl`) con casos in-corpus y
   fuera-de-corpus para que la suite por defecto corra con datos reales.
2. Un **loader** del dataset (`load_golden`) que lee el fichero JSONL, valida cada
   item contra el esquema y rechaza con error claro los items malformados.
3. Tres **métricas**, cada una definida con su fórmula exacta y computables como
   funciones puras sobre los `Answer` ya producidos (sin red):
   - **Retrieval hit-rate** sobre los items in-corpus (¿la URL esperada aparece en
     las `Answer.sources`?).
   - **Faithfulness / groundedness** por defecto = **proxy determinista**
     (presencia de cita + solapamiento léxico de la respuesta contra el contexto
     citado / la respuesta de referencia), sin LLM. Opcionalmente, un
     **juez-LLM** pluggable reutilizando el `LLMProvider` de f7, fakeable en tests
     y gated tras `@pytest.mark.integration` para el modelo real.
   - **Abstención correcta** sobre los items etiquetados: precisión y recall de la
     abstención (un item fuera-de-corpus DEBE producir `Answer.abstained == True`).
4. Un **runner** (`EvalHarness`) que, dado un `RagOrchestrator` (f8) y un dataset,
   ejecuta cada pregunta y agrega las tres métricas en un **reporte estructurado**
   (`EvalReport`, modelo pydantic).
5. Un **entrypoint CLI / script** (`python -m wowrag.eval`) que construye el
   orquestador real (composición perezosa, reutilizando `build_orchestrator` de
   f9), corre el dataset y emite el reporte: resumen a stdout y, opcionalmente, un
   artefacto JSON. Toda la composición pesada (bge-m3 / pgvector / Ollama) es
   **perezosa** (imports dentro de función), de modo que importar `wowrag.eval` en
   tests NO arrastra torch / psycopg / el cliente HTTP.
6. La **reutilización** del `RagOrchestrator` (f8), de `Answer`/`Source`/
   `AnswerMetadata` (f8/f6) y de `Settings`/`LLMProvider` (f0/f7). f10 NO modifica
   f5–f9 ni `config.py` salvo, como mucho, añadir ajustes de eval nuevos y
   opcionales (ver R28); CONSUME los interfaces públicos.

> **Modelos nuevos de f10 viven en `src/wowrag/eval/`, no en `models.py`.** A
> diferencia de `Answer`/`BuiltPrompt` (modelos de datos del pipeline, en
> `models.py`), los modelos de f10 (`GoldenItem`, `EvalReport`, métricas) son del
> arnés de evaluación y viven en su propio paquete `eval/`, igual que `index/`
> alberga el `IndexingPipeline` fuera de `models.py`.

### Fuera de alcance (explícito)

f10 es **nivel librería + script**: evalúa el pipeline y produce un reporte. NO
introduce HTTP, NO escrapea, NO reordena, NO cambia la lógica de f5–f9.
Concretamente, queda fuera de alcance:

- **Construir un corpus real / scraping de wowhead**: es **f11**. Hasta f11 NO hay
  corpus real; el camino testeable por defecto usa **fakes/fixtures** (un
  `RagOrchestrator` fake o stub que devuelve `Answer` deterministas), NO una BD
  poblada. El runner contra el pipeline real (pgvector + bge-m3 + Ollama) existe
  pero queda **gated tras `@pytest.mark.integration`** y fuera de `./init.sh`.
- **Reranking** (f12) y **cambiar la lógica de f5–f9**: f10 SOLO consume sus
  interfaces públicas (`RagOrchestrator.answer`, `Answer`, `Source`).
- **Nuevo endpoint HTTP** (`POST /eval` u otro): es territorio de f9; f10 es un
  script/librería, NO una ruta de la API.
- **Faithfulness "real" (juez-LLM) como camino por defecto**: el camino por
  defecto, unitario y determinista es el **proxy** (R12–R14); el juez-LLM es
  **opcional** y, contra Ollama real, **`@integration`** (R15–R17). Importar
  `wowrag.eval` NO debe requerir ni contactar a Ollama.
- **Métricas de calidad lingüística avanzadas** (BLEU/ROUGE/embeddings de
  similitud semántica como dependencias pesadas): el proxy por defecto usa solo
  stdlib (solapamiento léxico de tokens). No se añaden dependencias pesadas al
  camino por defecto.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Golden Q&A dataset; metrics for retrieval hit-rate, answer
> faithfulness/groundedness, and correct abstention on out-of-corpus questions;
> runnable as a script/report."

| Fragmento del acceptance                                | Requisitos que lo cubren                |
|---------------------------------------------------------|-----------------------------------------|
| Golden Q&A dataset                                      | R1, R2, R3, R4, R5                       |
| metrics for retrieval hit-rate                          | R8, R9, R10, R11                        |
| answer faithfulness/groundedness                        | R12, R13, R14 (proxy); R15, R16, R17 (juez-LLM) |
| correct abstention on out-of-corpus questions           | R18, R19, R20, R21                      |
| runnable as a script/report                             | R22, R23, R24, R25, R26                 |

(Requisitos transversales: runner/composición por DI R6, R7; reutilización de
f8/config R27, R28; fakes/network-free R29; exports R30.)

## Requisitos

### Dataset dorado: esquema, loader y fixture

**R1** — El sistema DEBE definir un modelo `GoldenItem` (pydantic) en
`src/wowrag/eval/` con al menos los campos `question: str` (no vacío),
`expected_urls: list[str]` (URLs de fuente esperadas, posiblemente vacía),
`in_corpus: bool` (True = la respuesta está en el corpus; False = fuera-de-corpus,
debe abstenerse) y `reference_answer: str | None` (respuesta de referencia
opcional para faithfulness).

**R2** — SI un `GoldenItem` tiene `in_corpus = true` pero `expected_urls` está
vacío, ENTONCES el sistema DEBE rechazarlo con un error de validación claro
(un item in-corpus sin fuente esperada no es evaluable para hit-rate).

**R3** — SI un `GoldenItem` tiene `in_corpus = false` y `expected_urls` no está
vacío, ENTONCES el sistema DEBE rechazarlo con un error de validación claro
(una pregunta fuera-de-corpus no puede declarar fuentes esperadas).

**R4** — El sistema DEBE proporcionar un loader `load_golden(path)` que lea un
fichero JSONL (un `GoldenItem` por línea), valide cada línea contra el esquema y
devuelva una `list[GoldenItem]`; SI una línea está malformada o vacía de
contenido evaluable, ENTONCES DEBE elevar un error claro que identifique la línea
ofensora (no la silencia ni la salta).

**R5** — El sistema DEBE commitear un fichero de dataset dorado de ejemplo en
`src/wowrag/eval/data/golden.jsonl` que contenga al menos un item `in_corpus=true`
(con `expected_urls`) y al menos un item `in_corpus=false` (fuera-de-corpus), de
modo que la suite por defecto pueda cargarlo y validarlo con datos reales.

### Runner del arnés (composición por DI)

**R6** — El sistema DEBE definir un runner `EvalHarness` que reciba un
`RagOrchestrator` (la interfaz de f8) por inyección en el constructor, de modo que
sea construible e invocable en tests con un orquestador fake/stub, sin Postgres,
sin GPU, sin Ollama, sin red.

**R7** — CUANDO `EvalHarness` evalúa un dataset, el sistema DEBE invocar
`RagOrchestrator.answer(item.question)` exactamente una vez por `GoldenItem` y
conservar el `Answer` resultante para el cálculo de métricas, sin reordenar ni
mutar el `Answer` devuelto por f8.

### Métrica 1 — Retrieval hit-rate

**R8** — El sistema DEBE computar el **hit-rate de recuperación** SOLO sobre los
items con `in_corpus = true`, definido como la fracción de esos items para los que
al menos una de sus `expected_urls` aparece entre las URLs de `Answer.sources`
(`hit-rate = items_con_hit / items_in_corpus`).

**R9** — El sistema DEBE considerar que un item in-corpus tiene "hit" CUANDO la
intersección entre el conjunto de `item.expected_urls` y el conjunto de
`{s.url for s in answer.sources}` es no vacía (comparación exacta de URL).

**R10** — SI no hay ningún item `in_corpus = true` en el dataset, ENTONCES el
sistema DEBE reportar el hit-rate como `None` (o equivalente "no aplicable") en
lugar de dividir por cero.

**R11** — El sistema DEBE derivar el hit-rate exclusivamente de las
`Answer.sources` devueltas por el orquestador (f8), sin re-ejecutar la
recuperación ni re-embeber.

### Métrica 2 — Faithfulness / groundedness

**R12** — El sistema DEBE computar, por defecto, una **métrica proxy determinista
de faithfulness** que NO requiera ningún LLM ni red, computable como función pura
sobre el `Answer` (y, si existe, su `reference_answer`).

**R13** — El sistema DEBE definir el proxy de faithfulness de un item no-abstenido
como la combinación de (a) **presencia de cita**: el `Answer` no-abstenido tiene
al menos una `Source`; y (b) **solapamiento léxico**: la fracción de tokens de la
respuesta de referencia (`reference_answer`) cubiertos por la respuesta generada
(`Answer.answer`), o, si no hay `reference_answer`, la fracción de tokens de la
respuesta presentes en el material citado disponible — con la fórmula exacta y la
normalización (minúsculas, tokenización por palabras, stopwords descartables)
documentadas en `design.md`.

**R14** — SI un `Answer` está abstenido (`abstained = true`), ENTONCES el sistema
DEBE excluirlo del cálculo del faithfulness proxy (la faithfulness se mide solo
sobre respuestas fundamentadas; la corrección de la abstención la mide la métrica
3), y el reporte DEBE indicar cuántos items se excluyeron por abstención.

**R15** — DONDE se configura un **juez-LLM** opcional, el sistema DEBE permitir
inyectar un `LLMProvider` (interfaz de f7) que puntúe la faithfulness de cada
respuesta no-abstenida frente a su contexto/referencia, devolviendo una
puntuación normalizada en `[0, 1]`.

**R16** — El sistema DEBE que el juez-LLM sea **opcional y desacoplado del camino
por defecto**: si no se inyecta un juez, el reporte usa solo el proxy determinista
(R12–R14); importar `wowrag.eval` NUNCA debe instanciar ni contactar a Ollama.

**R17** — El sistema DEBE que el juez-LLM sea testeable con un `LLMProvider` fake
(determinista, sin red); SOLO la variante contra un Ollama real se marca
`@pytest.mark.integration` y queda fuera de `./init.sh`.

### Métrica 3 — Abstención correcta (fuera-de-corpus)

**R18** — El sistema DEBE evaluar la **corrección de la abstención** sobre los
items etiquetados: un item con `in_corpus = false` se considera correcto CUANDO su
`Answer.abstained` es `true`; un item con `in_corpus = true` se considera correcto
CUANDO su `Answer.abstained` es `false`.

**R19** — El sistema DEBE computar la **precisión de abstención** = (items
fuera-de-corpus correctamente abstenidos) / (todos los items en los que el sistema
se abstuvo), y la **recall de abstención** = (items fuera-de-corpus correctamente
abstenidos) / (todos los items fuera-de-corpus), con las fórmulas documentadas en
`design.md`.

**R20** — SI no hay items `in_corpus = false` en el dataset, ENTONCES el sistema
DEBE reportar la recall de abstención como `None` (no aplicable) en lugar de
dividir por cero; análogamente para la precisión cuando no hubo ninguna
abstención.

**R21** — El sistema DEBE derivar la métrica de abstención exclusivamente de la
bandera `Answer.abstained` devuelta por f8, sin recalcular el umbral de score ni
inspeccionar la lógica interna del orquestador.

### Reporte y entrypoint CLI / script

**R22** — El sistema DEBE definir un modelo de reporte `EvalReport` (pydantic) que
agregue, como mínimo: el número total de items evaluados, el hit-rate de
recuperación (o `None`), la faithfulness proxy media (y, si se usó, la del
juez-LLM), la precisión y recall de abstención (o `None`), y el conteo de items
in-corpus / fuera-de-corpus / excluidos por abstención.

**R23** — El sistema DEBE que `EvalReport` sea serializable a JSON (estable, vía
pydantic), de modo que el reporte pueda persistirse como artefacto y consumirse
por herramientas externas.

**R24** — El sistema DEBE proporcionar un entrypoint ejecutable como
`python -m wowrag.eval` que cargue el dataset dorado (por defecto el fixture
commiteado, configurable por argumento/ruta), ejecute el `EvalHarness` contra un
`RagOrchestrator` y emita un resumen legible del `EvalReport` por stdout.

**R25** — DONDE se solicita un artefacto de salida (p. ej. una ruta `--out`), el
entrypoint DEBE escribir el `EvalReport` serializado a JSON en esa ruta, además
del resumen por stdout.

**R26** — El sistema DEBE que el entrypoint construya el orquestador real
(bge-m3 + pgvector + Ollama) mediante **composición perezosa** (imports dentro de
la función de composición, reutilizando `build_orchestrator` de f9), de modo que
importar `wowrag.eval` NO arrastre torch / psycopg / el cliente HTTP ni contacte
servicios; las dependencias pesadas se resuelven SOLO al ejecutar el script.

### Reutilización de f8 / config y fronteras

**R27** — El sistema DEBE reutilizar el `RagOrchestrator` (f8), `Answer` /
`Source` / `AnswerMetadata` (f8/f6) y `LLMProvider` (f7) por sus interfaces
públicas, sin reimplementar recuperación, prompting ni generación, y sin modificar
f5–f9.

**R28** — El sistema DEBE NO modificar las claves de configuración existentes de
`Settings`; DONDE f10 necesite ajustes nuevos (p. ej. ruta del dataset por
defecto), DEBE añadirlos como campos nuevos con valor por defecto sano, sin alterar
los existentes ni requerir variables de entorno para el camino por defecto.

**R29** — El sistema DEBE que todo el camino por defecto del arnés (esquema,
loader, las tres métricas, el runner, el reporte) sea computable y testeable con
**fakes** (un `RagOrchestrator` fake/stub y, para el juez, un `LLMProvider` fake),
sin Postgres, sin GPU, sin Ollama, sin red, de modo que corra bajo `./init.sh`
(`pytest -m "not integration"`).

### Exports del paquete

**R30** — El sistema DEBE re-exportar desde `src/wowrag/eval/__init__.py` los
símbolos públicos del arnés (`GoldenItem`, `load_golden`, `EvalHarness`,
`EvalReport`, y las funciones de métricas públicas), de modo que los consumidores
importen del paquete `wowrag.eval`, no de sus módulos internos.
