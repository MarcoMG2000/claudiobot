"""Tests for the LLMProvider contract via FakeLLMProvider (network-free).

All tests here are unit tests: no httpx, no network, no Ollama server required.
FakeLLMProvider is used as the concrete implementation to verify the contract
defined by the LLMProvider Protocol (R1-R4, R14-R17).

Additional tests cover the OllamaLLM import isolation (R8, R9).
"""

from __future__ import annotations

import sys
import types

import pytest

from wowrag.llm import FakeLLMProvider, LLMError, LLMProvider, OllamaLLM


# ---------------------------------------------------------------------------
# R2: generate returns a non-empty string
# ---------------------------------------------------------------------------


def test_generate_returns_string():  # R2
    """FakeLLMProvider.generate returns a non-empty str for a valid prompt."""
    fake = FakeLLMProvider()
    result = fake.generate("hola mundo")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# R15: generate is deterministic (same prompt -> same output)
# ---------------------------------------------------------------------------


def test_generate_deterministic():  # R15
    """Same prompt returns identical output across calls and instances."""
    prompt = "what is onyxia"
    fake1 = FakeLLMProvider(model="m1", prefix="A: ")
    fake2 = FakeLLMProvider(model="m1", prefix="A: ")

    # Same instance, called twice
    assert fake1.generate(prompt) == fake1.generate(prompt)
    # Two different instances with same config
    assert fake1.generate(prompt) == fake2.generate(prompt)


# ---------------------------------------------------------------------------
# R3, R16: generate_stream concatenation equals generate
# ---------------------------------------------------------------------------


def test_stream_concatenation_equals_generate():  # R3, R16
    """Concatenation of all generate_stream fragments equals generate output."""
    prompt = "tell me about warrior class"
    fake = FakeLLMProvider()
    streamed = "".join(fake.generate_stream(prompt))
    direct = fake.generate(prompt)
    assert streamed == direct


# ---------------------------------------------------------------------------
# R4: model property is accessible and correct
# ---------------------------------------------------------------------------


def test_model_property():  # R4
    """model property returns configured model name without any network call."""
    fake = FakeLLMProvider(model="my-model")
    assert fake.model == "my-model"


# ---------------------------------------------------------------------------
# R1: FakeLLMProvider satisfies the LLMProvider Protocol (structural)
# ---------------------------------------------------------------------------


def test_fake_satisfies_protocol():  # R1
    """FakeLLMProvider is structurally compatible with LLMProvider Protocol."""
    fake: LLMProvider = FakeLLMProvider()  # type annotation assignment
    # Verify the three required interface members are present and callable.
    assert hasattr(fake, "model")
    assert callable(fake.generate)
    assert callable(fake.generate_stream)
    # The model property should return a str
    assert isinstance(fake.model, str)


# ---------------------------------------------------------------------------
# R17: empty/whitespace prompt raises LLMError (generate)
# ---------------------------------------------------------------------------


def test_empty_prompt_raises():  # R17
    """generate raises LLMError for empty or whitespace-only prompts."""
    fake = FakeLLMProvider()
    with pytest.raises(LLMError):
        fake.generate("")
    with pytest.raises(LLMError):
        fake.generate("   ")


# ---------------------------------------------------------------------------
# R17: empty/whitespace prompt raises LLMError (generate_stream)
# ---------------------------------------------------------------------------


def test_stream_empty_prompt_raises():  # R17
    """generate_stream raises LLMError for empty or whitespace-only prompts."""
    fake = FakeLLMProvider()
    with pytest.raises(LLMError):
        list(fake.generate_stream(""))
    with pytest.raises(LLMError):
        list(fake.generate_stream("   "))


# ---------------------------------------------------------------------------
# R8: OllamaLLM module importable without httpx
# ---------------------------------------------------------------------------


def test_ollama_module_importable_without_httpx():  # R8
    """wowrag.llm.ollama is importable even if httpx is not installed.

    This test verifies that the module-level code does not import httpx
    (the import is lazy, inside OllamaLLM.__init__). The module should already
    be imported at this point without error.
    """
    import wowrag.llm.ollama  # noqa: F401 — test that no ImportError was raised

    assert "wowrag.llm.ollama" in sys.modules


# ---------------------------------------------------------------------------
# R9: OllamaLLM instantiation raises LLMError (not ImportError) without httpx
# ---------------------------------------------------------------------------


def test_ollama_instantiation_raises_without_httpx(monkeypatch):  # R9
    """OllamaLLM() raises LLMError (not ImportError) when httpx is absent.

    Simulates a missing httpx by injecting None into sys.modules so that
    'import httpx' inside OllamaLLM.__init__ raises ImportError, which must
    be caught and re-raised as LLMError.
    """
    # Simulate missing httpx by setting it to None in sys.modules.
    # Python treats a None entry as "module not found" when importing.
    monkeypatch.setitem(sys.modules, "httpx", None)
    with pytest.raises(LLMError, match="requirements-llm.txt"):
        OllamaLLM()


# ---------------------------------------------------------------------------
# R19: malformed Ollama response (missing `response` field) raises LLMError
# ---------------------------------------------------------------------------


def test_generate_invalid_schema_raises_llm_error(monkeypatch):  # R19
    """OllamaLLM.generate raises LLMError when the JSON body lacks 'response'.

    Injects a fake ``httpx`` into ``sys.modules`` so the lazy import inside
    ``OllamaLLM.__init__`` resolves to it (no real httpx required). The fake
    ``.post()`` returns a response whose ``.json()`` lacks the ``response``
    key, simulating a malformed Ollama reply. No real network call is made.
    """
    fake_resp = types.SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"model": "fake", "done": True},  # no "response" key
    )
    fake_httpx = types.SimpleNamespace(post=lambda *a, **kw: fake_resp)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    llm = OllamaLLM(model="fake", base_url="http://localhost:11434")
    with pytest.raises(LLMError, match="Unexpected Ollama response schema"):
        llm.generate("test prompt")
