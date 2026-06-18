"""Tests for the wowhead Fetcher transport (Slice A): R1, R3, R4, R10, R25.

All network-free: FakeFetcher serves a predefined map; HttpxFetcher's httpx
import is exercised via sys.modules injection (a fake httpx with MockTransport
semantics simulated by a stub), so no real network call is ever made. Mirrors
the OllamaLLM import-isolation tests in test_llm_interface.py.
"""

from __future__ import annotations

import sys
import types

import pytest

from wowrag.ingest.wowhead import (
    FakeFetcher,
    Fetcher,
    FetchError,
    FetchResult,
    HttpxFetcher,
)


# ---------------------------------------------------------------------------
# R1: FakeFetcher satisfies the Fetcher Protocol (structural)
# ---------------------------------------------------------------------------


def test_fake_fetcher_satisfies_protocol():  # R1
    """FakeFetcher is structurally compatible with the Fetcher Protocol."""
    fake: Fetcher = FakeFetcher()  # type annotation assignment
    assert callable(fake.get)


# ---------------------------------------------------------------------------
# R4: FakeFetcher returns mapped responses without any network call
# ---------------------------------------------------------------------------


def test_fake_fetcher_returns_mapped_result():  # R4, R1
    """FakeFetcher.get returns the preconfigured FetchResult for a URL."""
    url = "https://www.wowhead.com/spell=133"
    fake = FakeFetcher({url: FetchResult(url=url, status_code=200, text="<html/>")})
    result = fake.get(url)
    assert isinstance(result, FetchResult)
    assert result.status_code == 200
    assert result.text == "<html/>"
    assert result.url == url


def test_fake_fetcher_accepts_status_text_tuple():  # R4
    """FakeFetcher accepts a (status, text) tuple and wraps it in a FetchResult."""
    url = "https://www.wowhead.com/spell=133"
    fake = FakeFetcher({url: (200, "body")})
    result = fake.get(url)
    assert result.status_code == 200
    assert result.text == "body"


def test_fake_fetcher_records_requested_urls():  # R4 (supports R5/R6)
    """FakeFetcher records every requested URL in call order."""
    a = "https://www.wowhead.com/a"
    b = "https://www.wowhead.com/b"
    fake = FakeFetcher({a: (200, "A"), b: (200, "B")})
    fake.get(a)
    fake.get(b)
    fake.get(a)
    assert fake.requested_urls == [a, b, a]


def test_fake_fetcher_unmapped_url_raises_without_default():  # R4
    """An unmapped URL raises FetchError when no default_status is configured."""
    fake = FakeFetcher({})
    with pytest.raises(FetchError):
        fake.get("https://www.wowhead.com/missing")


def test_fake_fetcher_default_status_for_unmapped():  # R4
    """With default_status set, unmapped URLs return that status (e.g. 404)."""
    fake = FakeFetcher({}, default_status=404)
    result = fake.get("https://www.wowhead.com/missing")
    assert result.status_code == 404
    assert result.text == ""


# ---------------------------------------------------------------------------
# R25: importing the module does not eagerly import httpx
# ---------------------------------------------------------------------------


def test_import_module_is_lazy_no_httpx(monkeypatch):  # R25
    """Importing wowrag.ingest.wowhead.fetcher does not import httpx eagerly.

    Even with httpx blocked in sys.modules, importing the module succeeds
    because the httpx import is lazy (inside HttpxFetcher.__init__).
    """
    monkeypatch.setitem(sys.modules, "httpx", None)
    # Drop cached modules so the import re-runs module-level code under the block.
    monkeypatch.delitem(sys.modules, "wowrag.ingest.wowhead.fetcher", raising=False)
    monkeypatch.delitem(sys.modules, "wowrag.ingest.wowhead", raising=False)
    import importlib

    mod = importlib.import_module("wowrag.ingest.wowhead.fetcher")
    assert mod is not None  # no ImportError at module import time


# ---------------------------------------------------------------------------
# R3: HttpxFetcher instantiation raises FetchError (not ImportError) sans httpx
# ---------------------------------------------------------------------------


def test_httpx_fetcher_missing_dep_raises_fetcherror(monkeypatch):  # R3
    """HttpxFetcher() raises FetchError (not ImportError) when httpx is absent.

    Injects None for 'httpx' in sys.modules so the lazy import inside
    HttpxFetcher.__init__ raises ImportError, which must surface as FetchError
    pointing at requirements-scrape.txt.
    """
    monkeypatch.setitem(sys.modules, "httpx", None)
    with pytest.raises(FetchError, match="requirements-scrape.txt"):
        HttpxFetcher(user_agent="test-agent/1.0")


# ---------------------------------------------------------------------------
# R10: HttpxFetcher sends the configured User-Agent header (no real network)
# ---------------------------------------------------------------------------


def test_httpx_fetcher_sets_user_agent(monkeypatch):  # R10
    """HttpxFetcher.get sends the configured User-Agent header on the request.

    A fake httpx is injected into sys.modules; its get() captures the headers it
    is called with and returns a stub response. No real network call is made.
    """
    captured: dict[str, object] = {}

    class _Resp:
        url = "https://www.wowhead.com/spell=133"
        status_code = 200
        text = "<html>ok</html>"

    def _fake_get(url, *, headers, timeout, follow_redirects):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["follow_redirects"] = follow_redirects
        return _Resp()

    fake_httpx = types.SimpleNamespace(get=_fake_get)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    fetcher = HttpxFetcher(user_agent="wow-classic-rag-bot/0.1 (+contact)")
    result = fetcher.get("https://www.wowhead.com/spell=133")

    assert captured["headers"] == {
        "User-Agent": "wow-classic-rag-bot/0.1 (+contact)"
    }  # R10
    assert captured["follow_redirects"] is True
    assert result.status_code == 200
    assert result.text == "<html>ok</html>"


# ---------------------------------------------------------------------------
# R3 family: a transport error inside get() surfaces as FetchError
# ---------------------------------------------------------------------------


def test_httpx_fetcher_get_transport_error_raises_fetcherror(monkeypatch):  # R3
    """A transport failure inside HttpxFetcher.get raises FetchError."""

    def _boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    fake_httpx = types.SimpleNamespace(get=_boom)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    fetcher = HttpxFetcher(user_agent="test-agent/1.0")
    with pytest.raises(FetchError, match="GET failed"):
        fetcher.get("https://www.wowhead.com/spell=133")
