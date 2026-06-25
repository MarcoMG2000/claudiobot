# Requirements — f12-reranking

> Feature: `f12-reranking` — Reranking layer; cross-encoder reranker to improve
> top-k ordering before generation. Optional, swappable, bypasseable.
> Notación: EARS estricto (ver `docs/specs.md`). Cada `R<n>` es una frase única
> verificable por al menos un test (ver `docs/verification.md`).

## Alcance

Esta feature establece:

1. El modelo **`RerankResult`** en `src/wowrag/models.py` — resultado del reranking:
   la lista de `RetrievedChunk` reordenada (o pasada tal cual), el `top_n` efectivo
   usado, y el origen (`reranker_model: str | None`). Permite a los consumidores
   (f8) diagnosticar qué reranker actuó.
2. La **interfaz `Reranker`** (Protocol swappable) en
   `src/wowrag/retrieval/reranker.py` — el único punto de intercambio para todas las
   implementaciones de reranker.
3. La **implementación `PassthroughReranker`** — no-op que devuelve los chunks tal
   cual sin reordenar, con coste cero. Es el default cuando no hay reranker
   configurado.
4. La **implementación `CrossEncoderReranker`** — reranker real que usa un modelo
   cross-encoder (sentence-transformers) para puntuar y reordenar la lista. Solo
   disponible cuando la dependencia ML `sentence-transformers` está instalada.
5. El **fake `FakeCrossEncoderReranker`** para tests — invierte el orden de los
   chunks para verificar que el pipeline respeta el orden devuelto por el reranker.
   Cero dependencias ML; usa solo stdlib.
6. La **integración en `DefaultRagOrchestrator`** (f8) por inyección de
   dependencias: el orquestador acepta un `Reranker` opcional entre el `Retriever` y
   el `PromptBuilder`. Cuando está presente, aplica el reranking antes de construir
   el prompt; cuando no está presente (o es `PassthroughReranker`), el flujo es
   idéntico al actual.
7. La **configuración** en `Settings` para activar, seleccionar y parametrizar el
   reranker: `reranker_model` (nombre del modelo cross-encoder), `reranker_top_n`
   (cuántos chunks devolver tras reranking) y `reranker_enabled` (flag on/off).

### Fuera de alcance (explícito)

- **HTTP API / FastAPI** (f9): la API no cambia su contrato externo. Si el
  orquestador tiene un reranker, la respuesta mejora implícitamente — sin nuevo
  campo en la respuesta de f9.
- **Evaluación** (f10): el harness de evaluación puede invocar el orquestador con
  o sin reranker, pero f12 NO modifica el harness ni el dataset.
- **Scraping** (f11): sin relación.
- **Embeddings / VectorStore / chunking**: f12 opera sobre los `RetrievedChunk` ya
  recuperados; no toca la capa de indexado.
- **Reescribir f5/f8**: f12 añade una capa opcional; no reimplementa el retriever
  ni el orquestador — solo extiende el orquestador por inyección.
- **Streaming / async**: fuera de alcance, igual que en f8.

## Trazabilidad con el `acceptance` original

El `acceptance` de `feature-list.json` para esta feature es:

> "Cross-encoder reranker to improve top-k ordering before generation."

| Fragmento del acceptance                          | Requisitos que lo cubren          |
|---------------------------------------------------|-----------------------------------|
| Cross-encoder reranker                            | R6, R7, R8, R9                    |
| to improve top-k ordering                         | R3, R4, R5, R8                    |
| before generation                                 | R16, R17, R18                     |
| (bypasseable / optional)                          | R10, R11, R19, R20                |

(Requisitos transversales: interfaz `Reranker` R1, R2; modelos R12; configuración
R13, R14, R15; tests con fakes R21, R22; integración R23; exports R24.)

## Requisitos

### Interfaz `Reranker`

**R1** — El sistema DEBE definir una interfaz `Reranker` (Protocol) en
`src/wowrag/retrieval/reranker.py` con un método
`rerank(query: str, chunks: list[RetrievedChunk], top_n: int | None = None) -> RerankResult`,
como único punto de intercambio para las implementaciones de reranker.

