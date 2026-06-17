# Design — f10-evaluation-harness

> CÓMO se construye el arnés de evaluación. f10 es un flujo **offline de
> evaluación** que COMPONE el `RagOrchestrator` de f8: ejecuta un dataset dorado
> contra el pipeline y agrega métricas en un reporte. Vive en su propio paquete
> `src/wowrag/eval/`, igual que `index/` alberga el flujo offline de indexado
> fuera de las capas de paso (`docs/architecture.md` §6; precedente
> `index/pipeline.py`). Respeta las convenciones: interfaz/Protocol donde haya
> swap point, modelos pydantic tipados, `from __future__ import annotations`,
> dependencia SOLO de interfaces, imports pesados perezosos, tests con fakes.

## 0. Decisión de entrega: 2 slices encadenados (PR-size)

f10 es más grande que f8: introduce un paquete nuevo con esquema + loader + tres
métricas + runner + reporte + CLI + fixture + sus tests. Estimación:

| Artefacto | Líneas aprox. |
|-----------|---------------|
| `eval/models.py` (`GoldenItem`, `EvalReport`) | ~70 |
| `eval/dataset.py` (`load_golden` + validación JSONL) | ~55 |
| `eval/metrics.py` (hit-rate, faithfulness proxy, abstención, juez-LLM hook) | ~140 |
| `eval/harness.py` (`EvalHarness.run`) | ~70 |
| `eval/data/golden.jsonl` (fixture) | ~6 |
| `eval/__main__.py` + `eval/cli.py` (entrypoint, composición perezosa) | ~80 |
| `eval/__init__.py` (re-exports) | ~15 |
| `tests/test_eval_dataset.py` | ~70 |
| `tests/test_eval_metrics.py` | ~150 |
| `tests/test_eval_harness.py` | ~90 |
| `tests/test_eval_cli.py` | ~60 |
| **Total estimado** | **~805 líneas** — supera el presupuesto de 400. |

**Recomendación: 2 slices encadenados** (work-unit commits; la numeración `R<n>`
es estable e independiente del troceo):

- **Slice A — dataset + métricas + runner (núcleo determinista, ~430 líneas).**
  `eval/models.py`, `eval/dataset.py`, `eval/metrics.py`, `eval/harness.py`,
  `eval/data/golden.jsonl`, `eval/__init__.py` (parcial) + `test_eval_dataset.py`,
  `test_eval_metrics.py`, `test_eval_harness.py`. Cubre R1–R21, R27, R29, R30
  (parcial). Todo computable con fakes, sin tocar red. *(Si el revisor exige
  estrictamente ≤400, el juez-LLM proxy de métricas — R15–R17 — puede separarse a
  un sub-slice A2 de ~60 líneas; queda a criterio del implementer.)*
- **Slice B — CLI / reporte ejecutable + composición perezosa (~140 líneas).**
  `eval/__main__.py`, `eval/cli.py`, completar `eval/__init__.py` +
  `test_eval_cli.py`. Cubre R22–R26, R28, R30 (final). Depende de Slice A.

El implementer debe aplicar la estrategia de entrega cacheada del leader. Por
defecto: Slice A primero (PR encadenado), Slice B después.

## 1. Archivos a tocar / crear

```
src/
  wowrag/
    eval/
      __init__.py        # NUEVO — re-exporta GoldenItem, load_golden, EvalHarness, EvalReport, métricas
      models.py          # NUEVO — GoldenItem, EvalReport (+ submodelos de métricas)
      dataset.py         # NUEVO — load_golden(path) (lee/valida JSONL)
      metrics.py         # NUEVO — retrieval_hit_rate, faithfulness_proxy, abstention_scores, juez-LLM hook
      harness.py         # NUEVO — EvalHarness (compone RagOrchestrator; run() -> EvalReport)
      cli.py             # NUEVO — parse args + compone orquestador real (lazy) + imprime/escribe reporte
      __main__.py        # NUEVO — `python -m wowrag.eval` -> cli.main()
      data/
        golden.jsonl     # NUEVO — fixture commiteado (in-corpus + fuera-de-corpus)
tests/
  test_eval_dataset.py   # NUEVO — esquema GoldenItem + load_golden (validación JSONL, fixture)
  test_eval_metrics.py   # NUEVO — las tres métricas + juez-LLM con fake (funciones puras)
  test_eval_harness.py   # NUEVO — EvalHarness con RagOrchestrator fake (run end-to-end, sin red)
  test_eval_cli.py       # NUEVO — entrypoint con orquestador fake inyectado; stdout + artefacto JSON
```

