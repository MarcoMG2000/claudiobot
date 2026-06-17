# Design — f6-prompt-builder

> CÓMO se construye la capa de prompt building (online query path, paso previo a la
> generación). Respeta el layout de `docs/architecture.md` §6
> (`src/wowrag/generation/prompt_builder.py`) y las convenciones del proyecto:
> interfaz en un `*_base.py`, implementación concreta aparte, excepción de dominio,
> `from __future__ import annotations`, dependencia solo de tipos/interfaces.
> Sigue el patrón establecido en f3 (`EmbeddingProvider`), f4 (`VectorStore`) y
> f5 (`Retriever`). Consume `RetrievedChunk`/`RetrievalResult` de f5 y el sistema
> de personas de f0.

## 0. Decisión de entrega: PR único (~≤ 280 líneas)

f6 es comparable en tamaño a f5: 2 modelos pydantic pequeños (`Source`,
`BuiltPrompt`), 1 interfaz + excepción, 1 implementación de composición de cadenas
(sin red, sin DB, sin ML), exports y sus tests unitarios. **No hay driver pesado,
ni migración SQL, ni servicios reales** (los tests construyen `RetrievalResult` a
mano con `Chunk`/`RetrievedChunk` y usan las personas YAML reales de f0). La fase de
apply **cabe holgadamente en un PR único dentro del presupuesto de ~400 líneas**.

**Recomendación: PR único.** No se necesitan slices encadenados.

Estimación de líneas cambiadas (apply):
- `models.py` (`Source` + `BuiltPrompt` + `__all__`): ~25
- `generation/prompt_builder_base.py` (Protocol + excepción): ~35
- `generation/prompt_builder.py` (`DefaultPromptBuilder`): ~70
- `generation/__init__.py` (exports): ~6
- `tests/test_models_prompt.py`: ~40
- `tests/test_prompt_builder.py`: ~110
- **Total estimado: ~286 líneas** — por debajo de 400. PR único, sin
  `size:exception`.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    models.py                          # EDITAR — añadir Source y BuiltPrompt (+ __all__)
    generation/
      __init__.py                      # EDITAR — re-exportar PromptBuilder, PromptBuilderError, DefaultPromptBuilder
      prompt_builder_base.py           # NUEVO — PromptBuilder (Protocol) + PromptBuilderError
      prompt_builder.py                # NUEVO — DefaultPromptBuilder (compone persona + grounding + contexto)
tests/
  test_models_prompt.py                # NUEVO — Source + BuiltPrompt (modelos)
  test_prompt_builder.py               # NUEVO — DefaultPromptBuilder (persona, grounding, citas, vacío)
```

Notas:
- `src/wowrag/generation/__init__.py` ya existe como placeholder (f0); se reemplaza
  con los re-exports reales (R27). El placeholder ya anticipa "Prompt builder …
  land in f6/f7".
- `generation/prompt_builder.py` ya está previsto en `docs/architecture.md` §6.
- **`generation/base.py` queda RESERVADO para f7** (`LLMProvider` + `LLMError`),
  según `docs/architecture.md` §6 (`generation/base.py # LLMProvider (interfaz)`).
  Para NO colisionar con f7 ni mezclar dos interfaces en un mismo `base.py`, la
  interfaz de f6 vive en **`prompt_builder_base.py`** (decisión §3).
- `models.py` SÍ se edita en f6: añade `Source` y `BuiltPrompt`. El docstring de
  `models.py` menciona que `Answer` llega "en una feature posterior" (f8); f6 no
  toca `Answer`.
- **`config.py` NO se edita.** `default_persona` YA existe en `Settings` y tiene
  default-assert + env-override test (`test_env_var_overrides_default` usa
  `DEFAULT_PERSONA=orc`). f6 solo lo **reutiliza** (R10, R23). Ver §8.
- **Personas NO se redefinen.** f6 reutiliza `Persona`, `load_persona` y el helper
  `default_persona()` de f0 tal cual.

## 2. Ubicación del módulo: `src/wowrag/generation/` (capa de generación, online)

Decisión: el prompt builder vive en **`src/wowrag/generation/`**, NO en `rag/` ni
en `retrieval/`.

Justificación según `docs/architecture.md` §3 y §6:
- El diagrama de flujo §3 sitúa el **prompt builder** como un paso propio del camino
  online, después del retriever y antes del LLM
  (`retriever (top-k + score) → prompt builder → persona + grounding → LLM`).