**R2** — El sistema DEBE que toda implementación de `Reranker` dependa solo de los
tipos de `wowrag.models` (`RetrievedChunk`, `RerankResult`), de modo que sea
construible e invocable en tests sin dependencias ML, sin red y sin Postgres.

### Modelo `RerankResult`

**R3** — El sistema DEBE definir un modelo `RerankResult` en
`src/wowrag/models.py` con al menos los campos `chunks: list[RetrievedChunk]`
(en el orden producido por el reranker), `top_n: int` (número de chunks devueltos)
y `reranker_model: str | None` (identificador del modelo usado, `None` para el
passtrthrough).

**R4** — El sistema DEBE que `RerankResult.chunks` contenga como mucho `top_n`
elementos: si el reranker produce `top_n` chunks, `len(RerankResult.chunks) == top_n`.

**R5** — El sistema DEBE que, cuando el número de chunks de entrada sea menor que
`top_n`, `RerankResult.chunks` contenga todos los chunks de entrada sin truncar
(i.e. `top_n` efectivo = `min(top_n_solicitado, len(chunks_entrada))`).

### `PassthroughReranker` (no-op)

**R6** — El sistema DEBE definir una implementación `PassthroughReranker` de la
interfaz `Reranker` en `src/wowrag/retrieval/reranker.py` que devuelva los chunks
en el mismo orden que los recibió, sin puntuar ni reordenar.

**R7** — CUANDO `PassthroughReranker.rerank` se invoca, el sistema DEBE devolver un
`RerankResult` con `reranker_model = None` y `top_n` igual al número de chunks
devueltos.

**R8** — CUANDO `PassthroughReranker.rerank` recibe `top_n` explícito, el sistema
DEBE truncar la lista devuelta a `min(top_n, len(chunks))` elementos, respetando
el orden original.

### `CrossEncoderReranker`

**R9** — El sistema DEBE definir una implementación `CrossEncoderReranker` de la
interfaz `Reranker` en `src/wowrag/retrieval/reranker.py` que, dado un `query` y
una lista de `RetrievedChunk`, use un modelo cross-encoder para puntuar cada par
`(query, chunk.chunk.text)`, ordene los chunks por puntuación descendente y
devuelva los `top_n` primeros en un `RerankResult`.

**R10** — El sistema DEBE que `CrossEncoderReranker` reciba el nombre del modelo
cross-encoder (`model_name: str`) en su constructor, de modo que sea configurable
por entorno sin cambiar código.

**R11** — El sistema DEBE que `CrossEncoderReranker` recargue el modelo perezosamente
(lazy load) la primera vez que se llama a `rerank`, no en el constructor, de modo
que el import del módulo no obligue a cargar pesos ML en tests o en el arranque de
la app si el reranker no se usa.

**R12** — CUANDO `CrossEncoderReranker.rerank` se invoca, el sistema DEBE devolver
un `RerankResult` con `reranker_model` igual al `model_name` configurado.

### `FakeCrossEncoderReranker` (para tests)

**R13** — El sistema DEBE definir una implementación `FakeCrossEncoderReranker` de
la interfaz `Reranker` en `src/wowrag/retrieval/reranker.py` que invierta el orden
de los chunks recibidos (el peor chunk del retriever pasa a ser el primero) como
estrategia determinista de reordenación, de modo que los tests puedan verificar que
el orquestador usa el orden del reranker y no el del retriever.

**R14** — El sistema DEBE que `FakeCrossEncoderReranker` no importe ni instancie
ninguna librería ML (`sentence-transformers`, `torch`, `transformers`, etc.),
garantizando que los tests unitarios pasen sin instalar `requirements-ml.txt`.

**R15** — CUANDO `FakeCrossEncoderReranker.rerank` se invoca, el sistema DEBE
devolver un `RerankResult` con `reranker_model = "fake"` y `top_n` igual al número
de chunks devueltos.

### Configuración