Notas:
- **`config.py`** solo se EDITA si se añade el campo opcional `eval_dataset_path`
  (R28); es opcional y con default sano (ver §9). No se altera ninguna clave
  existente. Si el implementer prefiere pasar la ruta solo por argumento de CLI,
  puede omitir el campo y `config.py` no se toca — ambas opciones satisfacen R28.
- **`models.py`** (el global) NO se toca: los modelos de f10 viven en
  `eval/models.py` (ver §2). `Answer`/`Source` se IMPORTAN de `wowrag.models`.
- `eval/data/golden.jsonl` se EMPAQUETA con el paquete (igual que `personas/*.yaml`
  se cargan vía `Path(__file__).parent`); el loader lo resuelve relativo al
  paquete para el default.

## 2. Ubicación del módulo: `src/wowrag/eval/` (flujo offline de evaluación)

Decisión: el arnés vive en **`src/wowrag/eval/`**, un paquete propio — NO en
`rag/`, NI en `api/`.

Justificación (`docs/architecture.md` §3, §6; `docs/verification.md` §3):
- f10 es un **flujo que compone varias capas en modo offline** (carga dataset →
  ejecuta orquestador → agrega métricas → reporte), exactamente el mismo papel
  estructural que `index/` (que compone loader+chunker+embedder+store offline y
  por eso NO vive en `ingest/` ni `store/`). El paralelo justifica un paquete
  propio `eval/`.
- `docs/verification.md` §3 nombra la "Evaluación RAG (feature f10)" como un nivel
  de verificación separado de los tests unitarios; un paquete `eval/` propio lo
  refleja.
- Meterlo en `rag/` mezclaría el **orquestador** (producción) con su **evaluador**
  (herramienta de calidad); el revisor rechaza mezcla de responsabilidades.
  Meterlo en `api/` lo acoplaría a HTTP, que está fuera de alcance.

## 3. Esquema del dataset: `GoldenItem` (R1–R3)

`src/wowrag/eval/models.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator


class GoldenItem(BaseModel):
    """Un caso del dataset dorado de evaluación.

    in_corpus=True  -> la respuesta está en el corpus; debe NO abstenerse y citar
                       al menos una de expected_urls (hit-rate).
    in_corpus=False -> pregunta fuera-de-corpus; el sistema DEBE abstenerse.
    """

    question: str
    expected_urls: list[str] = []
    in_corpus: bool
    reference_answer: str | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must be a non-empty string")
        return v

    @model_validator(mode="after")
    def _coherent_labels(self) -> "GoldenItem":
        # R2: un item in-corpus sin fuente esperada no es evaluable para hit-rate.
        if self.in_corpus and not self.expected_urls:
            raise ValueError("in_corpus item must declare at least one expected_url")
        # R3: una pregunta fuera-de-corpus no puede declarar fuentes esperadas.
        if not self.in_corpus and self.expected_urls:
            raise ValueError("out-of-corpus item must not declare expected_urls")
        return self
```

### Formato del fichero: JSONL (R4, R5)

Decisión: **JSONL** (un objeto JSON por línea), no un único array JSON ni YAML.
Razones:
- **Append-friendly / diff-friendly:** añadir un caso es una línea nueva; el diff
  de PR es mínimo y legible (alineado con `work-unit-commits` y revisiones ≤400).
- **Streaming-friendly:** el loader valida línea a línea y puede señalar la línea
  exacta que falla (R4).
- Consistente con el ecosistema de eval (datasets dorados suelen ser JSONL).

`src/wowrag/eval/data/golden.jsonl` (fixture commiteado, R5):

