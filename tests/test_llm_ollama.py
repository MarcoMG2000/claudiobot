"""Integration tests for OllamaLLM against a live local Ollama server.

All tests are marked ``@pytest.mark.integration`` and excluded by default
(``pytest -m "not integration"`` in ``init.sh``).

``httpx`` is required for these tests; ``pytest.importorskip("httpx")`` skips
the entire module automatically if it is not installed (mirrors the pattern
used in ``test_store_pgvector.py`` with ``psycopg``).

To run these tests manually:
    pip install -r requirements-llm.txt
    # Start a local Ollama server: ollama serve
    # Optionally set OLLAMA_URL / LLM_MODEL env vars
    pytest tests/test_llm_ollama.py -m integration -v
"""

from __future__ import annotations

import os

import pytest

httpx = pytest.importorskip("httpx")  # skip entire module if httpx not installed

from wowrag.llm import LLMError, OllamaLLM  # noqa: E402 — after importorskip


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://localhost:11434")


def _llm_model() -> str:
    return os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")


def _ollama_reachable() -> bool:
    """Return True if the Ollama server at the configured URL is reachable."""
    try:
        resp = httpx.get(f"{_ollama_url()}/api/tags", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


_REQUIRES_OLLAMA = pytest.mark.skipif(
    not _ollama_reachable(),
    reason="Ollama server not reachable at OLLAMA_URL (skipping integration test)",
)


# ---------------------------------------------------------------------------
# R5, R6: generate roundtrip with live Ollama
# ---------------------------------------------------------------------------


@pytest.mark.integration
@_REQUIRES_OLLAMA
def test_generate_roundtrip():  # R5, R6
    """OllamaLLM.generate returns a non-empty string from a live Ollama server."""
    llm = OllamaLLM(model=_llm_model(), base_url=_ollama_url())
    result = llm.generate("Say hi in one word")
    assert isinstance(result, str)
    assert len(result.strip()) > 0


# ---------------------------------------------------------------------------
# R7: generate_stream roundtrip with live Ollama
# ---------------------------------------------------------------------------


@pytest.mark.integration
@_REQUIRES_OLLAMA
def test_generate_stream_roundtrip():  # R7
    """generate_stream yields ≥1 fragment; concatenation is non-empty."""
    llm = OllamaLLM(model=_llm_model(), base_url=_ollama_url())
    fragments = list(llm.generate_stream("Say hi in one word"))
    assert len(fragments) >= 1
    concatenated = "".join(fragments)
    assert len(concatenated.strip()) > 0


# ---------------------------------------------------------------------------
# R20: model property does not contact the server
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_model_property_no_network():  # R20
    """OllamaLLM.model returns the configured name without any network call.

    This test does NOT require a live Ollama server: it only instantiates the
    class with a dummy base_url and reads the model property.
    """
    llm = OllamaLLM(model="test-model", base_url=_ollama_url())
    assert llm.model == "test-model"


# ---------------------------------------------------------------------------
# R10: unreachable server raises LLMError
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_unreachable_server_raises():  # R10
    """generate raises LLMError when the Ollama server is unreachable.

    Uses port 1 on localhost, which is virtually guaranteed to be refused
    (not a service). Does NOT require a live Ollama server.
    """
    llm = OllamaLLM(model=_llm_model(), base_url="http://127.0.0.1:1", timeout=3.0)
    with pytest.raises(LLMError):
        llm.generate("x")


# ---------------------------------------------------------------------------
# R11: empty prompt raises LLMError without opening a connection
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_empty_prompt_no_request():  # R11
    """generate raises LLMError for an empty prompt without any network call.

    Does NOT require a live Ollama server: validation happens before the HTTP
    call is made.
    """
    llm = OllamaLLM(model=_llm_model(), base_url=_ollama_url())
    with pytest.raises(LLMError):
        llm.generate("")


# ---------------------------------------------------------------------------
# R19: invalid/missing response field raises LLMError
#
# Covered by a network-free unit test in test_llm_interface.py
# (test_generate_invalid_schema_raises_llm_error), which monkeypatches the
# lazy httpx import — no live server or pytest-localserver dependency needed.
# ---------------------------------------------------------------------------
