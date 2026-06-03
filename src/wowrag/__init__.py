"""wowrag — self-hosted RAG chatbot for WoW Classic (grounded in wowhead).

This package exposes the configuration system (``Settings``), the swappable
persona system (``Persona`` + ``load_persona``) and placeholder subpackages for
the RAG pipeline layers implemented in later features.
"""

from wowrag.config import Settings, default_persona
from wowrag.personas import Persona, PersonaNotFoundError, load_persona

__version__ = "0.0.0"

__all__ = [
    "Settings",
    "Persona",
    "PersonaNotFoundError",
    "load_persona",
    "default_persona",
    "__version__",
]