```jsonl
{"question": "What does Fireball do?", "expected_urls": ["https://www.wowhead.com/classic/spell=133/fireball"], "in_corpus": true, "reference_answer": "Fireball hurls a fiery ball that deals fire damage."}
{"question": "How much mana does Frostbolt cost at rank 1?", "expected_urls": ["https://www.wowhead.com/classic/spell=116/frostbolt"], "in_corpus": true, "reference_answer": "Frostbolt rank 1 costs 25 mana."}
{"question": "What is the best pizza topping in Azeroth?", "expected_urls": [], "in_corpus": false, "reference_answer": null}
{"question": "Who won the 2026 FIFA World Cup?", "expected_urls": [], "in_corpus": false, "reference_answer": null}
```

> Las URLs/respuestas del fixture son ilustrativas: el camino por defecto NO las
> verifica contra un corpus real (no hay corpus hasta f11). Sirven para ejercitar
> el esquema, el loader y las métricas con un `RagOrchestrator` fake cuyos
> `Answer` se controlan en el test.

## 4. Loader: `load_golden(path)` (R4)

`src/wowrag/eval/dataset.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from wowrag.eval.models import GoldenItem

_DEFAULT_DATASET = Path(__file__).parent / "data" / "golden.jsonl"


class GoldenDatasetError(Exception):
    """Raised when the golden dataset file is malformed (identifies the line)."""


def load_golden(path: str | Path | None = None) -> list[GoldenItem]:
    """Load and validate a golden JSONL dataset.

    path=None -> the committed default fixture (eval/data/golden.jsonl).
    Each non-blank line must be a JSON object valid against GoldenItem.
    A malformed/invalid line raises GoldenDatasetError naming the 1-based line.
    """
    src = Path(path) if path is not None else _DEFAULT_DATASET
    items: list[GoldenItem] = []
    for lineno, raw in enumerate(src.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # blank lines tolerated
        try:
            data = json.loads(line)
            items.append(GoldenItem(**data))
        except Exception as exc:  # JSON error or pydantic ValidationError
            raise GoldenDatasetError(f"invalid golden item at line {lineno}: {exc}") from exc
    return items
```

Decisión: líneas en blanco se toleran; cualquier línea con contenido inválido
(JSON roto o que falla la validación de `GoldenItem`, incl. R2/R3) eleva
`GoldenDatasetError` nombrando la línea (R4). No se silencia ni se salta.

## 5. Métricas (R8–R21) — funciones puras sobre `list[(GoldenItem, Answer)]`

`src/wowrag/eval/metrics.py`. Todas las métricas son **funciones puras** que toman
los pares `(item, answer)` ya producidos por el runner; no llaman al orquestador,
no recuperan, no embeben (R11, R21). Devuelven submodelos de métricas (o `None`
para "no aplicable").

### 5.1 Retrieval hit-rate (R8–R11)

```
hit(item, answer)   = (set(item.expected_urls) ∩ {s.url for s in answer.sources}) ≠ ∅      (R9)
items_in_corpus     = [pares con item.in_corpus is True]
hit_rate            = (# items_in_corpus con hit) / len(items_in_corpus)                    (R8)
                    = None   si len(items_in_corpus) == 0                                   (R10)
```

Comparación exacta de URL (igualdad de string). Solo sobre items in-corpus.
Derivado SOLO de `answer.sources` (R11).

### 5.2 Faithfulness proxy determinista (R12–R14) — DECISIÓN CLAVE

**Decisión:** el camino por defecto de faithfulness es un **proxy determinista,
sin LLM**, computable como función pura. Un juez-LLM "de verdad" requiere un
modelo vivo, lo que rompería el contrato de `./init.sh` (sin red/Ollama). Por
tanto el default es el proxy; el juez-LLM es un *hook* opcional (§5.4).

Definición del proxy para un par no-abstenido `(item, answer)`:

```
# (a) presencia de cita — propiedad nº1 del proyecto (grounding):
cited = len(answer.sources) >= 1                                  ∈ {0.0, 1.0}   (R13a)

# (b) solapamiento léxico:
def tokens(s): return set(w for w in re.findall(r"[a-z0-9]+", s.lower())
                          if w not in STOPWORDS)                                  (R13)
ref = item.reference_answer
if ref:    overlap = |tokens(answer.answer) ∩ tokens(ref)| / max(1, |tokens(ref)|)
else:      overlap = (proxy degradado: 1.0 si cited else 0.0)    # sin referencia
                                                                                 (R13b)

faithfulness(item, answer) = 0.5 * (1.0 if cited else 0.0) + 0.5 * overlap        (R13)
```

