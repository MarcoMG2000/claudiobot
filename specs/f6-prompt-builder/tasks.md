# Tasks — f6-prompt-builder

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests son unitarios con stdlib + modelos construidos a mano
> (`Chunk`/`RetrievedChunk`/`RetrievalResult` de f5) + las personas YAML reales de
> f0 (`simple`/`orc`/`troll`); sin Postgres, sin GPU, sin red, sin LLM. La
> trazabilidad `R<n>` ↔ test es obligatoria (`docs/verification.md`); nombra o
> comenta cada test con su `R<n>`.
>
> **Entrega: PR único** (ver `design.md` §0 y §11). f6 es comparable a f5; cabe en
> ~286 líneas, por debajo del presupuesto de 400. No se necesitan slices, no se
> necesita `size:exception`.
>
> `build(query, result, persona=None) -> BuiltPrompt`. f6 SOLO construye las
> cadenas del prompt (system+user) y las fuentes numeradas. NO llama al LLM (f7),
> NO orquesta ni decide abstención ni emite el mensaje "No hay evidencia
> suficiente…" (f8), NO recupera (f5). Reutiliza personas de f0 — NO las redefinas.

---

## Implementación

- [x] **T1 — Modelos `Source` y `BuiltPrompt` en `models.py`.**
  Editar `src/wowrag/models.py` para añadir:
  - `Source(BaseModel)` con `n: int`, `title: str`, `url: str` (cita numerada,
    shape `{n, title, url}` que f9 devolverá; ver `design.md` §4).
  - `BuiltPrompt(BaseModel)` con `system: str`, `user: str` y
    `sources: list[Source]`.
  - Añadir `"Source"` y `"BuiltPrompt"` a `__all__` de `models.py`.
  _(Cubre R1, R2)_

- [x] **T2 — Interfaz `PromptBuilder` y excepción `PromptBuilderError`.**
  Crear `src/wowrag/generation/prompt_builder_base.py` (NO `generation/base.py`,
  que queda reservado a f7 — ver `design.md` §3) con:
  - `PromptBuilderError(Exception)` — excepción de dominio (query vacía).
  - `PromptBuilder` Protocol con
    `build(self, query: str, result: RetrievalResult, persona: Persona | None = None) -> BuiltPrompt`.
    Docstring con el contrato: `persona=None` → `Settings.default_persona` vía
    `default_persona()`; query vacía → `PromptBuilderError`; contexto vacío →
    `BuiltPrompt` válido con `sources=[]` (no abstiene; eso es f8); persona
    inexistente → `PersonaNotFoundError` propagada (no envuelta).
  Importa `BuiltPrompt`/`RetrievalResult` de `wowrag.models` y `Persona` de
  `wowrag.personas`. `from __future__ import annotations`.
  _(Cubre R6, R25)_

- [x] **T3 — Implementación `DefaultPromptBuilder`.**
  Crear `src/wowrag/generation/prompt_builder.py` con `DefaultPromptBuilder` (ver
  `design.md` §5):
  - Constructor `__init__(self, settings: Settings | None = None)` — depende solo
    de modelos/persona/Settings (R7).
  - `build(query, result, persona=None) -> BuiltPrompt`:
    - query vacía/solo-espacios → `PromptBuilderError` ANTES de construir nada (R8).
    - resolver persona: explícita gana; si `None` → `default_persona(settings)` de
      f0 (R10, R11, R23); `PersonaNotFoundError` se deja propagar (R24, R26).
    - `system` = `persona.system_style` + bloque de grounding constante (R3, R12);
      el bloque de grounding incluye las 3 instrucciones (solo-contexto R13,
      declarar-falta-de-evidencia R14, citar-con-[n] R15) y es independiente de la
      persona (R16).
    - formatear contexto: enumerar `result.chunks` 1-indexado, en orden score-desc
      (sin reordenar), cada uno con `[n]`, `title`, `chunk.text` y `source_url`
      (R17, R18); SOLO datos del chunk (R20); una `Source(n, title, url)` por chunk
      (R5, R19, R22).
    - `user` = pregunta literal (R9) + bloque de contexto (R4); contexto vacío →
      aviso "(No hay contexto disponible.)" + `sources=[]`, sin excepción (R21).
  - Cero imports de LLM/red/DB/ML.
  _(Cubre R3, R4, R5, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R26)_

- [x] **T4 — Re-exportar desde `generation/__init__.py`.**
  Reemplazar el placeholder de `src/wowrag/generation/__init__.py` con imports y
  `__all__` que exporten `PromptBuilder`, `PromptBuilderError`,
  `DefaultPromptBuilder` (NO añadir nada de LLM; eso es f7).
  _(Cubre R27)_

---

## Tests

