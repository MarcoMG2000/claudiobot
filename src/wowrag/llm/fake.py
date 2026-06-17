"""Deterministic, network-free LLM provider for unit tests.

``FakeLLMProvider`` generates text as a pure function of the prompt and the
configured ``model``/``prefix``, so the same prompt always yields the same
output across instances and sessions. Zero HTTP, zero network — only stdlib.
Used by f7 tests and by f8 to swap Fake<->OllamaLLM by config.
"""

from __future__ import annotations

from typing import Iterator

from wowrag.llm.base import LLMError


class FakeLLMProvider:
    """Deterministic, network-free LLM provider for unit tests.

    The completion is a pure function of the prompt (and the configured
    ``model``/``prefix``), so the same prompt always yields the same output
    across instances and sessions. Zero HTTP, zero network. Used by f7 tests
    and by f8 to swap Fake<->Ollama by config.

    Parameters
    ----------
    model:
        Model name returned by the ``model`` property. Default: ``"fake-llm"``.
    prefix:
        String prepended to the stripped prompt in the output.
        Default: ``"ECHO: "``.
    """

    def __init__(
        self,
        model: str = "fake-llm",
        prefix: str = "ECHO: ",
    ) -> None:
        self._model = model
        self._prefix = prefix

    @property
    def model(self) -> str:
        """Name of the configured model. Read-only; no network."""
        return self._model

    def generate(self, prompt: str) -> str:
        """Return a deterministic completion for ``prompt``.

        The output is a pure function of ``prefix + prompt.strip()``.
        Empty or whitespace-only prompts raise ``LLMError`` (R17).

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text.

        Returns
        -------
        str
            ``self._prefix + prompt.strip()`` — deterministic across calls
            and instances with the same configuration (R15).

        Raises
        ------
        LLMError
            If ``prompt`` is empty or whitespace-only (R17).
        """
        if not prompt or not prompt.strip():
            raise LLMError("prompt is empty or whitespace-only.")  # R17
        # Deterministic: output is a pure function of the prompt (R15).
        return f"{self._prefix}{prompt.strip()}"

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield the completion for ``prompt`` in successive word fragments.

        The concatenation of all yielded fragments is byte-identical to
        ``generate(prompt)`` (R16). Validates the prompt first; raises
        ``LLMError`` on empty/whitespace (R17).

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text.

        Yields
        ------
        str
            Word-level fragments of the full completion.

        Raises
        ------
        LLMError
            If ``prompt`` is empty or whitespace-only (R17).
        """
        # generate() validates the prompt and is deterministic (R17, R15).
        full = self.generate(prompt)
        # Split into word tokens so each yield is a non-empty fragment, then
        # re-join with a space between tokens.  The concatenation must be
        # byte-identical to `full` (R16), so we reconstruct carefully:
        words = full.split(" ")
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word