- **Normalización documentada (R13):** minúsculas; tokenización por `[a-z0-9]+`;
  `STOPWORDS` = un conjunto pequeño en inglés/español (the, a, of, el, la, de, …)
  declarado como constante de módulo. El resultado está en `[0, 1]`.
- **Cuándo no hay `reference_answer`:** el solapamiento léxico no tiene referencia
  contra la que medir; el proxy degrada a la señal de cita (overlap = `1.0` si hay
  cita, `0.0` si no). Esto mantiene la métrica computable y monótona con el
  grounding. (Alternativa medir contra el contexto citado: descartada porque f8
  no expone el texto del contexto en `Answer`, solo las `Source`; ver §11.)
- **Abstención excluida (R14):** los `Answer` con `abstained == True` NO entran en
  el promedio de faithfulness; el reporte cuenta `excluded_abstained`. Medir
  faithfulness sobre una abstención no tiene sentido (no fundamenta nada).

`faithfulness_proxy_mean(pairs) -> float | None` promedia sobre los pares
no-abstenidos; `None` si todos abstuvieron.

### 5.3 Abstención: precisión y recall (R18–R21)

```
out_of_corpus   = [pares con item.in_corpus is False]
abstained_pairs = [pares con answer.abstained is True]
correct_abst    = [pares en out_of_corpus con answer.abstained is True]           (R18)

abstention_recall    = len(correct_abst) / len(out_of_corpus)                     (R19)
                     = None  si len(out_of_corpus) == 0                           (R20)
abstention_precision = len(correct_abst) / len(abstained_pairs)                   (R19)
                     = None  si len(abstained_pairs) == 0                         (R20)
```

Derivado SOLO de `answer.abstained` (R21). (Un item in-corpus que abstiene es un
falso positivo de abstención: baja la precisión; un item fuera-de-corpus que NO
abstiene es un falso negativo: baja la recall.)

### 5.4 Juez-LLM opcional (R15–R17) — hook desacoplado

```python
def faithfulness_llm_judge(
    pairs: list[tuple[GoldenItem, Answer]],
    llm: LLMProvider,          # interfaz de f7; inyectada, fakeable
) -> float | None:
    """Score faithfulness via an injected LLMProvider (optional).

    Builds a judge prompt per non-abstained answer asking for a [0,1] score,
    parses the score, returns the mean. NOT called unless a judge is provided.
    """
```

- **Inyección, no instanciación (R15, R16):** el juez recibe un `LLMProvider` ya
  construido. `metrics.py` NO importa `OllamaLLM` (import perezoso solo en la CLI
  si se pide juez real). Importar `wowrag.eval` jamás contacta Ollama (R16).
- **Default sin juez (R16):** `EvalHarness.run` solo invoca el juez si se le pasó
  uno; por defecto `EvalReport.faithfulness_llm` es `None` y el reporte usa el
  proxy.
- **Test con fake (R17):** se testea con `FakeLLMProvider` (f7) configurado para
  devolver, p. ej., `"0.8"`; el parser extrae el float. Solo la variante contra
  Ollama real lleva `@pytest.mark.integration`.

## 6. Runner: `EvalHarness` (R6, R7)

`src/wowrag/eval/harness.py`:

