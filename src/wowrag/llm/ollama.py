"""OllamaLLM: LLMProvider implementation backed by a local Ollama server.

The ``httpx`` import is lazy (inside ``__init__``), so this module is importable
without ``httpx`` installed (R8). Only instantiation requires the dependency;
failing that raises ``LLMError``, not ``ImportError`` (R9).

Install the LLM HTTP client dependency when a local Ollama server is available:
    pip install -r requirements-llm.txt
"""

from __future__ import annotations

import json
from typing import Iterator

from wowrag.llm.base import LLMError


class OllamaLLM:
    """Real LLMProvider backed by a local Ollama server over HTTP.

    The ``httpx`` import happens inside ``__init__``, so this module is
    importable without ``httpx`` installed (R8). Only instantiation requires
    the dependency (R9).

    Parameters
    ----------
    model:
        Name of the Ollama model to use. Default matches ``Settings.llm_model``
        (``"qwen2.5:7b-instruct"``).
    base_url:
        Base URL of the local Ollama server. Default matches
        ``Settings.ollama_url`` (``"http://localhost:11434"``).
    timeout:
        HTTP request timeout in seconds. Default: ``120.0``.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        try:
            import httpx  # lazy import (R8)
        except ImportError as exc:
            raise LLMError(
                "HTTP client not installed. "
                "Install LLM dependencies: pip install -r requirements-llm.txt"
            ) from exc  # R9
        self._httpx = httpx
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model(self) -> str:
        """Name of the configured model. Read-only; no network call (R20)."""
        return self._model

    def generate(self, prompt: str) -> str:
        """Generate the full completion for ``prompt`` as a single string.

        Sends a POST to ``{base_url}/api/generate`` with ``stream=false`` and
        returns ``response["response"]`` (R6).

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text to complete.

        Returns
        -------
        str
            The full generated text from Ollama.

        Raises
        ------
        LLMError
            On empty/whitespace prompt without any network call (R11).
            On an unreachable server or HTTP error status (R10).
            On a response body that is not valid JSON or lacks the ``response``
            field (R19).
        """
        self._validate(prompt)  # R11: validate before any network call
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        try:
            resp = self._httpx.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except LLMError:
            raise
        except Exception as exc:  # connection error or HTTP error status (R10)
            raise LLMError(f"Ollama generate failed: {exc}") from exc
        try:
            data = resp.json()
            return data["response"]  # R6
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(
                f"Unexpected Ollama response schema: {exc}"
            ) from exc  # R19

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield the completion for ``prompt`` in successive token fragments.

        Sends a POST to ``{base_url}/api/generate`` with ``stream=true`` and
        yields ``obj["response"]`` from each NDJSON line until ``done=true``
        (R7).

        Parameters
        ----------
        prompt:
            Non-empty, non-whitespace-only text to complete.

        Yields
        ------
        str
            Token-level fragments of the completion.

        Raises
        ------
        LLMError
            On empty/whitespace prompt without any network call (R11).
            On an unreachable server or HTTP error status (R10).
        """
        self._validate(prompt)  # R11: validate before any network call
        payload = {"model": self._model, "prompt": prompt, "stream": True}
        try:
            with self._httpx.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():  # NDJSON: one JSON object per line
                    if not line:
                        continue
                    obj = json.loads(line)
                    if "response" in obj:
                        yield obj["response"]  # R7
                    if obj.get("done"):
                        break
        except LLMError:
            raise
        except Exception as exc:  # connection error or HTTP error status (R10)
            raise LLMError(f"Ollama stream failed: {exc}") from exc

    @staticmethod
    def _validate(prompt: str) -> None:
        """Raise ``LLMError`` if ``prompt`` is empty or whitespace-only (R11)."""
        if not prompt or not prompt.strip():
            raise LLMError("prompt is empty or whitespace-only.")  # R11
