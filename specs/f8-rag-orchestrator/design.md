# Design — f8-rag-orchestrator

> CÓMO se construye la capa de orquestación (online query path, el paso que une
> todo). Respeta el layout de `docs/architecture.md` §6 (`src/wowrag/rag/
> orchestrator.py`) y las convenciones del proyecto: interfaz en `base.py`,
> implementación concreta aparte, excepción de dominio, `from __future__ import
> annotations`, dependencia SOLO de interfaces (Protocols). Sigue el patrón ya
> establecido en f3 (`EmbeddingProvider`), f4 (`VectorStore`), f5 (`Retriever`),
> f6 (`PromptBuilder`) y f7 (`LLMProvider`). Consume f5/f6/f7 por inyección.

## 0. Decisión de entrega: PR único (~≤ 320 líneas)

f8 es comparable en tamaño a f6/f7: 1 modelo pydantic (`Answer` + un submodelo de
metadata), 1 interfaz + excepción, 1 implementación que **solo compone** tres
dependencias inyectadas (sin red, sin DB, sin ML), exports y sus tests unitarios.
**No hay driver pesado, ni migración SQL, ni servicios reales** (los tests usan
`FakeLLMProvider` de f7 + fakes/stubs de `Retriever`/`PromptBuilder`, o las impls
reales de f5/f6 alimentadas con `FakeEmbeddingProvider`/`FakeVectorStore`). La fase
de apply **cabe holgadamente en un PR único dentro del presupuesto de ~400 líneas**.

Estimación de líneas cambiadas (apply):

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `models.py` (`Answer` + `AnswerMetadata` + `__all__`) | ~40 |
| `rag/base.py` (Protocol `RagOrchestrator` + `OrchestratorError`) | ~45 |
| `rag/orchestrator.py` (`DefaultRagOrchestrator`) | ~85 |
| `rag/__init__.py` (re-exports) | ~10 |
| `tests/test_models_answer.py` | ~45 |
| `tests/test_orchestrator.py` (flujo feliz + abstención + errores) | ~115 |
| **Total estimado** | **~340 líneas** — por debajo de 400. |

**Recomendación: PR único.** No se necesitan slices encadenados. La numeración
`R<n>` es estable independientemente de esta decisión.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py                  # EDITAR — añadir Answer (+ AnswerMetadata) (+ __all__)
    rag/
      __init__.py              # NUEVO/EDITAR — re-exportar RagOrchestrator, OrchestratorError, DefaultRagOrchestrator
      base.py                  # NUEVO — RagOrchestrator (Protocol) + OrchestratorError
      orchestrator.py          # NUEVO — DefaultRagOrchestrator (compone Retriever + PromptBuilder + LLMProvider)
tests/
  test_models_answer.py        # NUEVO — Answer + AnswerMetadata (modelos)
  test_orchestrator.py         # NUEVO — DefaultRagOrchestrator con fakes (flujo feliz, abstención, errores)
```

Notas:
- `src/wowrag/rag/` está previsto en `docs/architecture.md` §6
  (`rag/orchestrator.py # une todo + abstención`). Si el paquete `rag/` aún no
  existe como placeholder de f0, se crea con su `__init__.py`. Se añade `base.py`
  para la interfaz (mismo patrón `base.py` que `retrieval/`, `store/`, `llm/`).
- `models.py` SÍ se edita en f8: añade `Answer` (y `AnswerMetadata`). El docstring
  de `models.py` ya anticipa `Answer` ("will be added by a later feature").
- **`config.py` NO se edita.** `top_k`, `score_threshold`, `default_persona`,
  `ollama_url`, `llm_model` YA existen en `Settings` (f0). f8 solo los reutiliza
  indirectamente a través de f5/f6/f7, que ya los consumen (R26). f8 no lee config
  de scores/umbral directamente: la decisión de abstención usa la señal
  `below_threshold` que f5 ya computó (R18, R21).

## 2. Ubicación del módulo: `src/wowrag/rag/` (capa de orquestación, online)

Decisión: el orquestador vive en **`src/wowrag/rag/`**, NO en `retrieval/` ni
`generation/`.