```python
from __future__ import annotations

from wowrag.eval.metrics import (
    abstention_scores, faithfulness_proxy_mean, faithfulness_llm_judge,
    retrieval_hit_rate,
)
from wowrag.eval.models import EvalReport, GoldenItem
from wowrag.llm.base import LLMProvider
from wowrag.models import Answer
from wowrag.rag.base import RagOrchestrator   # la INTERFAZ (Protocol), no la impl


class EvalHarness:
    """Runs a golden dataset through a RagOrchestrator and aggregates metrics.

    Depends only on the RagOrchestrator Protocol (R6): testable with a fake
    orchestrator, no Postgres/GPU/Ollama/network.
    """

    def __init__(self, orchestrator: RagOrchestrator) -> None:
        self._orchestrator = orchestrator

    def run(
        self,
        items: list[GoldenItem],
        judge: LLMProvider | None = None,   # optional LLM judge (R15, R16)
    ) -> EvalReport:
        pairs: list[tuple[GoldenItem, Answer]] = [
            (item, self._orchestrator.answer(item.question))   # one call/item (R7)
            for item in items
        ]
        return EvalReport(
            total=len(pairs),
            hit_rate=retrieval_hit_rate(pairs),                       # R8-R11
            faithfulness_proxy=faithfulness_proxy_mean(pairs),       # R12-R14
            faithfulness_llm=(faithfulness_llm_judge(pairs, judge)   # R15-R17
                              if judge is not None else None),
            **abstention_scores(pairs),  # precision/recall + counts  # R18-R21
        )
```

- **Solo el Protocol (R6):** el constructor toma `RagOrchestrator`, nunca
  `DefaultRagOrchestrator`. Tests inyectan un fake.
- **Una llamada por item (R7):** `answer(item.question)` exactamente una vez por
  `GoldenItem`; el `Answer` se conserva sin mutar.
- **Persona:** el runner llama `answer(question)` con persona por defecto (la
  faithfulness/grounding no depende del estilo de persona). Persona configurable
  queda fuera de alcance de f10.

## 7. Reporte: `EvalReport` (R22, R23)

`src/wowrag/eval/models.py`:

```python
class EvalReport(BaseModel):
    """Aggregated evaluation report; JSON-serializable (R23)."""

    total: int                              # items evaluados
    in_corpus: int                          # # items in-corpus
    out_of_corpus: int                      # # items fuera-de-corpus
    excluded_abstained: int                 # # excluidos del faithfulness (R14)

    hit_rate: float | None                  # R8-R11 (None si no aplica)
    faithfulness_proxy: float | None        # R12-R14 (None si todos abstuvieron)
    faithfulness_llm: float | None          # R15-R17 (None si no se usó juez)
    abstention_precision: float | None      # R19, R20
    abstention_recall: float | None         # R19, R20
```

- **JSON estable (R23):** `report.model_dump_json(indent=2)` produce el artefacto.
- Los conteos (`in_corpus`, `out_of_corpus`, `excluded_abstained`) los puede
  rellenar `abstention_scores`/`faithfulness_proxy_mean` o calcularse en `run`;
  el implementer elige, manteniendo cada campo trazable a su `R<n>`.

## 8. CLI / entrypoint: `python -m wowrag.eval` (R24–R26)

`src/wowrag/eval/cli.py` + `src/wowrag/eval/__main__.py`.

```python
# __main__.py
from wowrag.eval.cli import main
raise SystemExit(main())
```

```python
# cli.py (esquema)
from __future__ import annotations

import argparse
from pathlib import Path

from wowrag.eval.dataset import load_golden
from wowrag.eval.harness import EvalHarness
from wowrag.rag.base import RagOrchestrator


def _build_orchestrator() -> RagOrchestrator:
    """Real composition point — LAZY heavy imports (R26).

    Reuses f9's build_orchestrator (bge-m3 + pgvector + Ollama). Imported INSIDE
    the function so `import wowrag.eval` never pulls torch/psycopg/httpx (R26).
    """
    from wowrag.api.dependencies import build_orchestrator
    return build_orchestrator()


def main(
    argv: list[str] | None = None,
    orchestrator: RagOrchestrator | None = None,   # injectable for tests (R29)
) -> int:
    parser = argparse.ArgumentParser(prog="python -m wowrag.eval")
    parser.add_argument("--dataset", type=Path, default=None)  # None -> fixture
    parser.add_argument("--out", type=Path, default=None)      # JSON artifact (R25)
    args = parser.parse_args(argv)

    items = load_golden(args.dataset)
    orch = orchestrator if orchestrator is not None else _build_orchestrator()
    report = EvalHarness(orch).run(items)

    print(_format_summary(report))                 # stdout summary (R24)
    if args.out is not None:                        # R25
        args.out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return 0
```

