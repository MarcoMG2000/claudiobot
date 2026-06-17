# Review — feature f7-llm-provider-ollama

**Veredicto:** APPROVED

> Re-review tras change-round 1. El único bloqueante del veredicto anterior
> (R19 sin test unitario ejecutable) queda **resuelto**. `./init.sh` verde:
> **166 passed, 3 skipped, exit 0**.

## Trazabilidad requirements ↔ tests

- R1: [x] cubierto por `test_llm_interface.py::test_fake_satisfies_protocol`
- R2: [x] cubierto por `test_llm_interface.py::test_generate_returns_string`
- R3: [x] cubierto por `test_llm_interface.py::test_stream_concatenation_equals_generate`
- R4: [x] cubierto por `test_llm_interface.py::test_model_property`
- R5: [x] cubierto por `test_llm_ollama.py::test_generate_roundtrip` (@integration, requiere Ollama vivo)
- R6: [x] cubierto por `test_llm_ollama.py::test_generate_roundtrip` (@integration)
- R7: [x] cubierto por `test_llm_ollama.py::test_generate_stream_roundtrip` (@integration)
- R8: [x] cubierto por `test_llm_interface.py::test_ollama_module_importable_without_httpx`
- R9: [x] cubierto por `test_llm_interface.py::test_ollama_instantiation_raises_without_httpx`
- R10: [x] cubierto por `test_llm_ollama.py::test_unreachable_server_raises` (@integration; no requiere Ollama vivo, sí httpx)
- R11: [x] cubierto por `test_llm_interface.py::test_empty_prompt_raises` + `test_llm_ollama.py::test_empty_prompt_no_request`
- R12: [x] defaults del constructor (`qwen2.5:7b-instruct`, `http://localhost:11434`) coherentes con Settings; verificable en `src/wowrag/llm/ollama.py:40-41` y ejercitado por `test_llm_ollama.py::test_generate_roundtrip`
- R13: [x] cubierto por `test_config.py::test_ollama_url_and_llm_model_overridable_from_env`
- R14: [x] cubierto por `test_llm_interface.py::test_generate_returns_string` (import sin httpx confirma sin red)
- R15: [x] cubierto por `test_llm_interface.py::test_generate_deterministic`
- R16: [x] cubierto por `test_llm_interface.py::test_stream_concatenation_equals_generate`
- R17: [x] cubierto por `test_llm_interface.py::test_empty_prompt_raises` + `test_llm_interface.py::test_stream_empty_prompt_raises`
- R18: [x] cubierto por `test_llm_interface.py::test_empty_prompt_raises` (verifica que se lanza `LLMError`)
- R19: [x] **RESUELTO** — cubierto por `test_llm_interface.py::test_generate_invalid_schema_raises_llm_error`.
  Test network-free: `monkeypatch.setitem(sys.modules, "httpx", fake_httpx)` con un
  `fake_resp.json()` que devuelve `{"model": "fake", "done": True}` (sin clave
  `response`); ejercita la rama KeyError de `src/wowrag/llm/ollama.py:99-104` y
  asserta `LLMError` (match `"Unexpected Ollama response schema"`). **Verificado
  que CORRE y pasa** en este entorno sin `httpx` ni `pytest_localserver` instalados
  en `.venv` (ejecución aislada: `1 passed`; no se omite).
- R20: [x] cubierto por `test_llm_ollama.py::test_model_property_no_network` (@integration, no requiere Ollama vivo)
- R21: [x] cubierto implícitamente por todos los tests que hacen `from wowrag.llm import ...`

**Brecha previa cerrada.** La rama `data["response"]` missing/KeyError en
`OllamaLLM.generate` (líneas 98-104) ahora tiene cobertura unitaria ejecutable.
El test `test_llm_ollama.py::test_invalid_response_schema_raises` basado en
`pytest_localserver` fue retirado y sustituido por el unitario con monkeypatch
(ver comentario en `test_llm_ollama.py:137-143`).

## Tasks completas

- T1: [x]
- T2: [x]
- T3: [x]
- T4: [x]
- T5: [x]
- T6: [x] (incluye el nuevo `test_generate_invalid_schema_raises_llm_error` para R19)
- T7: [x]
- T8: [x] (caso `test_invalid_response_schema_raises` de localserver retirado; R19 cubierto por unitario)
- Z1: [x]

## Checkpoints

- C1: [x] Archivos base presentes; `./init.sh` exit 0 — **166 passed, 3 skipped** (verificado en esta re-review)
- C2: [x] Una sola feature en `in_progress` (f7); resto `done`/`pending`; tests previos pasan
- C3: [x] `src/wowrag/llm/` respeta capas; `httpx` aislado en `requirements-llm.txt` (no en `requirements.txt`/`init.sh`); `config.py` NO modificado por f7; `models.py` NO modificado por f7 (su diff es f5/f6); `generation/` intacto respecto a este round; sin `print()` de debug
- C4: [x] Tests unitarios con fakes (sin red); integración marcada `@pytest.mark.integration` + module `importorskip("httpx")`; `pytest -m "not integration"` en scope f7: **10 passed, 1 skipped** (el skip es el módulo de integración, no un test de requisito)
- C5: [ ] No aplica a f7 (capa de abstracción, no orquestación; abstención/citas son f8)
- C6: [x] `specs/f7-llm-provider-ollama/` con los 3 ficheros; EARS estricto; tasks todas `[x]`; R1–R21 cubiertos (R19 ahora con test unitario ejecutable)

## Scope / no-regresión (verificado en esta re-review)

- Round 1 tocó **solo** `tests/test_llm_interface.py` y `tests/test_llm_ollama.py` (territorio de tests de f7). Sin código de implementación cambiado: `src/wowrag/llm/ollama.py:98-104` ya envolvía `KeyError`/`ValueError`/`TypeError` → `LLMError`; el fix fue puramente del lado del test.
- No se tocaron ficheros de f6 (`src/wowrag/generation/prompt_builder*.py`) en este round.
- `src/wowrag/config.py` NO modificado. `src/wowrag/models.py` NO modificado por f7 (su diff añade `RetrievedChunk`/`RetrievalResult`/`Source`/`BuiltPrompt`, que son f5/f6).
- `feature-list.json`: f7 sigue en `in_progress` (no editado por el implementer; el cambio de estado lo hace leader/reviewer).
- Los 3 skips de `init.sh` son `importorskip` de dependencias opcionales (FlagEmbedding/f3, httpx/f7-integración, psycopg/f4); ninguno es un test de requisito silenciado.

## Cambios requeridos

Ninguno. El bloqueante de R19 está resuelto y no se detectan regresiones.
