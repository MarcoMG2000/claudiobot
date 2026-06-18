"""CLI entrypoint for the wowhead ingest flow (R21, R22, R23, R25).

Runs the ingest end-to-end (fetch with robots + rate-limit -> normalize ->
write JSONL corpus) and prints a summary to stdout (R23), returning 0 on success
(R22). Mirrors f10's ``wowrag.eval`` CLI pattern: ``main(argv, fetcher=None)`` is
**injectable** so unit tests pass a ``FakeFetcher`` and never touch the network
(R29); the real ``HttpxFetcher`` / ``WowheadNormalizer`` are composed **lazily**
in ``_build_*`` (their own httpx / selectolax imports stay inside those
constructors), so importing this module pulls neither httpx nor selectolax (R25).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from wowrag.ingest.wowhead.pipeline import IngestReport, WowheadIngestor

if TYPE_CHECKING:  # interfaces only; no heavy imports at module load (R25)
    from wowrag.config import Settings
    from wowrag.ingest.wowhead.base import Fetcher


def _build_fetcher(settings: Settings) -> Fetcher:
    """Build the real ``HttpxFetcher`` — lazy httpx import lives in its ctor (R25).

    Only reached when ``main`` is run without an injected fetcher, so the default
    test suite (which injects a ``FakeFetcher``) never instantiates it.
    """
    from wowrag.ingest.wowhead.fetcher import HttpxFetcher

    return HttpxFetcher(user_agent=settings.scrape_user_agent)


def _build_ingestor(fetcher: Fetcher, settings: Settings) -> WowheadIngestor:
    """Compose robots + rate-limit + normalizer around ``fetcher`` (R25).

    The ``WowheadNormalizer`` does its own lazy ``selectolax`` import in its
    constructor, so this composition stays free of eager heavy imports until it
    actually runs.
    """
    from wowrag.ingest.wowhead.normalizer import WowheadNormalizer
    from wowrag.ingest.wowhead.robots import RobotsGate
    from wowrag.ingest.wowhead.throttle import RateLimiter

    robots = RobotsGate(settings.scrape_user_agent, fetcher)
    limiter = RateLimiter(settings.scrape_min_interval_s)
    normalizer = WowheadNormalizer()
    return WowheadIngestor(
        fetcher,
        robots,
        limiter,
        normalizer,
        allowed_host=settings.scrape_allowed_host,
        max_pages=settings.scrape_max_pages,
    )


def _format_summary(report: IngestReport) -> str:
    """Render a human-readable stdout summary of an ``IngestReport`` (R23)."""
    return "\n".join(
        [
            "=== wowrag wowhead ingest ===",
            f"urls requested      : {report.requested}",
            f"  skipped allowlist : {report.skipped_allowlist}",
            f"  skipped robots    : {report.skipped_robots}",
            f"  skipped empty     : {report.skipped_empty}",
            f"documents written   : {report.documents_written}",
            f"corpus file         : {report.out_path}",
        ]
    )


def main(argv: list[str] | None = None, fetcher: Fetcher | None = None) -> int:
    """Run the wowhead ingest end-to-end and emit the summary (R21-R23).

    Parses ``urls`` (one or more seed URLs, R17) and ``--out`` (output corpus
    directory; default ``Settings.scrape_corpus_path``, R21). Builds ``Settings``
    lazily, composes the ingestor (using the injected ``fetcher`` when given, R29,
    else the real lazy stack, R25), runs it, prints the summary (R23) and returns
    0 on success (R22).
    """
    parser = argparse.ArgumentParser(prog="python -m wowrag.ingest.wowhead")
    parser.add_argument("urls", nargs="+", help="seed wowhead URL(s) to ingest")  # R17
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output corpus directory (default: Settings.scrape_corpus_path)",
    )  # R21
    args = parser.parse_args(argv)

    from wowrag.config import Settings  # lazy: no config side effects at import

    settings = Settings()
    out_dir = args.out if args.out is not None else Path(settings.scrape_corpus_path)

    # Injected fetcher short-circuits the real (lazy, heavy) composition (R29).
    f = fetcher if fetcher is not None else _build_fetcher(settings)
    ingestor = _build_ingestor(f, settings)
    report = ingestor.run(args.urls, out_dir)

    print(_format_summary(report))  # stdout summary (R23)
    return 0