Justificación según `docs/architecture.md` §3 y §6:
- El diagrama de flujo §3 sitúa la **orquestación** como el paso que une
  `retriever → prompt builder → LLM → abstención/respuesta`. §6 reserva
  explícitamente `rag/orchestrator.py # une todo + abstención` para esta capa.
- f5 vive en `retrieval/`, f6/f7 en `generation/`/`llm/`. Cada uno es un paso; f8
  es el **coordinador**. Meter la orquestación en cualquiera de esas capas
  mezclaría responsabilidades; el revisor rechaza mezcla de capas.
- **Espacio para f9 (HTTP API):** `api/app.py` (f9) construirá un
  `DefaultRagOrchestrator` y llamará a `answer()`. Mantener f8 como librería pura
  (sin FastAPI) deja a f9 envolverlo sin acoplar HTTP a la lógica RAG.

## 3. Modelo `Answer` y `AnswerMetadata` (R1–R7)

### Decisión: `Answer` en `models.py` (no módulo aparte)

`Answer` vive en `src/wowrag/models.py`, junto a `Document`, `Chunk`,
`RetrievedChunk`, `RetrievalResult`, `Source`, `BuiltPrompt`. Razones:

- **Convención del proyecto.** `models.py` es "the single home for all data-layer
  pydantic models" (su propio docstring), y su docstring YA nombra `Answer` como
  pendiente. f5 puso ahí `RetrievalResult`; f6 puso ahí `Source`/`BuiltPrompt`.
  Un módulo aparte rompería esa convención y duplicaría el patrón de import.
- **Reutiliza `Source`.** `Answer.sources: list[Source]` referencia el `Source` ya
  definido en `models.py` (f6); tenerlos juntos evita un import circular o cruzado.

### Decisión: metadata como submodelo `AnswerMetadata` (no dict suelto)

La `metadata` se modela como un **submodelo pydantic `AnswerMetadata`** con campos
tipados, no como un `dict[str, Any]` opaco. Razones:

- **Tipado y validación** (convención: type hints obligatorios; `docs/conventions
  .md`). f9 serializará `Answer` a JSON; un submodelo da un esquema estable y
  autodescriptivo a la API y al frontend futuro.
- **Trazabilidad de R4–R7.** Cada campo es un requisito verificable por test, no un
  `dict` con claves mágicas.

```python
class AnswerMetadata(BaseModel):
    """Metadata de diagnóstico de una respuesta RAG.

    Incluye el modelo LLM, la persona usada y los scores de recuperación.
    f9 la serializa a JSON en la respuesta de la API.
    """

    model: str               # nombre del modelo LLM (LLMProvider.model) (R4)
    persona: str             # nombre de la persona resuelta (R5)
    max_score: float         # mejor score de recuperación, 0.0 si vacío (R6)
    scores: list[float]      # scores por fuente, alineados con sources [n] (R7)


class Answer(BaseModel):
    """Respuesta estructurada final del pipeline RAG (f8).

    abstained=True -> answer es el mensaje de abstención y sources=[] (R14-R16).
    abstained=False -> answer es el texto del LLM y sources son las citas (R2, R19).
    f9 la serializa a JSON: {answer, sources, abstained, metadata}.
    """

    answer: str                      # texto del LLM, o mensaje de abstención (R2, R15)
    sources: list[Source]            # citas [n]; [] si abstención (R3, R16, R19, R20)
    abstained: bool                  # True si se abstuvo por below_threshold (R14)
    metadata: AnswerMetadata         # modelo, persona, scores (R4-R7, R17)
```

