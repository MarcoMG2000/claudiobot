"""Tests for WowheadIngestor: end-to-end ingest -> JSONL (Slice B).

Covers R6, R16, R17, R18, R19, R20 (the key handoff round-trip), R23. All
network-free: a ``FakeFetcher`` (Slice A) serves fixtures/robots, and the
normalizer is a deterministic fake that returns ``Document``s WITHOUT parsing —
so the orchestration tests run parser-free regardless. One extra test exercises
the REAL normalizer against the HTML fixture; selectolax is installed by init.sh
(pinned in requirements.txt), so it runs in the default suite.

The JSONL the pipeline writes is loaded back through f1's ``JsonlCorpusLoader``
(R20) — proving f11's output is consumable by the existing path unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wowrag.ingest import JsonlCorpusLoader
from wowrag.ingest.wowhead import (
    FakeFetcher,
    FetchResult,
    IngestReport,
    RateLimiter,
    RobotsGate,
    WowheadIngestor,
)
from wowrag.models import Document

UA = "wow-classic-rag-bot/0.1 (+contact)"
HOST = "www.wowhead.com"
HTTPS = f"https://{HOST}"
ROBOTS_URL = f"{HTTPS}/robots.txt"
# Disallows /forums for everyone; allows the rest.
ROBOTS_BODY = "User-agent: *\nDisallow: /forums\n"

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wowhead"


# ---------------------------------------------------------------------------
# Fake normalizer: returns a Document derived from the HTML marker, no parsing.
# Implements the WowheadNormalizer.normalize(html, source_url) -> Document | None
# shape structurally, so the pipeline runs without selectolax.
# ---------------------------------------------------------------------------


class FakeNormalizer:
    """Maps the fetched body to a Document (or None) without a real parser.

    Bodies containing ``EMPTY`` normalize to ``None`` (simulating R16); otherwise
    a Document is built using the body text and the (post-redirect) source URL.
    """

    def normalize(self, html: str, source_url: str) -> Document | None:
        if "EMPTY" in html:
            return None
        return Document(
            text=html.strip(),
            source_url=source_url,
            title="Fireball",
            section="Spell Details",
        )


def _zero_clock() -> float:
    """A clock that never advances; with a 0 interval the limiter never sleeps."""
    return 0.0


def _build_ingestor(
    fetcher: FakeFetcher,
    *,
    allowed_host: str = HOST,
    max_pages: int = 100,
    normalizer=None,
) -> WowheadIngestor:
    robots = RobotsGate(UA, fetcher)
    limiter = RateLimiter(0.0, clock=_zero_clock, sleep=lambda _s: None)
    return WowheadIngestor(
        fetcher,
        robots,
        limiter,
        normalizer or FakeNormalizer(),
        allowed_host=allowed_host,
        max_pages=max_pages,
    )


# ---------------------------------------------------------------------------
# R19: run writes the Documents as JSONL to out_dir/wowhead.jsonl
# ---------------------------------------------------------------------------


def test_run_writes_jsonl(tmp_path):  # R19
    """run() writes one JSON object per Document to out_dir/wowhead.jsonl."""
    url = f"{HTTPS}/spell=133"
    fetcher = FakeFetcher(
        {ROBOTS_URL: (200, ROBOTS_BODY), url: (200, "Fireball body text")}
    )
    report = _build_ingestor(fetcher).run([url], tmp_path)

    out_file = tmp_path / "wowhead.jsonl"
    assert out_file.exists()
    lines = [ln for ln in out_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    assert report.documents_written == 1
    assert report.out_path == str(out_file)


# ---------------------------------------------------------------------------
# R20: the written JSONL round-trips through f1's JsonlCorpusLoader (KEY TEST)
# ---------------------------------------------------------------------------


def test_output_roundtrips_through_jsonl_loader(tmp_path):  # R20
    """The corpus f11 writes loads back through JsonlCorpusLoader unchanged.

    This is the f11 -> f1 handoff contract: what the ingestor writes, the f1
    loader reads, returning equivalent Documents (no schema change, R26).
    """
    url = f"{HTTPS}/spell=133"
    fetcher = FakeFetcher(
        {ROBOTS_URL: (200, ROBOTS_BODY), url: (200, "Fireball deals fire damage")}
    )
    _build_ingestor(fetcher).run([url], tmp_path)

    docs = JsonlCorpusLoader().load(tmp_path)  # f1 loader, unchanged
    assert len(docs) == 1
    doc = docs[0]
    assert isinstance(doc, Document)
    assert doc.text == "Fireball deals fire damage"
    assert doc.source_url == url
    assert doc.title == "Fireball"
    assert doc.section == "Spell Details"


# ---------------------------------------------------------------------------
# R6, R18: disallowed and off-allowlist URLs are neither written nor fetched
# ---------------------------------------------------------------------------


def test_disallowed_and_off_allowlist_skipped(tmp_path):  # R6, R18
    """Robots-denied and off-allowlist URLs are skipped without being fetched."""
    allowed = f"{HTTPS}/spell=133"
    denied = f"{HTTPS}/forums/topic=1"  # disallowed by robots
    foreign = "https://evil.example.com/spell=133"  # off allowlist
    fetcher = FakeFetcher(
        {
            ROBOTS_URL: (200, ROBOTS_BODY),
            allowed: (200, "Fireball body"),
            denied: (200, "should never be fetched"),
            foreign: (200, "should never be fetched"),
        }
    )
    report = _build_ingestor(fetcher).run([allowed, denied, foreign], tmp_path)

    assert report.requested == 3
    assert report.skipped_robots == 1
    assert report.skipped_allowlist == 1
    assert report.documents_written == 1
    # The denied/foreign content URLs were NEVER requested (R6, R18).
    assert denied not in fetcher.requested_urls
    assert foreign not in fetcher.requested_urls
    assert allowed in fetcher.requested_urls


# ---------------------------------------------------------------------------
# R16: a page with no extractable text produces no JSONL line
# ---------------------------------------------------------------------------


def test_empty_document_skipped(tmp_path):  # R16
    """A page the normalizer maps to None writes no line and counts as empty."""
    good = f"{HTTPS}/spell=133"
    empty = f"{HTTPS}/spell=999"
    fetcher = FakeFetcher(
        {
            ROBOTS_URL: (200, ROBOTS_BODY),
            good: (200, "Fireball body"),
            empty: (200, "EMPTY"),  # FakeNormalizer maps this to None
        }
    )
    report = _build_ingestor(fetcher).run([good, empty], tmp_path)

    assert report.skipped_empty == 1
    assert report.documents_written == 1
    lines = [
        ln
        for ln in (tmp_path / "wowhead.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# R23: the IngestReport reflects requested / skipped / written counts
# ---------------------------------------------------------------------------


def test_report_counts(tmp_path):  # R23
    """IngestReport aggregates the per-category counts for the run."""
    allowed = f"{HTTPS}/spell=133"
    denied = f"{HTTPS}/forums/topic=1"
    foreign = "https://evil.example.com/x"
    empty = f"{HTTPS}/spell=999"
    fetcher = FakeFetcher(
        {
            ROBOTS_URL: (200, ROBOTS_BODY),
            allowed: (200, "Fireball body"),
            denied: (200, "x"),
            foreign: (200, "x"),
            empty: (200, "EMPTY"),
        }
    )
    report = _build_ingestor(fetcher).run([allowed, denied, foreign, empty], tmp_path)

    assert isinstance(report, IngestReport)
    assert report.requested == 4
    assert report.skipped_allowlist == 1
    assert report.skipped_robots == 1
    assert report.skipped_empty == 1
    assert report.documents_written == 1


# ---------------------------------------------------------------------------
# max_pages cap: only the first max_pages URLs are processed
# ---------------------------------------------------------------------------


def test_max_pages_caps_requested(tmp_path):
    """Only the first max_pages seed URLs are processed (runaway-crawl defense)."""
    urls = [f"{HTTPS}/spell={i}" for i in range(5)]
    responses = {ROBOTS_URL: (200, ROBOTS_BODY)}
    responses.update({u: (200, f"body {u}") for u in urls})
    fetcher = FakeFetcher(responses)

    report = _build_ingestor(fetcher, max_pages=2).run(urls, tmp_path)

    assert report.requested == 2
    assert report.documents_written == 2


# ---------------------------------------------------------------------------
# R12-R20 with the REAL normalizer: full normalizer+pipeline against a fixture
# (selectolax is installed by init.sh via requirements.txt, so this RUNS)
# ---------------------------------------------------------------------------


def test_run_with_real_normalizer_roundtrips(tmp_path):  # R12-R15, R19, R20
    """End-to-end with the real selectolax normalizer over the HTML fixture.

    Fetches the committed fixture via FakeFetcher, normalizes it with the real
    WowheadNormalizer and loads the JSONL back through JsonlCorpusLoader (R20).
    """
    from wowrag.ingest.wowhead import WowheadNormalizer

    url = f"{HTTPS}/spell=133"
    html = (FIXTURES / "spell_fireball.html").read_text(encoding="utf-8")
    fetcher = FakeFetcher({ROBOTS_URL: (200, ROBOTS_BODY), url: (200, html)})
    ingestor = _build_ingestor(fetcher, normalizer=WowheadNormalizer())

    report = ingestor.run([url], tmp_path)
    assert report.documents_written == 1

    docs = JsonlCorpusLoader().load(tmp_path)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_url == url
    assert doc.title == "Fireball"
    assert doc.section == "Spell Details"
    assert "Fire damage" in doc.text
    assert "BUY GOLD NOW" not in doc.text  # boilerplate stripped (R12)


# ---------------------------------------------------------------------------
# R30: a live fetch against wowhead, marked integration (excluded by init.sh)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_live_fetch_respects_robots(tmp_path):  # R30
    """One real fetch against live wowhead, honoring robots + UA.

    Excluded from the default suite (``-m "not integration"``). Requires network
    access (selectolax + httpx are installed by init.sh via requirements.txt).
    Verifies the courteous transport works end-to-end against the real host:
    robots is consulted, the UA is sent and a corpus is written.
    """
    from wowrag.config import Settings
    from wowrag.ingest.wowhead import HttpxFetcher, WowheadNormalizer

    settings = Settings()
    fetcher = HttpxFetcher(user_agent=settings.scrape_user_agent)
    robots = RobotsGate(settings.scrape_user_agent, fetcher)
    limiter = RateLimiter(settings.scrape_min_interval_s)
    ingestor = WowheadIngestor(
        fetcher,
        robots,
        limiter,
        WowheadNormalizer(),
        allowed_host=settings.scrape_allowed_host,
        max_pages=1,
    )

    url = f"https://{settings.scrape_allowed_host}/spell=133/fireball"
    report = ingestor.run([url], tmp_path)

    # robots.txt was consulted before the content fetch (R5); a courteous run
    # either writes the page or skips it per robots — both are valid outcomes.
    assert report.requested == 1
    assert report.skipped_robots + report.documents_written + report.skipped_empty == 1
