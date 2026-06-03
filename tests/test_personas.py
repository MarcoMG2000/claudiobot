"""Tests for the persona system. Covers R7, R8, R9, R10, R11, R12."""

import pytest

from wowrag.config import Settings, default_persona
from wowrag.personas import Persona, PersonaNotFoundError, load_persona


def test_load_simple_persona_returns_persona():  # R7, R8, R10
    persona = load_persona("simple")
    assert isinstance(persona, Persona)
    assert persona.name == "simple"
    assert persona.system_style
    # language is optional (R7).
    assert persona.language == "es"


@pytest.mark.parametrize("name", ["simple", "orc", "troll"])
def test_all_bundled_personas_load(name):  # R10
    persona = load_persona(name)
    assert persona.name == name
    assert persona.system_style


def test_orc_persona_has_zug_zug():  # R11
    persona = load_persona("orc")
    assert "Zug zug" in persona.system_style


def test_unknown_persona_raises_with_name():  # R9
    with pytest.raises(PersonaNotFoundError) as excinfo:
        load_persona("nope")
    assert "nope" in str(excinfo.value)


def test_default_persona_resolves_from_settings():  # R12
    settings = Settings(_env_file=None, default_persona="orc")
    persona = default_persona(settings)
    assert persona.name == "orc"


def test_default_persona_uses_default_setting():  # R12
    settings = Settings(_env_file=None)  # default_persona == "simple"
    assert default_persona(settings).name == "simple"
