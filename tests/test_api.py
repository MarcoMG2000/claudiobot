"""Tests for the HTTP API layer (f9-http-api).

All tests are DB-free / GPU-free / network-free: the real ``RagOrchestrator`` is
replaced by a ``FakeOrchestrator`` via ``app.dependency_overrides`` and the app
is exercised through Starlette/FastAPI's ``TestClient`` (needs ``httpx``). They
run under the default ``pytest -m "not integration"`` suite in ``./init.sh`` --
no ``@pytest.mark.integration`` markers. Traceability to R1..R25 is noted per
test.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from wowrag.api import create_app
from wowrag.api.dependencies import get_orchestrator
from wowrag.config import Settings
from wowrag.embeddings.base import EmbeddingError
from wowrag.llm.base import LLMError
from wowrag.models import Answer, AnswerMetadata, Source
from wowrag.personas import Persona, PersonaNotFoundError
from wowrag.rag import OrchestratorError
from wowrag.retrieval.base import RetrieverError
from wowrag.store.base import VectorStoreError


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #
class FakeOrchestrator:
    """Stand-in for ``RagOrchestrator``: returns a fixed Answer or raises.

    Records every ``answer`` call so tests can assert call count and the exact
    (query, persona) it received. Never touches Postgres / bge-m3 / Ollama.
    """

    def __init__(self, result: Answer | Exception) -> None:
        self._result = result
        self.calls: list[tuple[str, Persona | None]] = []

    def answer(self, query: str, persona: Persona | None = None) -> Answer:
        self.calls.append((query, persona))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _happy_answer() -> Answer:
    return Answer(
        answer="Fireball deals fire damage.",
        sources=[
            Source(n=1, title="Fireball - Spell", url="https://wowhead.com/spell=133"),
            Source(n=2, title="Pyroblast - Spell", url="https://wowhead.com/spell=11366"),
        ],
        abstained=False,
        metadata=AnswerMetadata(
            model="qwen2.5:7b-instruct",
            persona="simple",
            max_score=0.91,
            scores=[0.91, 0.74],
        ),
    )


def _abstention_answer() -> Answer:
    return Answer(
        answer="No hay evidencia suficiente en los documentos para responder con seguridad.",
        sources=[],
        abstained=True,
        metadata=AnswerMetadata(
            model="qwen2.5:7b-instruct",
            persona="simple",
            max_score=0.10,
            scores=[0.10],
        ),
    )


def client_with(fake: FakeOrchestrator, settings: Settings | None = None) -> TestClient:
    """Build a TestClient whose orchestrator dependency is the given fake (R20)."""
    app = create_app(settings=settings)
    app.dependency_overrides[get_orchestrator] = lambda: fake
    return TestClient(app)


# --------------------------------------------------------------------------- #
# T15 / app + routes (R1, R3)
# --------------------------------------------------------------------------- #
def test_create_app_returns_fastapi_with_routes():  # R1
    from fastapi import FastAPI

    app = create_app()
    assert isinstance(app, FastAPI)
    # Collect registered paths from the generated OpenAPI schema (robust across
    # FastAPI versions, which may wrap routes in include_router containers).
    paths = set(app.openapi()["paths"].keys())
    assert "/ask" in paths
    assert "/health" in paths


def test_health_ok_without_orchestrator():  # R3
    # Spy: /health must NOT touch the orchestrator. If it did, calls would record.
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert fake.calls == []  # orchestrator never invoked


# --------------------------------------------------------------------------- #
# T16 / happy path (R2, R4, R5, R6, R7)
# --------------------------------------------------------------------------- #
def test_ask_happy_path_maps_answer():  # R2, R5, R6, R7
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "What does Fireball do?"})
    assert resp.status_code == 200
    body = resp.json()
    # R2: top-level keys
    assert set(body.keys()) == {"answer", "sources", "abstained", "metadata"}
    # R5: answer text + sources as {n,title,url}, abstained false
    assert body["answer"] == "Fireball deals fire damage."
    assert body["abstained"] is False
    assert body["sources"] == [
        {"n": 1, "title": "Fireball - Spell", "url": "https://wowhead.com/spell=133"},
        {"n": 2, "title": "Pyroblast - Spell", "url": "https://wowhead.com/spell=11366"},
    ]
    # R6/R7: metadata mapped 1:1 from AnswerMetadata, not recomputed
    assert body["metadata"] == {
        "model": "qwen2.5:7b-instruct",
        "persona": "simple",
        "max_score": 0.91,
        "scores": [0.91, 0.74],
    }


def test_ask_calls_orchestrator_once_with_query():  # R4
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    client.post("/ask", json={"query": "Where is Orgrimmar?"})
    assert len(fake.calls) == 1  # exactly once
    assert fake.calls[0][0] == "Where is Orgrimmar?"  # the body query


# --------------------------------------------------------------------------- #
# T17 / abstention path (R8, R9)
# --------------------------------------------------------------------------- #
def test_ask_abstention_path():  # R8, R9
    fake = FakeOrchestrator(_abstention_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "Who won the 2042 election?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["abstained"] is True  # R8
    assert body["sources"] == []  # R8: empty list on abstention
    assert "No hay evidencia suficiente" in body["answer"]  # R8: f8 message
    # R9: metadata still present for diagnostics
    assert body["metadata"]["model"] == "qwen2.5:7b-instruct"
    assert body["metadata"]["persona"] == "simple"
    assert body["metadata"]["max_score"] == 0.10
    assert body["metadata"]["scores"] == [0.10]


# --------------------------------------------------------------------------- #
# T18 / persona (R10, R11, R12)
# --------------------------------------------------------------------------- #
def test_ask_persona_explicit_forwarded():  # R10
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "q", "persona": "orc"})
    assert resp.status_code == 200
    _, persona = fake.calls[0]
    assert isinstance(persona, Persona)
    assert persona.name == "orc"  # resolved from orc.yaml and forwarded


def test_ask_persona_default_when_absent():  # R11
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "q"})  # no persona field
    assert resp.status_code == 200
    _, persona = fake.calls[0]
    assert persona is None  # f8/Settings.default_persona resolves it, not f9


def test_ask_unknown_persona_returns_400():  # R12, R18
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "q", "persona": "does-not-exist"})
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")  # R18
    assert "detail" in resp.json()
    assert fake.calls == []  # orchestrator never reached for unknown persona


# --------------------------------------------------------------------------- #
# T19 / CORS (R13, R14)
# --------------------------------------------------------------------------- #
def test_cors_headers_present():  # R13
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.get("/health", headers={"Origin": "https://game.example"})
    assert resp.status_code == 200
    # Default allow_origins=["*"] -> wildcard echoed back
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_cors_origins_from_settings_not_hardcoded():  # R14
    # Override Settings with a closed allow-list; the response must reflect that
    # origin (from Settings), proving origins are not hardcoded to "*".
    fake = FakeOrchestrator(_happy_answer())
    settings = Settings(_env_file=None, cors_allow_origins=["https://game.example"])
    client = client_with(fake, settings=settings)
    resp = client.get("/health", headers={"Origin": "https://game.example"})
    assert resp.headers.get("access-control-allow-origin") == "https://game.example"


# --------------------------------------------------------------------------- #
# T20 / validation + error mapping (R15, R16, R17, R18)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("body", [{"query": "   "}, {"query": ""}, {}])
def test_ask_empty_or_missing_query_422(body):  # R15
    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json=body)
    assert resp.status_code == 422  # pydantic validation
    assert fake.calls == []  # orchestrator NOT invoked


def test_ask_orchestrator_error_400():  # R16
    fake = FakeOrchestrator(OrchestratorError("query must be a non-empty string"))
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "valid query"})
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "detail" in resp.json()


@pytest.mark.parametrize(
    "exc",
    [
        RetrieverError("boom"),
        EmbeddingError("gpu down"),
        VectorStoreError("pg down"),
        LLMError("ollama unreachable"),
    ],
)
def test_ask_infra_error_503(exc):  # R17, R18
    fake = FakeOrchestrator(exc)
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "valid query"})
    assert resp.status_code == 503
    body = resp.json()
    assert body == {"detail": "upstream RAG component failed"}
    # R17/R18: no internal trace / exception message leaked in the body
    assert "boom" not in resp.text
    assert "Traceback" not in resp.text


def test_error_body_is_json_not_html():  # R18
    fake = FakeOrchestrator(LLMError("secret internal detail"))
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "valid query"})
    assert resp.headers["content-type"].startswith("application/json")
    assert "<html" not in resp.text.lower()
    assert "secret internal detail" not in resp.text


# --------------------------------------------------------------------------- #
# T21 / DI override (R19, R20, R21)
# --------------------------------------------------------------------------- #
def test_dependency_override_used_real_orchestrator_never_built(monkeypatch):  # R19, R20, R21
    # If the override works, build_orchestrator (the real composition that would
    # import bge-m3/pgvector/Ollama) is NEVER invoked.
    import wowrag.api.dependencies as deps

    called = {"build": False}

    def _boom() -> object:  # pragma: no cover - must never run
        called["build"] = True
        raise AssertionError("build_orchestrator must not be called in tests")

    monkeypatch.setattr(deps, "build_orchestrator", _boom)

    fake = FakeOrchestrator(_happy_answer())
    client = client_with(fake)
    resp = client.post("/ask", json={"query": "q"})
    assert resp.status_code == 200
    assert called["build"] is False  # real composition never reached
    assert len(fake.calls) == 1  # the fake handled the request


def test_importing_api_does_not_pull_heavy_deps():  # R20, R21
    # Importing the API package must not eagerly import torch/psycopg. (Lazy
    # imports live inside build_orchestrator.) We assert the heavy modules are
    # not imported as a side effect of importing wowrag.api.
    import sys

    import wowrag.api  # noqa: F401  (import under test)

    assert "torch" not in sys.modules
    assert "psycopg" not in sys.modules
