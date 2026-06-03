"""Tests for package importability. Covers R1, R2."""

import importlib

import pytest


def test_import_wowrag_succeeds():  # R1
    module = importlib.import_module("wowrag")
    assert module.__version__  # exported and non-empty


@pytest.mark.parametrize(
    "subpackage",
    [
        "wowrag.ingest",
        "wowrag.embeddings",
        "wowrag.store",
        "wowrag.retrieval",
        "wowrag.generation",
        "wowrag.rag",
        "wowrag.api",
    ],
)
def test_placeholder_subpackages_import(subpackage):  # R2
    assert importlib.import_module(subpackage) is not None


def test_top_level_exports_present():  # R1
    import wowrag

    for name in ("Settings", "Persona", "PersonaNotFoundError", "load_persona", "default_persona"):
        assert hasattr(wowrag, name), name
