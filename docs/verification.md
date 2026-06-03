# Verificación — wow-classic-rag

> Cómo demostrar que el trabajo funciona. Léelo antes de declarar `done`.

## Principio

En este proyecto la corrección manda. La verificación tiene dos niveles:
**tests automáticos** (siempre) y **evaluación RAG** (feature `f10`).

## 1. Tests automáticos (pytest)

- Ejecuta: `pytest` (o vía `./init.sh`). Debe pasar al 100%.
- **Un fichero de test por módulo** de `src/wowrag/`.
- **Trazabilidad obligatoria:** cada requisito `R<n>` del `requirements.md` de la
  feature está cubierto por al menos un test. Nombra o comenta el test con el
  `R<n>` que cubre (p. ej. `def test_abstains_below_threshold():  # R4`).
- La lógica se testea con **fakes** inyectados (sin red ni servicios):
  - `FakeEmbeddingProvider` (vectores deterministas).
  - `InMemoryVectorStore`.
  - `FakeLLMProvider` (devuelve un texto fijo o ecoa el prompt).
- Usa `tmp_path` para ficheros temporales. No escribas en el repo.

### Tests de integración (servicios reales)

- Marca con `@pytest.mark.integration` lo que necesite pgvector u Ollama vivos.
- Por defecto se excluyen (`pytest -m "not integration"`); se corren a propósito
  cuando hay entorno. `init.sh` corre la suite no-integration.

## 2. Casos de grounding que SIEMPRE deben testearse (cuando la feature aplica)

- **Abstención:** una pregunta sin contexto suficiente (score < umbral) produce
  `abstained = true` y NO llama al LLM.
- **Citas:** una respuesta no-abstenida incluye al menos una fuente con `url`.
- **Solo-contexto:** el prompt construido contiene únicamente el contexto
  recuperado (verificable inspeccionando el prompt con un `FakeLLMProvider`).

## 3. Evaluación RAG (feature f10)

- Dataset dorado de preguntas con respuesta/fuente esperada y preguntas
  fuera-de-corpus (deben abstenerse).
- Métricas: hit-rate de recuperación, faithfulness/groundedness de la respuesta,
  tasa de abstención correcta. Se genera un reporte ejecutable.

## 4. Checklist antes de `done`

1. `./init.sh` termina en exit 0 y la suite pasa.
2. Todos los `R<n>` de la feature tienen test (trazabilidad).
3. Sin `print()` de debug, sin TODOs sin contexto, sin secretos.
4. `tasks.md` con todas las tasks `[x]`.
5. Resumen movido a `progress/history.md` y `feature-list.json` actualizado.
