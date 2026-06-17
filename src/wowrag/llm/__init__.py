"""LLM layer: provider interface, domain exception, fake (tests) and Ollama (real).

Consumers depend on this package, not on the internal modules.

``OllamaLLM`` is importable without ``httpx`` installed because the httpx import
is lazy (inside ``OllamaLLM.__init__``). Only instantiation requires the
dependency (R8, R21).
"""

from wowrag.llm.base import LLMError, LLMProvider
from wowrag.llm.fake import FakeLLMProvider
from wowrag.llm.ollama import OllamaLLM

__all__ = [
    "LLMError",
    "LLMProvider",
    "FakeLLMProvider",
    "OllamaLLM",
]