- §6 reserva explícitamente `generation/prompt_builder.py` para esta capa, junto a
  `generation/base.py` (LLMProvider, f7) y `generation/ollama.py` (f7). El prompt
  building y la provisión de LLM son la misma capa de **generación**; la
  **orquestación** (unir retrieve→prompt→LLM→abstención) es `rag/orchestrator.py`
  (f8).
- Meter el prompt builder en `retrieval/` o en `rag/` mezclaría capas; el revisor
  rechaza la mezcla de capas (`architecture.md` §6).

## 3. Decisión: interfaz en `prompt_builder_base.py`, NO en `generation/base.py`

`docs/architecture.md` §6 reserva `generation/base.py` para `LLMProvider` (f7). Si
f6 metiera `PromptBuilder` en `generation/base.py`, f7 tendría que ampliar ese mismo
fichero con una interfaz no relacionada (LLM), mezclando dos contratos
independientes en un `base.py`. Para mantener una interfaz por fichero y dejar
`base.py` libre para f7, f6 define su Protocol en
**`src/wowrag/generation/prompt_builder_base.py`**.

> El patrón del proyecto es "interfaz en `base.py` de su paquete". Aquí el paquete
> `generation/` aloja DOS capacidades distintas (prompt building y LLM provider).
> Para respetar el espíritu del patrón (una interfaz = un fichero `*_base.py`) sin
> colisionar con f7, se sufija el nombre: `prompt_builder_base.py`. Esto se documenta
> como decisión explícita y se justifica en la tabla de alternativas (§11).

`src/wowrag/generation/prompt_builder_base.py`:

```python
from __future__ import annotations

from typing import Protocol

from wowrag.models import BuiltPrompt
from wowrag.personas import Persona
from wowrag.models import RetrievalResult


class PromptBuilderError(Exception):
    """Domain exception for prompt-builder input failures.

    Raised for an empty/whitespace query. A missing persona surfaces as
    PersonaNotFoundError from the f0 loader and is NOT wrapped (R24, R26).
    """


class PromptBuilder(Protocol):
    """Swap point: (query + RetrievalResult + persona) -> BuiltPrompt.

    Implementación concreta: DefaultPromptBuilder. Callers (f8/f9) depend on this
    Protocol, never on a concrete impl. f6 builds the prompt STRINGS only; it does
    NOT call any LLM (f7), orchestrate, or decide abstention (f8).
    """

    def build(
        self,
        query: str,
        result: RetrievalResult,
        persona: Persona | None = None,
    ) -> BuiltPrompt:
        """Construye el prompt system+user con persona, grounding y contexto citable.

        persona=None -> resuelve Settings.default_persona vía default_persona() (f0).
        Query vacía -> PromptBuilderError. Contexto vacío -> BuiltPrompt válido con
        sources=[] (NO abstiene; eso es f8).
        """
        ...
```

## 4. Modelos: `Source` y `BuiltPrompt` (R1–R5, R19, R22)

`models.py` añade dos modelos. `Source` modela la cita resoluble (lo que f9
devolverá en `sources` con `{n, title, url}`, según `docs/conventions.md`).
`BuiltPrompt` empaqueta las dos cadenas + las fuentes.

```python
class Source(BaseModel):
    """Una fuente citable, numerada para enlazar con el marcador [n] del prompt.

    Forma estable de cita del proyecto: n + title + url (docs/conventions.md).
    f9 la devolverá en la respuesta de la API como {n, title, url}.
    """

    n: int        # número de cita, 1-indexado, coincide con [n] en el prompt (R5, R19)
    title: str
    url: str      # source_url de wowhead del RetrievedChunk citado


class BuiltPrompt(BaseModel):
    """El prompt construido: system + user + las fuentes numeradas que cita.

    f6 produce este objeto; f8 pasa system/user al LLMProvider (f7) y devuelve
    sources en la respuesta final. f6 NO llama al LLM.
    """

    system: str                  # estilo de persona + grounding estricto (R3, R12, R13-R16)
    user: str                    # pregunta + contexto formateado con [n] (R4, R9, R17)
    sources: list[Source]        # una por chunk citado; [] si contexto vacío (R2, R22)
```

### Decisión: devolver un objeto `BuiltPrompt`, no un `tuple[str, str]`

`build()` devuelve un **`BuiltPrompt`** (objeto), no `(system, user)` suelto ni un
dict. Razones:
- Las `sources` numeradas tienen que viajar JUNTO a las cadenas para que f8 las
  devuelva en la respuesta sin re-parsear el prompt buscando `[n]`. Modelarlo como
  objeto cohesiona los tres datos (coherente con `RetrievalResult` de f5, que
  cohesiona chunks + señal en un objeto de retorno).
