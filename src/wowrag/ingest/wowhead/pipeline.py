"""WowheadIngestor: the ingest pipeline (R5-R9, R16, R17-R21, R23).

Composes the injected ``Fetcher`` (interface) with the ``RobotsGate``,
``RateLimiter`` and ``WowheadNormalizer`` collaborators. For each seed URL it
applies a STRICT order — allowlist (R18) -> robots (R5, R6) -> rate-limit
(R8, R9) -> fetch -> normalize (R12-R15) — so a URL rejected by the allowlist or
robots NEVER reaches ``fetcher.get`` (verifiable because ``FakeFetcher`` records
requested URLs). Normalized ``Document``s are written as JSONL to
``out_dir/wowhead.jsonl`` (R19), exactly the format ``JsonlCorpusLoader`` reads
(R20). ``run`` returns an ``IngestReport`` with the counts the CLI prints (R23).

``IngestReport`` is a LOCAL subpackage model (NOT added to ``wowrag.models``,
which f11 does not touch — R26).
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from wowrag.ingest.wowhead.base import Fetcher, FetchError
from wowrag.ingest.wowhead.normalizer import WowheadNormalizer
from wowrag.ingest.wowhead.robots import RobotsGate
from wowrag.ingest.wowhead.throttle import RateLimiter

logger = logging.getLogger(__name__)

# Name of the JSONL corpus file written inside the output directory. A directory
# is used so JsonlCorpusLoader (which globs ``*.jsonl`` in a directory) consumes
# it unchanged (R19, R20).
CORPUS_FILENAME = "wowhead.jsonl"


class IngestReport(BaseModel):
    """Counts from one ingest run; the CLI renders these to stdout (R23).

    Fields
    ------
    requested          : seed URLs considered for ingestion.
    skipped_allowlist  : URLs skipped because their host is off the allowlist (R18).
    skipped_robots     : URLs skipped because robots.txt disallowed them (R6).
    skipped_empty      : pages that yielded no extractable text (R16).
    documents_written  : ``Document``s written to the JSONL corpus (R19).
    out_path           : path of the written JSONL corpus file.
    """

    requested: int
    skipped_allowlist: int
    skipped_robots: int
    skipped_empty: int
    documents_written: int
    out_path: str


class WowheadIngestor:
    """Runs the courteous ingest flow and writes a JSONL corpus.

    Depends only on the ``Fetcher`` interface and injected collaborators, so the
    whole flow is testable end-to-end with fakes + fixtures (R29).

    Parameters
    ----------
    fetcher:
        The ``Fetcher`` performing HTTP GETs (real or fake).
    robots:
        ``RobotsGate`` consulted before every fetch (R5, R6).
    limiter:
        ``RateLimiter`` enforcing the courtesy interval (R8, R9).
    normalizer:
        ``WowheadNormalizer`` turning HTML into ``Document``s (R12-R16).
    allowed_host:
        Only URLs on this host are fetched; others are skipped (R17, R18).
    max_pages:
        Hard cap on URLs processed per run (defense against runaway crawls).
    """

    def __init__(
        self,
        fetcher: Fetcher,
        robots: RobotsGate,
        limiter: RateLimiter,
        normalizer: WowheadNormalizer,
        *,
        allowed_host: str,
        max_pages: int,
    ) -> None:
        self._fetcher = fetcher
        self._robots = robots
        self._limiter = limiter
        self._normalizer = normalizer
        self._allowed_host = allowed_host
        self._max_pages = max_pages

    def run(self, seed_urls: list[str], out_dir: str | Path) -> IngestReport:
        """Ingest ``seed_urls`` and write the JSONL corpus to ``out_dir``.

        Applies the strict allowlist -> robots -> rate-limit -> fetch ->
        normalize order per URL (up to ``max_pages``), writes every produced
        ``Document`` to ``out_dir/wowhead.jsonl`` (R19) and returns the counts
        (R23).
        """
        out_path = Path(out_dir) / CORPUS_FILENAME
        out_path.parent.mkdir(parents=True, exist_ok=True)

        requested = 0
        skipped_allowlist = 0
        skipped_robots = 0
        skipped_empty = 0
        written = 0

        with out_path.open("w", encoding="utf-8") as fh:
            for url in seed_urls[: self._max_pages]:
                requested += 1

                if not self._on_allowlist(url):  # R18
                    skipped_allowlist += 1
                    logger.info("skipping off-allowlist URL %s", url)
                    continue

                if not self._robots.allowed(url):  # R5, R6
                    skipped_robots += 1
                    logger.info("skipping robots-disallowed URL %s", url)
                    continue

                self._limiter.acquire()  # R8, R9

                try:
                    result = self._fetcher.get(url)
                except FetchError as exc:
                    skipped_empty += 1
                    logger.warning("fetch failed for %s (%s); skipping", url, exc)
                    continue

                doc = self._normalizer.normalize(result.text, result.url)  # R12-R15
                if doc is None:  # R16
                    skipped_empty += 1
                    logger.info("no document produced for %s; skipping", url)
                    continue

                fh.write(doc.model_dump_json() + "\n")  # R19
                written += 1

        return IngestReport(
            requested=requested,
            skipped_allowlist=skipped_allowlist,
            skipped_robots=skipped_robots,
            skipped_empty=skipped_empty,
            documents_written=written,
            out_path=str(out_path),
        )

    def _on_allowlist(self, url: str) -> bool:
        """True iff ``url``'s host equals the configured allowed host (R18)."""
        return urlsplit(url).netloc == self._allowed_host