> **`abstained` modelada en el tipo de retorno, no como excepción** (regla de
> `docs/conventions.md`: "la abstención es una respuesta válida, no una
> excepción"). f8 NUNCA lanza por abstención; lanza solo por entrada inválida
> (`OrchestratorError`, R24/R25) o deja propagar errores de infra (R26).

## 4. Interfaz `RagOrchestrator` y excepción (R8, R9, R24)

`src/wowrag/rag/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from wowrag.models import Answer
from wowrag.personas import Persona


class OrchestratorError(Exception):
    """Domain exception for orchestrator input failures.

    Raised for an empty/whitespace query, BEFORE touching retriever/prompt/LLM.
    Infra errors from lower layers (RetrieverError, EmbeddingError,
    VectorStoreError, LLMError) are NOT wrapped: they propagate as-is (R26).
    Abstention is a valid Answer, never an exception.
    """


class RagOrchestrator(Protocol):
    """Swap point: query -> (retrieve -> [abstain] -> prompt -> generate) -> Answer.

    Concrete implementation: DefaultRagOrchestrator (composes Retriever +
    PromptBuilder + LLMProvider). Callers (f9) depend on this Protocol, never
    on a concrete impl.

    Contract:
    - Empty/whitespace query -> OrchestratorError (no retrieve/prompt/LLM call).
    - below_threshold == True -> abstain: Answer(abstained=True, sources=[]),
      no PromptBuilder/LLMProvider call (R14).
    - below_threshold == False -> build prompt + generate; Answer(abstained=False)
      with sources = BuiltPrompt.sources (R13, R19, R20).
    - Infra errors propagate unmasked (R26).
    """

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        """Run the RAG pipeline for a query and return a structured Answer.

        persona=None -> resolved via the PromptBuilder (Settings.default_persona).
        Empty query -> OrchestratorError.
        """
        ...
```

## 5. Implementación `DefaultRagOrchestrator` (R9–R26)

`src/wowrag/rag/orchestrator.py` — compone por inyección de dependencias; sin
imports de DB/ML/red. La decisión de abstención usa la señal `below_threshold` de
f5 (no recalcula umbral). El mensaje de abstención es una constante de módulo
(propiedad de f8).

```python
from __future__ import annotations

from wowrag.config import Settings
from wowrag.generation.prompt_builder_base import PromptBuilder
from wowrag.llm.base import LLMProvider
from wowrag.models import Answer, AnswerMetadata, RetrievalResult
from wowrag.personas import Persona
from wowrag.rag.base import OrchestratorError
from wowrag.retrieval.base import Retriever

# Mensaje de abstención — propiedad de f8 (f5 solo expuso la señal). (R15, R18)
_ABSTENTION_MESSAGE = (
    "No hay evidencia suficiente en los documentos para responder con seguridad."
)


class DefaultRagOrchestrator:
    """Orquestador que compone Retriever + PromptBuilder + LLMProvider.

    Depende solo de las interfaces (R9, R22): testeable con fakes/stubs de las
    tres dependencias, sin Postgres, sin GPU, sin Ollama, sin red.
    """

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm: LLMProvider,
        settings: Settings | None = None,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm = llm
        self._settings = settings or Settings()

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        # R25: validar query ANTES de tocar ninguna dependencia.
        if not query or not query.strip():
            raise OrchestratorError("query must be a non-empty string")

        # R10: recuperar. Errores de infra (RetrieverError/Embedding/Store) propagan (R26).
        result: RetrievalResult = self._retriever.retrieve(query)

        # R21: scores derivados del RetrievalResult (sin recalcular).
        scores = [rc.score for rc in result.chunks]

        # R14: short-circuit del LLM si la señal de abstención está activa.
        if result.below_threshold:
            return Answer(
                answer=_ABSTENTION_MESSAGE,                       # R15
                sources=[],                                       # R16
                abstained=True,                                   # R14
                metadata=AnswerMetadata(
                    model=self._llm.model,                        # R4
                    persona=self._resolve_persona_name(persona),  # R5, R17, R23
                    max_score=result.max_score,                   # R6, R17
                    scores=scores,                                # R7
                ),
            )

        # R11: construir prompt. PersonaNotFoundError de f6/f0 propaga (R26).
        built = self._prompt_builder.build(query, result, persona)

        # R12: componer system+user en un único prompt y generar UNA vez.
        prompt = f"{built.system}\n\n{built.user}"
        text = self._llm.generate(prompt)  # LLMError propaga (R26)

        # R13/R19/R20: respuesta fundamentada con citas de f6 tal cual.
        return Answer(
            answer=text,                                          # R2, R13
            sources=built.sources,                                # R3, R19, R20
            abstained=False,                                      # R13
            metadata=AnswerMetadata(
                model=self._llm.model,                            # R4
                persona=self._persona_name_from_sources(persona, built),  # R5, R23
                max_score=result.max_score,                       # R6
                scores=scores,                                    # R7
            ),
        )
```

Contrato de la implementación:
- Validación de entrada ANTES de tocar dependencias (R25): query vacía lanza
  `OrchestratorError` sin llamar a retrieve/build/generate.
- Una sola llamada a `retrieve` por `answer` (R10); scores derivados de su
  resultado (R21).
- Short-circuit por `below_threshold` (R14): sin llamar a `build` ni `generate`.
- Respuesta fundamentada: una sola llamada a `generate` (R12); `sources` =
  `BuiltPrompt.sources` sin reconstruir (R19, R20).
- Errores de infra (`RetrieverError`, `EmbeddingError`, `VectorStoreError`,
  `LLMError`, `PersonaNotFoundError`) propagan tal cual (R26).

### Resolución del nombre de persona en la metadata (R5, R23)

f6 NO devuelve el nombre de la persona resuelta en `BuiltPrompt` (solo `system`,
`user`, `sources`). f8 necesita reportar ese nombre en la metadata. Opciones y
decisión:

- **Decisión adoptada:** cuando `persona` se pasa explícito, la metadata usa
  `persona.name` (R5). Cuando `persona is None`, f8 resuelve el **mismo** default
  que usará f6 llamando a `default_persona(self._settings)` (helper de f0/`config
  .py`) y reporta `resolved.name`, **pasando esa misma persona resuelta a**
  `PromptBuilder.build(query, result, resolved)`. Así el nombre reportado y la
  persona realmente usada coinciden, y la fuente de verdad del default sigue siendo
  `Settings.default_persona` (R23, sin duplicar la lógica de resolución).
- En el pseudocódigo de §5, `_resolve_persona_name` y la rama no-abstenida deben
  resolver la persona UNA vez al principio de `answer` (cuando es `None`) y
  reutilizarla tanto para `build` como para la metadata, para garantizar
  consistencia. (El implementer simplifica: resolver `effective_persona` arriba,
  usarlo en ambas ramas.)

> **Implementación recomendada (simplificación del pseudocódigo):** resolver
> `effective_persona = persona or default_persona(self._settings)` una sola vez al
> inicio (tras validar la query), usar `effective_persona.name` en toda la metadata
> y pasar `effective_persona` a `PromptBuilder.build`. Esto elimina los dos helpers
> separados y mantiene un único punto de resolución. `PersonaNotFoundError`
> propaga (R26).

## 6. Composición del prompt: `system` + `user` → string único (R12)

`LLMProvider.generate(prompt: str)` (f7) toma **un solo string**, pero
`BuiltPrompt` (f6) separa `system` y `user`. f8 los une:

```python
prompt = f"{built.system}\n\n{built.user}"
```

Decisión: concatenar `system` + doble salto de línea + `user`. Razones:
- f7 expone una API de prompt único (no un par system/user tipo chat). f8 es el
  punto natural donde se aplana el `BuiltPrompt` a la forma que `generate` espera.
- El grounding y la persona viven en `system` (f6); ponerlos ANTES del `user`
  (que ya trae CONTEXTO + PREGUNTA) preserva el orden evidencia→instrucción que f6
  diseñó. No se reordena ni se reescribe el contenido de f6.
- Mantener el separador como detalle de f8 deja a f7 agnóstico del formato y a f6
  dueño del contenido. Si f9 más adelante usa una API chat (system/user
  separados), solo cambia este punto de aplanado.

## 7. Lógica de abstención (propiedad nº1 — R14–R18)

- **Señal, no recálculo (R18, R21).** f8 lee `result.below_threshold` (computado
  por f5 como `max_score < score_threshold`, `<` estricto). f8 NO vuelve a comparar
  contra `Settings.score_threshold`; consume la señal. Esto evita duplicar la
  fuente de verdad del umbral y mantiene a f5 como único dueño del cálculo.
- **Short-circuit total (R14).** Si `below_threshold` es `true`, f8 retorna ANTES
  de tocar `PromptBuilder` o `LLMProvider`. Verificable con fakes que registren si
  fueron llamados (spy).
- **Mensaje claro y propio (R15, R18).** Constante de módulo `_ABSTENTION_MESSAGE`
  = "No hay evidencia suficiente en los documentos para responder con seguridad."
  Alineado con `docs/architecture.md` §5.2 y el principio 2 de `feature-list.json`.
- **`sources=[]` en abstención (R16).** No se ha fundamentado nada; no hay citas.
- **Metadata aún poblada (R17).** `max_score` (típicamente bajo) y `persona` se
  reportan para diagnóstico incluso al abstenerse.
- **Caso store vacío.** f5 ya devuelve `below_threshold=True` con `chunks=[]` y
  `max_score=0.0` (f5 R20). f8 lo trata como abstención normal: mensaje + `[]` +
  `max_score=0.0`. No hay rama especial.

## 8. Secuencia: camino feliz vs. camino de abstención

```
answer(query, persona)
  │
  ├─ query vacía ──────────────► raise OrchestratorError            (R25)
  │
  ├─ result = retriever.retrieve(query)                              (R10)
  │     └─ errores de infra ──► propagan (RetrieverError/…)         (R26)
  │
  ├─ scores = [rc.score for rc in result.chunks]                    (R21)
  │
  ├─ ¿result.below_threshold?
  │     │
  │     ├─ SÍ ► Answer(abstained=True, answer=MENSAJE, sources=[],  (R14-R17)
  │     │        metadata{model, persona, max_score, scores})
  │     │        (NO se llama a build ni a generate)
  │     │
  │     └─ NO ► built = prompt_builder.build(query, result, persona) (R11)
  │              prompt = built.system + "\n\n" + built.user         (R12)
  │              text = llm.generate(prompt)  ──► LLMError propaga   (R12, R26)
  │              Answer(abstained=False, answer=text,                (R13)
  │                     sources=built.sources,                       (R19, R20)
  │                     metadata{model, persona, max_score, scores}) (R4-R7)
  ▼
 return Answer
```

## 9. Exports del paquete `rag` y de `models` (R27)

`src/wowrag/rag/__init__.py`:

```python
from wowrag.rag.base import OrchestratorError, RagOrchestrator
from wowrag.rag.orchestrator import DefaultRagOrchestrator

__all__ = ["RagOrchestrator", "OrchestratorError", "DefaultRagOrchestrator"]
```

`Answer` (y `AnswerMetadata`) se exponen desde `wowrag.models` (importables como
`from wowrag.models import Answer`); incluir ambos en el `__all__` de `models.py`.

## 10. Estrategia de tests (todos DB-free / GPU-free / network-free; corren con `init.sh`)

Trazabilidad `R<n>` ↔ test obligatoria (comenta cada test con su `R<n>`). Dos
estilos de dependencia, ambos válidos:

- **Stubs/spies de las tres interfaces** (preferido para aislar el orquestador):
  un `Retriever` stub que devuelve un `RetrievalResult` fijo, un `PromptBuilder`
  stub que devuelve un `BuiltPrompt` fijo y registra si fue llamado, y
  `FakeLLMProvider` (f7) o un spy de `LLMProvider`.
- **Impls reales de f5/f6 + fakes de capa baja** (integración de la composición,
  sin red): `DefaultRetriever(FakeEmbeddingProvider, FakeVectorStore)` +
  `DefaultPromptBuilder` + `FakeLLMProvider`, con personas YAML reales de f0.

- `tests/test_models_answer.py` (modelos):
  - `Answer` con `answer`/`sources`/`abstained`/`metadata` se construye y expone los
    cuatro (R1). `AnswerMetadata` con `model`/`persona`/`max_score`/`scores` (R4-R7).
  - `Answer.sources` acepta `list[Source]` de f6 (R3).
  - `from wowrag.models import Answer, AnswerMetadata` funciona (R27).
- `tests/test_orchestrator.py` (`DefaultRagOrchestrator`):
  - `test_empty_query_raises`: query `""`/`"   "` → `OrchestratorError`; spies
    confirman que NO se llamó a retrieve/build/generate (R25).
  - `test_happy_path_returns_answer_with_citations`: `below_threshold=False` →
    `abstained is False`, `answer` == texto del LLM (R2, R13), `sources` ==
    `BuiltPrompt.sources` (R19, R20). (R3)
  - `test_generate_called_once_with_combined_prompt`: `generate` recibe un string
    que contiene `system` y `user` del `BuiltPrompt`, llamado exactamente una vez
    (R12).
  - `test_metadata_model_persona_scores`: `metadata.model` == `llm.model` (R4),
    `metadata.persona` == persona efectiva (R5), `metadata.max_score` ==
    `result.max_score` (R6), `metadata.scores` == scores por chunk (R7, R21).
  - `test_abstains_when_below_threshold`: `below_threshold=True` →
    `abstained is True`, `answer` == mensaje de abstención claro (R14, R15);
    `sources == []` (R16); spies confirman que NO se llamó a build/generate (R14).
  - `test_abstention_metadata_present`: al abstener, `metadata.max_score` y
    `metadata.persona` siguen presentes (R17).
  - `test_empty_store_abstains`: con f5 real sobre store vacío
    (`below_threshold=True`, `max_score=0.0`), f8 abstiene (R14-R17).
  - `test_persona_none_resolves_default`: `answer(q)` sin persona → metadata reporta
    `Settings.default_persona` y f6 recibe esa persona resuelta (R23).
  - `test_persona_explicit_reported`: `answer(q, persona=orc)` → `metadata.persona
    == "orc"` (R5).
  - `test_infra_errors_propagate`: un `Retriever` stub que lanza `RetrieverError`
    (o un `LLMProvider` que lanza `LLMError`) hace que `answer` propague la
    excepción, no devuelva un `Answer` vacío (R26).
  - `test_depends_only_on_interfaces`: construir `DefaultRagOrchestrator` con stubs
    que solo implementan los Protocols `Retriever`/`PromptBuilder`/`LLMProvider`
    (R9, R22).
  - `test_exports_from_package`: `from wowrag.rag import RagOrchestrator,
    OrchestratorError, DefaultRagOrchestrator` funciona (R27).

## 11. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| `Answer` en un módulo aparte (`rag/answer.py`) | `models.py` es la única casa de los modelos de datos y su docstring ya anticipa `Answer`; un módulo aparte rompe la convención de f5/f6 y complica el import de `Source` |
| `metadata` como `dict[str, Any]` suelto | Sin tipado ni validación; claves mágicas no testeables. Un submodelo `AnswerMetadata` da esquema estable para f9/frontend (convención: type hints obligatorios) |
| f8 recalcula el umbral (`max_score < Settings.score_threshold`) | Duplica la fuente de verdad; f5 ya computó `below_threshold` (`<` estricto). f8 consume la señal (R18, R21), no la recalcula |
| Abstención modelada como excepción (`raise AbstentionError`) | `docs/conventions.md`: "la abstención es una respuesta válida, no una excepción". Se modela en `Answer.abstained` (R14) |
| f8 llama a `generate_stream` / async | f7 expone `generate` síncrono como API principal; streaming/async se difieren a f9. f8 es síncrono (alcance) |
| Pasar `system`/`user` por separado al LLM | f7 `generate` toma un solo string; f8 es el punto de aplanado. Mantener f7 agnóstico del formato chat (R12, §6) |
| f8 produce su propio formato de citas | f6 ya numera `Source` con el formato estable del proyecto (`{n,title,url}`); f8 las devuelve tal cual (R20), sin reconstruir |
| Orquestador en `retrieval/` o `generation/` | Esas son capas de paso; la orquestación que une todo vive en `rag/` (`architecture.md` §3, §6). Mezclar capas → el revisor lo rechaza |
| f8 incluye el endpoint HTTP / FastAPI | HTTP es f9; f8 es librería pura para que f9 lo envuelva sin acoplar transporte a la lógica RAG |
| Resolver el default de persona con lógica propia en f8 | Duplicaría `default_persona()` de f0. f8 delega en el mismo helper y pasa la persona resuelta a f6 para que nombre reportado y persona usada coincidan (R23) |
| Enmascarar `LLMError`/`RetrieverError` como `Answer` con texto vacío | Oculta fallos de infra como respuesta; `docs/conventions.md` exige excepciones claras para infra (R26) |
| `ABC` en lugar de `Protocol` para `RagOrchestrator` | Inconsistente con `Retriever`/`PromptBuilder`/`LLMProvider` (todos Protocol); Protocol permite duck-typing en tests |