- Pydantic da validación y serialización gratis (f9 serializa `sources` a JSON).
- Evita que f8 tenga que reconstruir el mapeo `[n] → url` parseando texto.

## 5. Implementación `DefaultPromptBuilder` (R8–R24)

`src/wowrag/generation/prompt_builder.py` — compone cadenas; sin imports de
LLM/red/DB/ML. Resuelve persona desde `Settings` cuando no se pasa una explícita.

```python
from __future__ import annotations

from wowrag.config import Settings, default_persona
from wowrag.generation.prompt_builder_base import PromptBuilderError
from wowrag.models import BuiltPrompt, RetrievalResult, Source
from wowrag.personas import Persona

# Instrucciones de grounding (constantes de módulo; idénticas para toda persona, R16).
_GROUNDING_INSTRUCTIONS = (
    "Responde ÚNICAMENTE con la información del CONTEXTO de abajo. "          # R13
    "No uses conocimiento externo ni inventes datos. "                        # R13
    "Si el CONTEXTO no contiene evidencia suficiente para responder, dilo "   # R14
    "explícitamente en lugar de inventar. "                                   # R14
    "Cita cada afirmación con su marcador [n] correspondiente del CONTEXTO."  # R15
)
_NO_CONTEXT_NOTICE = "(No hay contexto disponible.)"  # R21


class DefaultPromptBuilder:
    """Construye un BuiltPrompt a partir de (query, RetrievalResult, persona).

    Depende solo de modelos/persona/Settings (R7): testeable sin red, sin GPU,
    sin Postgres. NO llama a ningún LLM ni decide abstención (frontera f7/f8).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def build(
        self,
        query: str,
        result: RetrievalResult,
        persona: Persona | None = None,
    ) -> BuiltPrompt:
        if not query or not query.strip():
            raise PromptBuilderError("query must be a non-empty string")  # R8

        # R10/R11/R23/R24: persona explícita gana; si None, resuelve la de config.
        # default_persona() puede lanzar PersonaNotFoundError -> propaga (R24, R26).
        resolved = persona if persona is not None else default_persona(self._settings)

        system = self._build_system(resolved)            # R3, R12, R13-R16
        context_block, sources = self._format_context(result)  # R17-R22
        user = self._build_user(query, context_block)    # R4, R9

        return BuiltPrompt(system=system, user=user, sources=sources)

    def _build_system(self, persona: Persona) -> str:
        # Estilo de persona + grounding (grounding SIEMPRE presente, R16).
        return f"{persona.system_style}\n\n{_GROUNDING_INSTRUCTIONS}"

    def _format_context(self, result: RetrievalResult) -> tuple[str, list[Source]]:
        if not result.chunks:                            # R21
            return _NO_CONTEXT_NOTICE, []
        lines: list[str] = []
        sources: list[Source] = []
        for i, rc in enumerate(result.chunks, start=1):  # R17 (1-indexado, orden score-desc)
            # R18/R20: SOLO datos del RetrievedChunk (text, title, source_url).
            lines.append(f"[{i}] {rc.title}\n{rc.chunk.text}\n(Fuente: {rc.source_url})")
            sources.append(Source(n=i, title=rc.title, url=rc.source_url))  # R5, R19, R22
        return "\n\n".join(lines), sources

    def _build_user(self, query: str, context_block: str) -> str:
        # R9: incluye la query literal; R4/R20: contexto formateado (o aviso de vacío).
        return f"CONTEXTO:\n{context_block}\n\nPREGUNTA:\n{query}"
```

Contrato de la implementación:
- Validación de entrada ANTES de construir nada (R8): query vacía/solo-espacios
  lanza `PromptBuilderError`.
- Resolución de persona: explícita gana sobre `Settings.default_persona`
  (R10, R11); `None` → `default_persona(settings)` de f0 (R23). Persona inexistente
  → `PersonaNotFoundError` propagada, no enmascarada (R24, R26).
- `system` = `persona.system_style` + grounding (R3, R12); las 3 instrucciones de
  grounding son constantes independientes de la persona (R13–R16).
- `_format_context` enumera `result.chunks` en orden (score-desc, sin reordenar),
  1-indexado; cada línea lleva `[n]`, `title`, `chunk.text` y `source_url` (R17,
  R18); SOLO datos del chunk (R20). Una `Source(n, title, url)` por chunk (R19,
  R22). Marcadores `[n]` y `sources[n]` siempre alineados (R5).
