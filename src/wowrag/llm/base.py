"""LLM-provider interface and domain exception for the LLM layer.

``LLMProvider`` is the swap point (Protocol) that all LLM implementations must
satisfy. The concrete implementations are ``OllamaLLM`` (real, local HTTP via
httpx) and ``FakeLLMProvider`` (deterministic, network-free, for tests).
``LLMError`` is raised for all LLM-layer failures (missing HTTP client,
unreachable Ollama server, invalid/empty prompt, unexpected response schema).
"""

from __future__ import annotations

from typing import Iterator, Protocol


class LLMError(Exception):
    """Domain exception for LLM-layer failures.

    Raised for a missing HTTP client, an unreachable Ollama server, an
    invalid/empty prompt, or an unexpected response schema.
    """


class LLMProvider(Protocol):
    """Swap point: turns a prompt string into generated text.

    Concrete implementations: ``OllamaLLM`` (real, local HTTP) and
    ``FakeLLMProvider`` (deterministic, network-free, for tests). Callers
    (f8 RagOrchestrator) depend on this Protocol, never on a concrete
    implementation, so the backend is selected by config.

    Contract
    --------
    - ``model`` is a read-only property; it does not contact any remote server.
    - ``generate`` blocks until the full completion is ready and returns it as
      a single ``str``. Empty or whitespace-only prompts raise ``LLMError``
      without any network call.
    - ``generate_stream`` yields the completion in successive text fragments.
      The concatenation of all yielded fragments equals the result of
      ``generate`` for the same prompt and implementation. Same error contract
      as ``generate``.
    - All LLM-layer failures are reported as ``LLMError``, never silently
      swallowed as empty strings.
    """

    @property
    def model(self) -> str:
        """Name of the model this provider generates with. Read-only; no network."""
        ...

    def generate(self, prompt: str) -> str:
        """Generate the full completion for ``prompt`` as a single string.

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text to complete.

        Returns
        -------
        str
            The full generated text.

        Raises
        ------
        LLMError
            On empty/whitespace prompt (no network call), an unreachable
            backend, or an unexpected response.
        """
        ...

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield the completion for ``prompt`` in successive text fragments.

        The concatenation of all yielded fragments equals ``generate(prompt)``
        for the same prompt and implementation. Same error contract as
        ``generate``.

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text to complete.

        Yields
        ------
        str
            Successive text fragments (tokens/chunks) of the completion.

        Raises
        ------
        LLMError
            On empty/whitespace prompt (no network call), an unreachable
            backend, or an unexpected response.
        """
        ...
