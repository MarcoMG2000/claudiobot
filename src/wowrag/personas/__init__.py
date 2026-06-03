"""Swappable persona/style system.

A persona is defined by a YAML data file in this directory (not in code), so it
can be swapped without touching Python. ``load_persona`` reads ``<name>.yaml``
and returns a validated ``Persona``.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

_PERSONA_DIR = Path(__file__).parent


class Persona(BaseModel):
    """A response style/persona loaded from a YAML file."""

    name: str
    system_style: str
    language: str | None = None


class PersonaNotFoundError(Exception):
    """Raised when a requested persona has no matching YAML file.

    The message includes the requested name to aid debugging.
    """


def load_persona(name: str) -> Persona:
    """Load persona ``<name>.yaml`` from the personas directory.

    Raises ``PersonaNotFoundError`` (including ``name``) if the file is missing.
    """
    path = _PERSONA_DIR / f"{name}.yaml"
    if not path.is_file():
        raise PersonaNotFoundError(
            f"No existe una persona con nombre {name!r} en {_PERSONA_DIR}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Persona(**data)


__all__ = ["Persona", "PersonaNotFoundError", "load_persona"]