- Contexto vacío → bloque "(No hay contexto disponible.)" + `sources=[]`, sin
  excepción (R21). f6 NO emite mensaje de abstención (eso es f8).
- Cero imports de LLM/red/DB/ML.

> **Idioma de las instrucciones.** El grounding y los rótulos (`CONTEXTO`,
> `PREGUNTA`, `Fuente`) se redactan en español, coherente con las personas actuales
> (`language: es`) y con el carácter multilingüe del proyecto
> (`docs/architecture.md` §2: preguntas/personas pueden ser en español, corpus
> mayormente inglés). El `chunk.text` se inserta tal cual (puede ser inglés); el
> LLM bge-m3/qwen es multilingüe. f6 no traduce contenido (fuera de alcance).

## 6. Frontera de alcance (crítica — encodada en el diseño)

| Responsabilidad | Feature | f6 hace |
|-----------------|---------|---------|
| Recuperar top-k + scores + señal `below_threshold` | f5 | CONSUME `RetrievalResult` |
| Construir system+user prompt + citas | **f6** | **SÍ** |
| Definir personas | f0 | REUTILIZA `Persona`/`load_persona`/`default_persona` |
| Llamar al LLM (Ollama) | f7 | NO |
| Orquestar retrieve→prompt→generate, mensaje de abstención, `Answer` | f8 | NO |
| Decidir abstención según `below_threshold` | f8 | NO (f6 no lee `below_threshold`) |
| API HTTP, persona por petición | f9 | NO (acepta override por argumento, sin HTTP) |

> **Distinción fina (grounding vs abstención).** f6 SÍ instruye al LLM, *dentro del
> prompt*, a declarar falta de evidencia si el contexto no respalda (R14) — eso es
> una instrucción de grounding. f6 NO hace el short-circuit de abstención (no llamar
> al LLM cuando `below_threshold` es true) ni emite el texto final "No hay evidencia
> suficiente…": eso es f8, que lee la señal de f5.

## 7. Formato de cita (R5, R17–R22) — coherente con `docs/conventions.md`

`docs/conventions.md` ("Citas") fija el contrato: cada chunk recuperado conserva
`source_url` y `title`; el `PromptBuilder` numera las fuentes `[1], [2]…` y la
respuesta de la API las devuelve en `sources` con `{n, title, url}`. f6 implementa
exactamente eso:
- Numeración 1-indexada, secuencial, en el orden de `result.chunks` (score desc).
- Cada `[n]` en el bloque de contexto ↔ una `Source(n, title, url)` en
  `BuiltPrompt.sources` con la `source_url` del chunk (R19). El modelo `Source` usa
  el shape `{n, title, url}` que f9 devolverá tal cual.
- Solo-contexto (R20): el bloque se deriva exclusivamente de `result.chunks`; no se
  inyecta texto/hechos/fuentes externas.

## 8. Configuración: reutiliza `default_persona` (R10, R23) — sin nuevos campos

`config.py` **NO se modifica en f6.** El campo ya existe en `Settings`
(`src/wowrag/config.py`) y el helper de composición también:

```python
default_persona: str = "simple"          # campo de Settings (f0)

def default_persona(settings: Settings | None = None) -> Persona:  # helper (f0)
    settings = settings or Settings()
    return load_persona(settings.default_persona)
```

- `Settings.default_persona` → nombre de persona por defecto (R23).
- `default_persona(settings)` → resuelve y carga la `Persona` (R10).

> **Lección f3 R10 / f4 / f5 (regla del proyecto): todo campo de `Settings` que una
> feature usa necesita test de default-assert + env-override.** Estado de
> `default_persona`:
> - default-assert ✅ — `EXPECTED_DEFAULTS` en `tests/test_config.py` tiene
>   `"default_persona": "simple"`.
> - env-override ✅ — `test_env_var_overrides_default` ya hace
>   `monkeypatch.setenv("DEFAULT_PERSONA", "orc")` y asierta
>   `settings.default_persona == "orc"`.
>
> Ambos casos YA están cubiertos. **f6 NO añade campos de config nuevos y, por
> tanto, NO necesita añadir tests de config nuevos** (a diferencia de f5, que tuvo
> que cerrar el hueco de `score_threshold`). El hueco no existe aquí: el campo que
> f6 consume ya está plenamente testeado. f6 SÍ añade un test funcional de que
> `build(persona=None)` resuelve la persona de `Settings.default_persona` (R10),
> que valida el uso del campo a nivel de la feature.

