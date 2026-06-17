"""Generation layer: prompt building (f6) + LLM provider (f7, lands later).

Re-exports for callers (f8/f9): import from this package, not from internal
modules. f7 will extend __all__ with LLMProvider, LLMError, OllamaLLM,
FakeLLMProvider when it lands.
"""

from __future__ import annotations

from wowrag.generation.prompt_builder import DefaultPromptBuilder
from wowrag.generation.prompt_builder_base import PromptBuilder, PromptBuilderError

__all__ = ["PromptBuilder", "PromptBuilderError", "DefaultPromptBuilder"]
