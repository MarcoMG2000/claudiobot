# Tasks — f10-evaluation-harness

> Checklist ordenada para el implementer. Cada task referencia los `R<n>` que
> cubre. Todos los tests del camino por defecto son unitarios con stdlib + fakes:
> un `FakeOrchestrator` (implementa el Protocol `RagOrchestrator`) y, para el juez,
> `FakeLLMProvider` (f7). Sin Postgres, sin GPU, sin Ollama, sin red. La
> trazabilidad `R<n>` ↔ test es obligatoria (`docs/verification.md`); nombra o
> comenta cada test con su `R<n>`.
>
> **Entrega: 2 slices encadenados** (ver `design.md` §0). Estimación total ~805
> líneas, por encima del presupuesto de 400 → NO cabe en un PR único.
> - **Slice A** (núcleo determinista, ~430 líneas): T1–T8 (dataset + métricas +
>   runner + sus tests). Cubre R1–R21, R27, R29, R30 (parcial).
> - **Slice B** (CLI / reporte ejecutable, ~140 líneas): T9–T11 (entrypoint +
>   composición perezosa + su test). Cubre R22–R26, R28, R30 (final).
>
> Aplica la estrategia de entrega que indique el leader. f10 EVALÚA: CONSUME f8
> (`RagOrchestrator.answer`, `Answer`, `Source`) y f7 (`LLMProvider`) por interfaz;
> NO reimplementa f5–f9 ni modifica `config.py` salvo el campo opcional de R28. NO
> introduce HTTP (eso es f9), NO escrapea (f11), NO reordena (f12). El faithfulness
> por defecto es el **proxy determinista** (sin LLM); el juez-LLM es opcional e
> `@integration` para el modelo real.

---

## Slice A — dataset + métricas + runner (núcleo determinista)

### Implementación

- [x] **T1 — Modelo `GoldenItem` en `eval/models.py`.**
  Crear `src/wowrag/eval/models.py` con `GoldenItem(BaseModel)` (ver `design.md`
  §3): `question: str` (validador no-vacío), `expected_urls: list[str] = []`,
  `in_corpus: bool`, `reference_answer: str | None = None`. Añadir un
  `model_validator(mode="after")` que: (a) rechace in-corpus sin `expected_urls`;
  (b) rechace fuera-de-corpus con `expected_urls`. `from __future__ import
  annotations`. (Crear el paquete `eval/` con su `__init__.py` si no existe.)
  _(Cubre R1, R2, R3)_

- [x] **T2 — Loader `load_golden` en `eval/dataset.py`.**
  Crear `src/wowrag/eval/dataset.py` con `GoldenDatasetError(Exception)` y
  `load_golden(path: str | Path | None = None) -> list[GoldenItem]` (ver §4): lee
  JSONL relativo al default `eval/data/golden.jsonl` cuando `path is None`; valida
  línea a línea; tolera líneas en blanco; una línea con JSON roto o que falla la
  validación de `GoldenItem` (incl. R2/R3) eleva `GoldenDatasetError` nombrando la
  línea 1-based. No silenciar ni saltar líneas inválidas.
  _(Cubre R4)_

- [x] **T3 — Fixture commiteado `eval/data/golden.jsonl`.**
  Crear `src/wowrag/eval/data/golden.jsonl` con al menos un item `in_corpus=true`
  (con `expected_urls`) y al menos un item `in_corpus=false` (sin `expected_urls`).
  Formato JSONL (un objeto por línea), ver el ejemplo en `design.md` §3.
  _(Cubre R5)_

- [x] **T4 — Métricas en `eval/metrics.py` (hit-rate + abstención).**
  Crear `src/wowrag/eval/metrics.py` con funciones puras sobre
  `list[tuple[GoldenItem, Answer]]` (ver §5.1, §5.3):
  - `retrieval_hit_rate(pairs) -> float | None`: hit cuando
    `set(item.expected_urls) ∩ {s.url for s in answer.sources}` no es vacío (R9);
    fracción sobre items in-corpus (R8); `None` si no hay in-corpus (R10); derivado
    solo de `answer.sources` (R11).
  - `abstention_scores(pairs) -> dict` con `abstention_precision`,
    `abstention_recall` (R19) — `None` en los bordes (R20) — más los conteos
    `in_corpus`, `out_of_corpus`. Un item es correcto según `in_corpus` vs
    `answer.abstained` (R18); derivado solo de `answer.abstained` (R21).
  _(Cubre R8, R9, R10, R11, R18, R19, R20, R21)_