## 9. Exports del paquete `generation` y de `models` (R27)

`src/wowrag/generation/__init__.py` — reemplazar el placeholder:

```python
from wowrag.generation.prompt_builder import DefaultPromptBuilder
from wowrag.generation.prompt_builder_base import PromptBuilder, PromptBuilderError

__all__ = ["PromptBuilder", "PromptBuilderError", "DefaultPromptBuilder"]
```

> f7 ampliará este `__all__` con `LLMProvider`, `LLMError`, `OllamaLLM`,
> `FakeLLMProvider` cuando aterrice; f6 no añade nada de LLM.

`Source` y `BuiltPrompt` se exponen desde `wowrag.models` añadiéndolos a su
`__all__` (importables como `from wowrag.models import BuiltPrompt, Source`).

```python
__all__ = [
    "Document",
    "Chunk",
    "RetrievedChunk",
    "RetrievalResult",
    "Source",         # f6
    "BuiltPrompt",    # f6
]
```

## 10. Estrategia de tests (todos DB-free / GPU-free / network-free; corren con `init.sh`)

Los tests construyen `RetrievalResult` a mano con `Chunk`/`RetrievedChunk`
(sin retriever, sin store, sin embeddings) y usan las personas YAML reales de f0
(`simple`, `orc`, `troll`). Trazabilidad `R<n>` ↔ test obligatoria (comenta cada
test con su `R<n>`).

Helper de test sugerido: una factoría local que produce un `RetrievalResult` con N
`RetrievedChunk` de `source_url`/`title`/`text` conocidos y `score` descendente.

- `tests/test_models_prompt.py` (modelos):
  - `Source(n=1, title=.., url=..)` construye y expone `n`/`title`/`url` (R2).
  - `BuiltPrompt(system=.., user=.., sources=[..])` construye y expone los tres
    campos (R1, R2); acepta `sources=[]` (R22 borde).
  - `from wowrag.models import BuiltPrompt, Source` funciona (R27, modelos).
- `tests/test_prompt_builder.py` (`DefaultPromptBuilder`):
  - `test_empty_query_raises`: `build("", result)` y `build("   ", result)` →
    `PromptBuilderError`. _(R8)_
  - `test_user_contains_query`: la query literal aparece en `BuiltPrompt.user`.
    _(R9)_
  - `test_system_and_user_nonempty`: `system` y `user` no vacíos tras construir.
    _(R3, R4)_
  - `test_default_persona_from_config`: `build(query, result)` sin persona usa
    `Settings(default_persona="orc")` → el `system_style` de `orc` aparece en
    `system`. Construir el builder con `Settings(_env_file=None)` + override
    explícito de `default_persona`, o monkeypatch `DEFAULT_PERSONA`. _(R10, R23)_
  - `test_explicit_persona_overrides_config`: `build(query, result, persona=troll)`
    con `Settings(default_persona="simple")` → aparece el estilo de `troll`, no el
    de `simple`. _(R11)_
  - `test_persona_style_injected`: el `system_style` de la persona resuelta está en
    `system`; cambiar de persona cambia ese texto. _(R12)_
  - `test_grounding_instructions_present`: `system` contiene las 3 instrucciones de
    grounding (solo-contexto, declarar-falta-de-evidencia, citar-con-[n]).
    _(R13, R14, R15)_
  - `test_grounding_independent_of_persona`: con `simple`, `orc` y `troll`, las 3
    instrucciones de grounding siguen presentes (R16); verificable buscando
    fragmentos clave de `_GROUNDING_INSTRUCTIONS` en cada `system`. _(R16)_
  - `test_context_has_sequential_citation_markers`: con N chunks, el `user` contiene
    `[1]..[N]` en orden, 1-indexado, en el orden de `result.chunks`. _(R17)_
  - `test_context_includes_chunk_text_and_url`: para cada chunk, su `chunk.text` y
    su `source_url` (y `title`) aparecen en el bloque de contexto. _(R18)_
  - `test_sources_match_markers`: por cada `[n]` hay exactamente una
    `Source(n=n, url=source_url)` en `sources` con la URL del chunk n; longitud de
    `sources` == nº de chunks. _(R5, R19, R22)_
  - `test_context_only_from_result`: el bloque de contexto no contiene URLs/títulos
    que no estén en `result.chunks` (solo-contexto; verificable comprobando que las
    únicas URLs presentes son las de los chunks). _(R20)_
  - `test_empty_context_builds_valid_prompt`: `result.chunks == []` →
    `BuiltPrompt` válido, `user` indica "no hay contexto", `sources == []`, sin
    excepción. _(R21)_
  - `test_missing_persona_propagates`: `Settings(default_persona="does_not_exist")`
    + `build(query, result)` (persona=None) → `PersonaNotFoundError` propagada (no
    `PromptBuilderError`, no prompt vacío). _(R24, R26)_
  - `test_builder_depends_only_on_models`: construir `DefaultPromptBuilder()` y
    llamar `build` sin ningún `LLMProvider`/`Retriever`/`VectorStore`/
    `EmbeddingProvider`; no se importa ni instancia ninguno. _(R7)_
  - `test_exports_from_package`:
    `from wowrag.generation import PromptBuilder, PromptBuilderError,
    DefaultPromptBuilder` funciona. _(R27)_