- **Composición perezosa (R26):** `build_orchestrator` (de `wowrag.api.dependencies`,
  f9) ya hace lazy-import de bge-m3/pgvector/Ollama. La CLI lo reutiliza dentro de
  `_build_orchestrator`, que a su vez es lazy. Reusar el punto de composición de f9
  evita duplicar el wiring real (DRY) y respeta el grounding/config de producción.
- **Inyectable (R29):** `main(argv, orchestrator=...)` permite a `test_eval_cli.py`
  pasar un orquestador fake y NUNCA tocar `_build_orchestrator` ni red.
- **Resumen stdout (R24)** + **artefacto JSON opcional (R25)** vía `--out`.
- El `__main__.py` mantiene `python -m wowrag.eval` operativo.

## 9. Config: campo opcional `eval_dataset_path` (R28)

Decisión: **mínima**. O bien (preferido) la ruta del dataset se pasa por
`--dataset` y `config.py` NO se toca; o bien se añade UN campo opcional a
`Settings`:

```python
eval_dataset_path: str | None = None   # None -> fixture commiteado por defecto
```

En ningún caso se modifican claves existentes ni se exigen variables de entorno
para el camino por defecto (R28). El implementer elige; si añade el campo, la CLI
puede usarlo como default cuando `--dataset` no se pasa.

## 10. Estrategia de tests (todos DB-free / GPU-free / network-free; corren con `init.sh`)

Trazabilidad `R<n>` ↔ test obligatoria (comenta cada test con su `R<n>`,
`docs/verification.md` §1). Fakes:

- **`FakeOrchestrator`** (implementa el Protocol `RagOrchestrator`): un stub
  construido en el test que mapea `question -> Answer` predefinido, para controlar
  `sources`/`abstained`/`answer` deterministamente. Vive en el test (o en un
  `conftest`), no en `src/`.
- **`FakeLLMProvider`** (f7, ya existe) para el juez-LLM (R17).

- `tests/test_eval_dataset.py` (esquema + loader):
  - `test_golden_item_fields`: `GoldenItem` con los 4 campos se construye (R1).
  - `test_in_corpus_requires_expected_urls`: in-corpus sin `expected_urls` →
    ValidationError (R2).
  - `test_out_of_corpus_rejects_expected_urls`: fuera-de-corpus con `expected_urls`
    → ValidationError (R3).
  - `test_load_golden_parses_jsonl`: dataset JSONL válido (vía `tmp_path`) →
    `list[GoldenItem]` (R4).
  - `test_load_golden_malformed_line_raises`: línea rota → `GoldenDatasetError`
    nombrando la línea (R4).
  - `test_default_fixture_loads`: `load_golden()` (default) carga el fixture
    commiteado con ≥1 in-corpus y ≥1 fuera-de-corpus (R5).
- `tests/test_eval_metrics.py` (funciones puras):
  - `test_hit_rate_counts_url_intersection`: hit cuando `expected_urls ∩
    sources.url ≠ ∅` (R9); fracción correcta (R8); solo in-corpus.
  - `test_hit_rate_none_when_no_in_corpus`: sin items in-corpus → `None` (R10).
  - `test_hit_rate_only_from_sources`: cambia `sources`, cambia hit-rate; no
    re-recupera (R11).
  - `test_faithfulness_proxy_cited_and_overlap`: respuesta citada con alto
    solapamiento contra `reference_answer` → score alto; sin cita o sin
    solapamiento → score bajo; rango `[0,1]` (R12, R13).
  - `test_faithfulness_excludes_abstained`: un `Answer` abstenido no entra en la
    media y se cuenta en `excluded_abstained` (R14).
  - `test_faithfulness_proxy_is_deterministic`: misma entrada → mismo score, sin
    red (R12).
  - `test_abstention_precision_recall`: dataset con TP/FP/FN de abstención →
    precisión y recall correctas (R18, R19).
  - `test_abstention_none_when_no_out_of_corpus` / `_when_no_abstentions`: bordes →
    `None` (R20).
  - `test_abstention_only_from_flag`: derivada solo de `answer.abstained` (R21).
  - `test_faithfulness_llm_judge_with_fake`: con `FakeLLMProvider` que devuelve un
    score parseable → media correcta (R15, R17).
  - `test_judge_not_called_by_default`: sin juez, `faithfulness_llm` es `None` y no
    se instancia ningún LLM (R16).