- [x] **T5 — `tests/test_models_prompt.py`** (modelos).
  - `test_source_fields`: `Source(n=1, title="t", url="u")` expone `n`/`title`/
    `url`. _(R2)_
  - `test_builtprompt_fields`: `BuiltPrompt(system=.., user=.., sources=[Source(..)])`
    expone los tres campos. _(R1, R2)_
  - `test_builtprompt_accepts_empty_sources`: `sources=[]` es válido. _(R22 borde)_
  - `test_models_exported`:
    `from wowrag.models import BuiltPrompt, Source` funciona. _(R27, modelos)_

- [x] **T6 — `tests/test_prompt_builder.py`** (`DefaultPromptBuilder`).
  Helper local: factoría que construye un `RetrievalResult` con N `RetrievedChunk`
  de `source_url`/`title`/`text` conocidos, `score` descendente,
  `below_threshold`/`max_score` plausibles (f6 no los usa, pero el objeto debe ser
  válido). Construir el builder con `Settings(_env_file=None)` u overrides
  explícitos de `default_persona`.
  - `test_empty_query_raises`: `build("", result)` y `build("   ", result)` →
    `PromptBuilderError`. _(R8)_
  - `test_user_contains_query`: la query literal aparece en `user`. _(R9)_
  - `test_system_and_user_nonempty`: `system` y `user` no vacíos. _(R3, R4)_
  - `test_default_persona_from_config`: sin persona, con
    `Settings(default_persona="orc")`, el `system_style` de `orc` aparece en
    `system`. _(R10, R23)_
  - `test_explicit_persona_overrides_config`: `build(.., persona=<troll>)` con
    `Settings(default_persona="simple")` → estilo de `troll`, no de `simple`. _(R11)_
  - `test_persona_style_injected`: el `system_style` de la persona resuelta está en
    `system`; cambiar de persona cambia ese texto. _(R12)_
  - `test_grounding_instructions_present`: `system` contiene las 3 instrucciones de
    grounding (solo-contexto, declarar-falta-de-evidencia, citar-con-[n]).
    _(R13, R14, R15)_
  - `test_grounding_independent_of_persona`: con `simple`, `orc` y `troll`, las 3
    instrucciones de grounding siguen presentes. _(R16)_
  - `test_context_has_sequential_citation_markers`: con N chunks, `user` contiene
    `[1]..[N]` en orden, 1-indexado, en el orden de `result.chunks`. _(R17)_
  - `test_context_includes_chunk_text_and_url`: para cada chunk, su `chunk.text` y
    su `source_url` (y `title`) aparecen en el contexto. _(R18)_
  - `test_sources_match_markers`: por cada `[n]` hay exactamente una
    `Source(n=n, url=source_url)` con la URL del chunk n; `len(sources)` == nº de
    chunks. _(R5, R19, R22)_
  - `test_context_only_from_result`: el contexto no contiene URLs/títulos ausentes
    de `result.chunks` (solo-contexto). _(R20)_
  - `test_empty_context_builds_valid_prompt`: `result.chunks == []` → `BuiltPrompt`
    válido, `user` indica "no hay contexto", `sources == []`, sin excepción. _(R21)_
  - `test_missing_persona_propagates`:
    `Settings(default_persona="does_not_exist")` + `build(.., persona=None)` →
    `PersonaNotFoundError` propagada (no `PromptBuilderError`, no prompt vacío).
    _(R24, R26)_
  - `test_builder_depends_only_on_models`: construir `DefaultPromptBuilder()` y
    `build` sin ningún `LLMProvider`/`Retriever`/`VectorStore`/`EmbeddingProvider`.
    _(R7)_
  - `test_exports_from_package`:
    `from wowrag.generation import PromptBuilder, PromptBuilderError,
    DefaultPromptBuilder` funciona. _(R27)_

---

## Cierre

- [x] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R27) tienen al menos un test.
  - `from wowrag.generation import PromptBuilder, PromptBuilderError,
    DefaultPromptBuilder` funciona.
  - `from wowrag.models import BuiltPrompt, Source` funciona.
  - `build` devuelve `BuiltPrompt` y NO llama a ningún LLM/Ollama, NO orquesta, NO
    emite mensaje de abstención ni decide abstención (frontera f7/f8 respetada),
    NO recupera (frontera f5 respetada).
  - Cada `[n]` del bloque de contexto tiene su `Source(n, title, url)` alineada
    (citas correctas, `docs/conventions.md`).
  - Las 3 instrucciones de grounding están presentes y son independientes de la
    persona; el contexto es solo-contexto (no hay datos externos en el prompt).
  - `config.py` NO fue modificado (solo se reutiliza `default_persona`); las
    personas de f0 NO fueron redefinidas.
  - `generation/base.py` NO fue creado/usado por f6 (queda reservado para f7); la
    interfaz de f6 vive en `prompt_builder_base.py`.
  - No quedan imports de DB/ML/red/LLM en `generation/prompt_builder*.py`.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json`. El cambio de estado y el cierre los hacen el leader /
> reviewer tras validar la trazabilidad `R<n>` ↔ test. Tu trabajo termina cuando
> todas las tasks `[x]` y `./init.sh` pasa en verde.