- [x] **T5 — Faithfulness proxy determinista en `eval/metrics.py`.**
  Añadir a `eval/metrics.py` (ver §5.2): constante `STOPWORDS`; helper de
  tokenización (`[a-z0-9]+`, minúsculas, sin stopwords); `faithfulness_proxy_mean(
  pairs) -> float | None` que, por par no-abstenido, combine presencia de cita
  (0.5) + solapamiento léxico contra `reference_answer` (0.5), degradando a la
  señal de cita cuando no hay `reference_answer`; resultado en `[0,1]`. Excluir los
  `Answer` abstenidos de la media y exponer el conteo `excluded_abstained` (R14).
  Determinista, sin red.
  _(Cubre R12, R13, R14)_

- [x] **T6 — Hook juez-LLM opcional en `eval/metrics.py`.**
  Añadir `faithfulness_llm_judge(pairs, llm: LLMProvider) -> float | None` (ver
  §5.4): recibe un `LLMProvider` ya construido (inyectado, NO instanciado aquí);
  por respuesta no-abstenida construye un prompt de juez que pide un score `[0,1]`,
  parsea el float de la salida y promedia. `metrics.py` NO importa `OllamaLLM`. El
  juez es opcional: el harness solo lo invoca si se le pasa uno.
  _(Cubre R15, R16, R17)_

- [x] **T7 — Modelo `EvalReport` en `eval/models.py`.**
  Añadir a `eval/models.py` `EvalReport(BaseModel)` (ver §7) con: `total`,
  `in_corpus`, `out_of_corpus`, `excluded_abstained`, `hit_rate: float | None`,
  `faithfulness_proxy: float | None`, `faithfulness_llm: float | None`,
  `abstention_precision: float | None`, `abstention_recall: float | None`.
  Serializable a JSON vía pydantic (R23).
  _(Cubre R22, R23)_

- [x] **T8 — Runner `EvalHarness` en `eval/harness.py` + exports parciales.**
  Crear `src/wowrag/eval/harness.py` con `EvalHarness` (ver §6): constructor
  `__init__(self, orchestrator: RagOrchestrator)` (solo el Protocol, R6);
  `run(items, judge: LLMProvider | None = None) -> EvalReport` que llame
  `self._orchestrator.answer(item.question)` exactamente una vez por item (R7),
  conserve cada `Answer` sin mutarlo, y agregue las métricas de T4/T5/T6 en un
  `EvalReport`; el juez solo se invoca si `judge is not None` (R16). Cero imports de
  DB/ML/red. Completar `eval/__init__.py` re-exportando `GoldenItem`,
  `load_golden`, `EvalHarness`, `EvalReport` y las funciones de métricas públicas
  (R30; se finaliza en T11 si la CLI añade símbolos).
  _(Cubre R6, R7, R27, R29, R30 parcial)_

### Tests (Slice A)

- [x] **T-A-tests — Tests del núcleo determinista.**
  Crear (ver `design.md` §10), todos `not integration`, con `tmp_path` para
  ficheros y un `FakeOrchestrator` (implementa el Protocol `RagOrchestrator`,
  mapea `question -> Answer` predefinido) construido en el propio test:
  - `tests/test_eval_dataset.py`: `test_golden_item_fields` (R1),
    `test_in_corpus_requires_expected_urls` (R2),
    `test_out_of_corpus_rejects_expected_urls` (R3), `test_load_golden_parses_jsonl`
    + `test_load_golden_malformed_line_raises` (R4), `test_default_fixture_loads`
    (R5).
  - `tests/test_eval_metrics.py`: hit-rate (R8, R9), `None` sin in-corpus (R10),
    solo de sources (R11); faithfulness proxy cita+solapamiento y rango (R12, R13),
    excluye abstenidos + cuenta (R14), determinismo (R12); abstención precisión/
    recall (R18, R19), bordes `None` (R20), solo de `answer.abstained` (R21);
    juez-LLM con `FakeLLMProvider` (R15, R17) y juez no usado por defecto (R16).
  - `tests/test_eval_harness.py`: 1 llamada/item con spy (R7), `EvalReport`
    agregado (R6, R22), depende solo del Protocol (R6, R29), JSON serializable
    (R23).
  _(Cubre los tests de R1–R23 del núcleo; trazabilidad `R<n>` ↔ test)_

---

## Slice B — CLI / reporte ejecutable + composición perezosa

### Implementación

