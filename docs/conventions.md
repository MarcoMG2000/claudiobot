# Convenciones — wow-classic-rag

> Reglas de estilo, nombres y estructura. Léelo antes de escribir código.

## Lenguaje y estilo

- Python 3.11+. **Type hints obligatorios** en funciones públicas.
- Formato: `black` + `ruff` (line length 100). Imports ordenados con `ruff`.
- Docstrings breves en módulos y funciones públicas. Comentarios solo donde el
  "por qué" no es obvio; no narres el "qué".
- Nada de `print()` para debug. Usa el `logging` estándar con un logger por módulo
  (`logger = logging.getLogger(__name__)`).

## Nombres

- Módulos y funciones: `snake_case`. Clases: `PascalCase`. Constantes: `UPPER_SNAKE`.
- Interfaces (Protocol/ABC) describen la capacidad: `EmbeddingProvider`,
  `VectorStore`, `LLMProvider`. Implementaciones nombran la tecnología:
  `BgeM3Embeddings`, `PgVectorStore`, `OllamaLLM`.

## Patrón de abstracción (clave del proyecto)

- Cada servicio externo se define como interfaz en `base.py` de su paquete y se
  implementa aparte. El resto del código depende de la **interfaz**, nunca de la
  implementación concreta.
- La selección de implementación ocurre en un único punto de composición
  (factory en `config.py` o un `build_*` explícito), no esparcida por el código.
- Esto permite (a) cambiar backend por config y (b) inyectar fakes en tests.

## Configuración

- Toda configuración via `pydantic-settings` (`Settings`), leyendo de entorno y
  `.env`. Sin valores mágicos hardcodeados (umbral de score, `k`, modelo, dim de
  embedding, DSN de Postgres, URL de Ollama, persona por defecto…).
- Personas/estilos en ficheros de datos (`src/wowrag/personas/*.yaml`), no en
  código. Una persona define al menos: `name`, `system_style` (instrucción de
  estilo) y opcional `language`.
- **Secretos nunca en el repo.** `.env` está en `.gitignore`; se commitea un
  `.env.example`.

## Errores y abstención

- La abstención es una **respuesta válida**, no una excepción. Modélala en el
  tipo de retorno (`Answer.abstained: bool`), no con `raise`.
- Errores de infraestructura (Postgres caído, Ollama no responde) sí son
  excepciones claras; no se enmascaran como respuestas vacías.

## Tests (resumen; detalle en `docs/verification.md`)

- `pytest`. Un fichero de test por módulo de `src/`.
- La lógica (retriever, prompt builder, orquestador, abstención) se testea con
  **fakes** de los providers — sin Postgres, Ollama ni red.
- Los tests que requieren servicios reales (pgvector, Ollama) se marcan
  `@pytest.mark.integration` y se pueden excluir por defecto.
- Usa `tmp_path`/`tempfile` para ficheros; nada de escribir en el repo.

## Citas

- Formato de cita interno estable: cada chunk recuperado conserva su
  `source_url` y `title`; el `PromptBuilder` numera las fuentes `[1], [2]…` y la
  respuesta de la API las devuelve en `sources` con `{n, title, url}`.
