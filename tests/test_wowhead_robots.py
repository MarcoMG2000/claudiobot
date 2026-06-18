"""Tests for RobotsGate robots.txt compliance (Slice A): R5, R6, R7.

Network-free: a FakeFetcher serves the robots.txt body and content URLs. The
gate is consulted before any content fetch; tests prove a disallowed URL is
never requested via the FakeFetcher's recorded calls (R6) and that robots.txt is
fetched once per host (R7). No new dependency: stdlib urllib.robotparser.
"""

from __future__ import annotations

from wowrag.ingest.wowhead import FakeFetcher, RobotsGate

UA = "wow-classic-rag-bot/0.1 (+contact)"
HOST = "https://www.wowhead.com"
ROBOTS_URL = f"{HOST}/robots.txt"

# Disallows /forums for everyone; allows the rest.
ROBOTS_BODY = "User-agent: *\nDisallow: /forums\n"


def _gate_with_robots(body: str) -> tuple[RobotsGate, FakeFetcher]:
    fetcher = FakeFetcher({ROBOTS_URL: (200, body)})
    return RobotsGate(UA, fetcher), fetcher


# ---------------------------------------------------------------------------
# R5: allowed() consults robots.txt and permits an allowed path
# ---------------------------------------------------------------------------


def test_allows_when_robots_permits():  # R5
    """A path not disallowed by robots.txt is allowed for the configured UA."""
    gate, _ = _gate_with_robots(ROBOTS_BODY)
    assert gate.allowed(f"{HOST}/spell=133") is True


# ---------------------------------------------------------------------------
# R6: a disallowed path is denied
# ---------------------------------------------------------------------------


def test_denies_when_robots_disallows():  # R6
    """A path disallowed by robots.txt is denied for the configured UA."""
    gate, _ = _gate_with_robots(ROBOTS_BODY)
    assert gate.allowed(f"{HOST}/forums/topic=1") is False


# ---------------------------------------------------------------------------
# R6: the disallowed content URL is NEVER fetched (only robots.txt was)
# ---------------------------------------------------------------------------


def test_disallowed_url_never_fetched():  # R6
    """Consulting the gate fetches only robots.txt; the denied URL is not fetched.

    The gate does not fetch content itself, but this proves that the only URL it
    requested is robots.txt — the disallowed content URL never reaches the
    fetcher (the pipeline relies on this to skip without requesting).
    """
    gate, fetcher = _gate_with_robots(ROBOTS_BODY)
    denied = f"{HOST}/forums/topic=1"
    assert gate.allowed(denied) is False
    assert denied not in fetcher.requested_urls
    assert fetcher.requested_urls == [ROBOTS_URL]


# ---------------------------------------------------------------------------
# R7: robots.txt is fetched once per host and cached for later URLs
# ---------------------------------------------------------------------------


def test_robots_cached_per_host():  # R7
    """Two URLs of the same host fetch robots.txt only once (cached parser)."""
    gate, fetcher = _gate_with_robots(ROBOTS_BODY)
    gate.allowed(f"{HOST}/spell=133")
    gate.allowed(f"{HOST}/item=1234")
    assert fetcher.requested_urls.count(ROBOTS_URL) == 1


# ---------------------------------------------------------------------------
# R5/§11: an inaccessible robots.txt -> permissive default (allowed)
# ---------------------------------------------------------------------------


def test_missing_robots_is_permissive():  # R5 (design.md §11)
    """A 404 robots.txt yields a permissive parser: the URL is allowed."""
    fetcher = FakeFetcher({}, default_status=404)
    gate = RobotsGate(UA, fetcher)
    assert gate.allowed(f"{HOST}/spell=133") is True


def test_robots_fetch_error_is_permissive():  # R5 (design.md §11)
    """A transport error fetching robots.txt yields a permissive parser."""
    fetcher = FakeFetcher({})  # any URL raises FetchError (no default_status)
    gate = RobotsGate(UA, fetcher)
    assert gate.allowed(f"{HOST}/spell=133") is True