> **Nota anti-abstención (frontera f8).** Ningún test de f6 verifica el texto "No
> hay evidencia suficiente…" ni el short-circuit del LLM; ese comportamiento es de
> f8. f6 solo verifica que el prompt INSTRUYE al modelo a declarar falta de
> evidencia (R14), que es distinto.

## 11. Estimación de carga de revisión (review-workload)

Apply estimado: 2 modelos pequeños + interfaz + excepción + 1 clase de composición
de cadenas (~70 líneas) + exports + 2 ficheros de test. **~286 líneas, por debajo
del presupuesto de 400.** PR único; no se recomiendan slices, no se necesita
`size:exception`.

- Chained PRs recommended: **No**
- 400-line budget risk: **Low**
- Decision needed before apply: **No**

## 12. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Interfaz `PromptBuilder` en `generation/base.py` | `architecture.md` §6 reserva `generation/base.py` para `LLMProvider` (f7); meter ahí el PromptBuilder mezcla dos contratos no relacionados en un fichero y obliga a f7 a compartirlo. `prompt_builder_base.py` mantiene una interfaz por fichero sin colisionar con f7 |
| `build()` devuelve `tuple[str, str]` (system, user) | Las `sources` numeradas quedarían desacopladas; f8 tendría que re-parsear el prompt buscando `[n]→url`. `BuiltPrompt` cohesiona system+user+sources en un retorno (coherente con `RetrievalResult` de f5) |
| `build()` devuelve un `dict` | Sin validación ni tipado; pydantic da validación y serialización JSON gratis para f9 |
| f6 lee `result.below_threshold` y emite el mensaje de abstención | Fuera de alcance: la decisión de abstención y el mensaje "No hay evidencia suficiente…" son f8, que lee la señal de f5. f6 solo construye el prompt (e instruye grounding, R14) |
| f6 llama al LLM / formatea la respuesta final | LLM es f7; `Answer` + orquestación es f8. f6 se detiene en el `BuiltPrompt` |
| Redefinir personas dentro de f6 (estilos hardcodeados) | f0 ya define `Persona`/`load_persona` y los YAML (`simple`/`orc`/`troll`); redefinirlos duplica la fuente de verdad y viola `conventions.md` (personas en ficheros, no en código). f6 reutiliza |
| Añadir un campo de config nuevo para la persona | `Settings.default_persona` ya existe y está testeado (default + env-override); añadir otro duplicaría la fuente de verdad (R23) |
| Marcadores de cita por `chunk_id` en vez de `[1..N]` | `conventions.md` fija `[1], [2]…` numerado secuencial + `sources` `{n,title,url}`; usar `chunk_id` rompería el contrato de cita esperado por f9 |
| Instrucciones de grounding dependientes de la persona (variar el grounding por estilo) | El grounding es no-negociable y constante (`architecture.md` §5); debilitarlo por persona arriesga alucinaciones. R16 exige independencia persona↔grounding |
| Inyectar el bloque de contexto en el `system` en vez del `user` | El contexto recuperado es contenido de la conversación (entrada del turno), no instrucción de sistema; separarlo en `user` mantiene `system` estable (persona + grounding) y el contexto variable en `user`, mejor para caché de prompts y claridad |
| `ABC` en lugar de `Protocol` para `PromptBuilder` | Inconsistente con `EmbeddingProvider`/`VectorStore`/`Retriever` (Protocol); Protocol no exige herencia y permite duck-typing en tests |
| Enmascarar `PersonaNotFoundError` como `PromptBuilderError` o prompt vacío | Oculta un error de configuración como fallo de entrada o como "sin contexto"; `conventions.md` exige errores claros, no respuestas vacías (R24, R26) |