- `tests/test_eval_harness.py` (`EvalHarness`):
  - `test_run_calls_orchestrator_once_per_item`: spy de `RagOrchestrator` cuenta 1
    llamada por `GoldenItem` (R7).
  - `test_run_produces_report`: con `FakeOrchestrator` → `EvalReport` con todas las
    métricas agregadas (R6, R22).
  - `test_run_depends_only_on_protocol`: `EvalHarness` se construye con un stub que
    solo implementa el Protocol `RagOrchestrator` (R6, R29).
  - `test_report_json_serializable`: `report.model_dump_json()` produce JSON
    estable (R23).
- `tests/test_eval_cli.py` (entrypoint):
  - `test_main_prints_summary`: `main([], orchestrator=fake)` imprime un resumen y
    devuelve 0 (R24); usa el fixture por defecto.
  - `test_main_writes_json_artifact`: `main(["--out", p], orchestrator=fake)`
    escribe `EvalReport` JSON en `tmp_path` (R25).
  - `test_main_does_not_build_real_orchestrator_when_injected`: con orquestador
    inyectado, `_build_orchestrator` NUNCA se llama (R26, R29).
  - `test_import_eval_is_network_free`: `import wowrag.eval` y `import
    wowrag.eval.cli` no importan torch/psycopg/httpx ni contactan red (R16, R26).
  - `test_exports`: `from wowrag.eval import GoldenItem, load_golden, EvalHarness,
    EvalReport` funciona (R30).

## 11. Alternativas descartadas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Modelos de f10 en `models.py` global | `models.py` es para modelos de DATOS del pipeline (`Document`…`Answer`); el arnés es una herramienta de calidad. Precedente: `index/` vive aparte. Un paquete `eval/` propio mantiene las capas limpias |
| Faithfulness por defecto = juez-LLM (Ollama) | Rompe `./init.sh` (sin red/Ollama) y hace los tests no deterministas. El default debe ser el proxy determinista; el juez-LLM es opcional e `@integration` (R12, R16, R17) |
| Faithfulness proxy mide la respuesta contra el TEXTO del contexto recuperado | `Answer` (f8) NO expone el texto de los chunks, solo `Source` ({n,title,url}). Medir contra el contexto exigiría cambiar f8 (fuera de alcance, R27). El proxy mide contra `reference_answer` y degrada a la señal de cita si no hay referencia |
| Dataset como array JSON único o YAML | JSONL es append/diff/streaming-friendly y permite señalar la línea exacta que falla (R4); mejor para PRs ≤400 y revisión |
| `EvalHarness` instancia `DefaultRagOrchestrator` por dentro | Acoplaría el arnés a la impl concreta y a la red/DB; debe depender solo del Protocol e inyectarse (R6, R29) |
| CLI compone bge-m3/pgvector/Ollama con imports al tope del módulo | Importar `wowrag.eval` arrastraría torch/psycopg/httpx; deben ser lazy dentro de la función de composición, reutilizando `build_orchestrator` de f9 (R26) |
| Duplicar el wiring real del orquestador en `eval/cli.py` | f9 ya expone `build_orchestrator` (lazy, single composition point); reutilizarlo evita divergencia de config/grounding (DRY) |
| Nuevo endpoint HTTP `POST /eval` | HTTP es f9; f10 es script/librería. Un endpoint acoplaría evaluación a transporte (fuera de alcance) |
| f10 recalcula el umbral o inspecciona internals del orquestador para abstención | La señal autoritativa es `Answer.abstained` (f8 ya la computó). f10 la consume, no la recalcula (R21) |
| Añadir BLEU/ROUGE/embeddings de similitud al proxy | Dependencias pesadas en el camino por defecto; el proxy léxico con stdlib basta y mantiene `./init.sh` ligero (alcance, R12) |
| Modificar claves existentes de `Settings` para la eval | Rompería config de f0–f9; f10 solo añade campos opcionales con default sano, o usa argumentos de CLI (R28) |
