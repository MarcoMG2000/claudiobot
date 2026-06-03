# Arquitectura — wow-classic-rag

> Qué significa "hacer un buen trabajo" en este proyecto. Léelo antes de
> redactar specs o implementar.

## 1. Objetivo

Un chatbot RAG **autoalojado** que responde preguntas sobre WoW Classic
**exclusivamente** a partir de contenido de wowhead. La prioridad nº1 es la
**corrección**: si la evidencia recuperada no respalda una respuesta, el sistema
**se abstiene** y lo dice con claridad. Nunca inventa.

API primero; el frontend (uso dentro del juego) llega después, pero el backend
debe diseñarse para integrarse con él (respuestas estructuradas, CORS, persona
seleccionable por petición).

## 2. Stack (decidido)

| Capa            | Elección                                                       |
|-----------------|----------------------------------------------------------------|
| Lenguaje        | Python 3.11+                                                    |
| API             | FastAPI + uvicorn                                              |
| Embeddings      | `BAAI/bge-m3` (multilingüe, GPU)                               |
| Vector store    | PostgreSQL + `pgvector`                                        |
| LLM             | **Solo local** vía Ollama (por defecto `qwen2.5:7b-instruct`)  |
| Configuración   | `pydantic-settings` + ficheros de persona                      |
| Tests           | `pytest`                                                        |

Idioma: **multilingüe** (ES/EN). El corpus de wowhead es mayormente inglés; las
preguntas y personas pueden ser en español.

## 3. Pipeline RAG y flujo de datos

```
                 (offline, indexado)
 corpus local ─► loader ─► chunking ─► embeddings ─► pgvector (upsert)
                                                          │
                 (online, consulta)                       ▼
 pregunta ─► embeddings ─► retriever (top-k + score) ─► prompt builder
                                       │                     │
                                       ▼                     ▼
                          ¿score < umbral?            persona + grounding
                                       │                     │
                                  abstención ◄──────── LLM (Ollama) ─► respuesta
                                                              │
                                                              ▼
                                              respuesta + citas (URLs) + metadata
```

## 4. Componentes y puntos de intercambio (swap points)

Todo componente externo vive **detrás de una interfaz** (Protocol/ABC). Las
implementaciones concretas se eligen por configuración. Esto cumple el objetivo
del usuario de "cambiar cosas por config" y mantiene los tests sin servicios
vivos (se inyectan fakes).

- `EmbeddingProvider` → impl `BgeM3Embeddings`, fake en tests.
- `VectorStore` → impl `PgVectorStore`, fake/in-memory en tests.
- `LLMProvider` → impl `OllamaLLM`, fake en tests.
- `Persona` / estilo → ficheros de configuración cargables (simple, Orc, Troll…).
- `Retriever`, `PromptBuilder`, `RagOrchestrator` son lógica propia, testeable
  sin red usando los fakes anteriores.

## 5. Contrato de grounding (no negociable)

1. El LLM recibe **solo** el contexto recuperado; se le instruye a responder
   únicamente con él.
2. Si el mejor score de recuperación está por debajo del umbral configurado, el
   orquestador **se abstiene** sin llamar al LLM (o el LLM debe declarar que no
   hay evidencia). Mensaje claro tipo: "No hay evidencia suficiente en los
   documentos para responder con seguridad."
3. Toda respuesta no-abstenida incluye **citas** (URLs de wowhead) de los chunks
   usados.
4. La metadata de respuesta incluye: modelo, persona, scores de recuperación,
   y si hubo abstención.

## 6. Layout de `src/`

```
src/
  wowrag/
    __init__.py
    config.py            # pydantic-settings, carga de personas
    models.py            # Document, Chunk, RetrievedChunk, Answer (dataclasses/pydantic)
    ingest/
      loader.py          # corpus local (wowhead scraper -> feature posterior)
      chunking.py
    embeddings/
      base.py            # EmbeddingProvider (interfaz)
      bge_m3.py
    store/
      base.py            # VectorStore (interfaz)
      pgvector_store.py
      migrations.sql
    retrieval/
      retriever.py
    generation/
      prompt_builder.py
      base.py            # LLMProvider (interfaz)
      ollama.py
    rag/
      orchestrator.py    # une todo + abstención
    api/
      app.py             # FastAPI: POST /ask, /health
    personas/            # ficheros de persona (yaml/toml)
  ...
```

> El nombre exacto de módulos puede afinarse en cada spec, pero **respeta esta
> separación por capas**. Un revisor rechaza código que mezcle capas (p. ej. SQL
> dentro del orquestador, o llamadas HTTP a Ollama fuera de `generation/`).

## 7. Política de dependencias

A diferencia del template original, **sí** usamos dependencias externas. Reglas:

- `requirements.txt` con **versiones pineadas**.
- Solo lo necesario para la feature en curso (no añadas libs "por si acaso").
- Nada de claves/secretos en el código: van por entorno (`.env`, no commiteado).

## 8. Diseño pensando en el frontend (futuro)

- Respuestas siempre **estructuradas** (JSON con `answer`, `sources`,
  `abstained`, `metadata`).
- Persona seleccionable por petición (`persona` en el body) además de por config.
- CORS configurable. No acoplar lógica a ningún cliente concreto.