- [ ] **T9 — (Opcional) Campo `eval_dataset_path` en `Settings`.**
  Ver `design.md` §9 y §1. O bien añadir a `src/wowrag/config.py` UN campo nuevo
  `eval_dataset_path: str | None = None` (sin tocar claves existentes), o bien
  omitirlo y pasar la ruta solo por `--dataset`. Cualquiera de las dos satisface
  R28; NO modifiques claves existentes ni exijas entorno para el camino por
  defecto.
  _(Cubre R28)_

- [ ] **T10 — CLI `eval/cli.py` + `eval/__main__.py` (composición perezosa).**
  Crear `src/wowrag/eval/cli.py` con `main(argv=None, orchestrator=None) -> int`
  (ver §8): `argparse` con `--dataset` (default `None` → fixture) y `--out`
  (artefacto JSON); `load_golden(args.dataset)`; usa el `orchestrator` inyectado o,
  si es `None`, `_build_orchestrator()` (que hace `from wowrag.api.dependencies
  import build_orchestrator` DENTRO de la función — import perezoso, R26);
  `EvalHarness(orch).run(items)`; imprime un resumen del `EvalReport` por stdout
  (R24); si `--out`, escribe `report.model_dump_json(indent=2)` en esa ruta (R25).
  Crear `src/wowrag/eval/__main__.py` que llame a `cli.main()` para que
  `python -m wowrag.eval` funcione (R24). Cero imports pesados al tope del módulo.
  _(Cubre R24, R25, R26)_

- [ ] **T11 — Finalizar exports de `eval/__init__.py`.**
  Asegurar que `src/wowrag/eval/__init__.py` re-exporta el conjunto público final
  (`GoldenItem`, `load_golden`, `EvalHarness`, `EvalReport`, funciones de métricas)
  con `__all__`, sin importar la CLI de forma que arrastre dependencias pesadas
  (mantener `import wowrag.eval` libre de torch/psycopg/httpx).
  _(Cubre R30)_

### Tests (Slice B)

- [ ] **T-B-tests — `tests/test_eval_cli.py`.**
  Crear (ver §10), `not integration`, con `FakeOrchestrator` inyectado y `tmp_path`:
  - `test_main_prints_summary`: `main([], orchestrator=fake)` imprime resumen y
    retorna 0 (R24).
  - `test_main_writes_json_artifact`: `main(["--out", p], orchestrator=fake)`
    escribe `EvalReport` JSON (R25).
  - `test_main_does_not_build_real_orchestrator_when_injected`: con orquestador
    inyectado, `_build_orchestrator` no se llama (R26, R29).
  - `test_import_eval_is_network_free`: `import wowrag.eval` / `import
    wowrag.eval.cli` no arrastran torch/psycopg/httpx (R16, R26).
  - `test_exports`: `from wowrag.eval import GoldenItem, load_golden, EvalHarness,
    EvalReport` funciona (R30).
  _(Cubre los tests de R24–R26, R30; trazabilidad `R<n>` ↔ test)_

---

## Cierre

- [ ] **Z1 — Verificación final.** Ejecutar `./init.sh` y confirmar exit 0 con la
  suite `not integration` en verde. Comprobar que:
  - Todos los `R<n>` de `requirements.md` (R1–R30) tienen al menos un test.
  - `from wowrag.eval import GoldenItem, load_golden, EvalHarness, EvalReport`
    funciona; `import wowrag.eval` NO arrastra torch/psycopg/httpx ni contacta red.
  - El faithfulness por defecto es el **proxy determinista** (sin LLM); el juez-LLM
    es opcional, fakeable, y SOLO contra Ollama real se marca `@integration`.
  - El hit-rate se deriva de `Answer.sources`, la abstención de `Answer.abstained`;
    ninguna métrica recalcula el umbral ni re-recupera (R11, R21).
  - `python -m wowrag.eval` corre contra el fixture y emite un resumen + (con
    `--out`) un artefacto JSON.
  - f10 NO implementa HTTP API, NI scraping, NI reranking, NI cambia f5–f9; solo
    consume sus interfaces (R27). `config.py` no cambia salvo, como mucho, el campo
    opcional de R28.
  - No quedan imports de DB/ML/red en el camino por defecto del paquete `eval/`.
  _(Verificación integral; no añade requirements nuevos)_

---

> **Nota para el implementer:** NO marques esta feature como `done` ni edites
> `feature-list.json` (salvo lo que ya hizo el spec-author: `pending` →
> `spec_ready`). El cambio a `in_progress` requiere aprobación humana; el cierre
> (`done`) lo hacen el leader / reviewer tras validar la trazabilidad `R<n>` ↔
> test. Tu trabajo termina cuando todas las tasks `[x]` y `./init.sh` pasa en verde.