**R16** — El sistema DEBE añadir a `Settings` un campo `reranker_enabled: bool`
con valor por defecto `False`, que indique si se activa el reranker en el pipeline.

**R17** — El sistema DEBE añadir a `Settings` un campo `reranker_model: str` con
valor por defecto `"cross-encoder/ms-marco-MiniLM-L-6-v2"`, que defina el modelo
cross-encoder a usar cuando `reranker_enabled` es `True`.

**R18** — El sistema DEBE añadir a `Settings` un campo `reranker_top_n: int` con
valor por defecto igual a `Settings.top_k` (o como entero positivo explícito, p.ej.
`3`), que controle cuántos chunks devuelve el reranker al orquestador.

### Integración en `DefaultRagOrchestrator`

**R19** — El sistema DEBE que `DefaultRagOrchestrator` acepte un parámetro
opcional `reranker: Reranker | None = None` en su constructor, sin romper ningún
código ni test existente de f8 (retrocompatibilidad: si `reranker` es `None`, el
comportamiento es idéntico al actual).

**R20** — CUANDO `DefaultRagOrchestrator` recibe un `reranker` no `None` y
`RetrievalResult.below_threshold` es `False`, el sistema DEBE llamar a
`reranker.rerank(query, result.chunks, top_n=self._settings.reranker_top_n)` antes
de llamar al `PromptBuilder`, y pasar los chunks de `RerankResult.chunks` al
`PromptBuilder` en lugar de `result.chunks`.

**R21** — CUANDO `DefaultRagOrchestrator` recibe un `reranker` no `None` y
`RetrievalResult.below_threshold` es `True`, el sistema DEBE NO llamar al reranker
(short-circuit de abstención tiene precedencia) y proceder con la abstención
exactamente igual que antes.

**R22** — MIENTRAS `reranker` es `None` en `DefaultRagOrchestrator`, el sistema
DEBE NO alterar el flujo existente de f8: los chunks de `result.chunks` se pasan
directamente al `PromptBuilder` sin ninguna operación de reranking intermedia.

**R23** — El sistema DEBE que la integración del reranker en `DefaultRagOrchestrator`
no cambie el contrato de retorno `Answer` de f8: el `Answer` devuelto mantiene los
mismos campos (`answer`, `sources`, `abstained`, `metadata`) sin añadir nuevos.

### Tests unitarios

**R24** — El sistema DEBE proporcionar tests unitarios en
`tests/test_reranker.py` que verifiquen `PassthroughReranker`,
`FakeCrossEncoderReranker` y la integración del reranker en
`DefaultRagOrchestrator`, sin instanciar ningún modelo ML ni requerir red o
Postgres. Los tests deben ejecutarse y pasar con `./init.sh` (suite `not integration`).

**R25** — El sistema DEBE proporcionar al menos un test de integración en
`tests/test_reranker.py` marcado con `@pytest.mark.integration` que instancie
`CrossEncoderReranker` con un modelo real y verifique que reordena chunks con scores
distintos. Este test se omite en CI (`not integration`) y solo corre en entornos con
`sentence-transformers` y el modelo descargado.

### Excepción de dominio

**R26** — SI `CrossEncoderReranker.rerank` recibe una lista de chunks vacía,
ENTONCES el sistema DEBE devolver un `RerankResult` con `chunks = []` y
`top_n = 0` sin lanzar excepción ni llamar al modelo cross-encoder.

**R27** — El sistema DEBE NO enmascarar errores propagados por el modelo
cross-encoder: si `sentence-transformers` lanza una excepción al puntuar, el
`CrossEncoderReranker` DEBE dejar propagar esa excepción tal cual (no convertirla
en un `RerankResult` vacío ni silenciarla).

### Exports del paquete

**R28** — El sistema DEBE re-exportar `Reranker`, `PassthroughReranker`,
`CrossEncoderReranker` y `FakeCrossEncoderReranker` desde
`src/wowrag/retrieval/__init__.py`, y re-exportar `RerankResult` desde
`src/wowrag/models.py` (vía su `__all__`), de modo que los consumidores dependan
del paquete/módulo de modelos, no de los módulos internos.
