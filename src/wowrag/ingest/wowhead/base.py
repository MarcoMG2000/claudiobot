"""Fetcher interface, domain errors and the FetchResult value object (R1).

This is the swap point for the wowhead ingest flow's HTTP transport. The
``Fetcher`` Protocol does HTTP GET *only*; robots.txt compliance and rate
limiting are separate collaborators (``RobotsGate``, ``RateLimiter``) that wrap
the fetcher in the pipeline (single responsibility — see ``design.md`` §3).

The error hierarchy mirrors f1's ``CorpusError`` family so callers can catch by
family: ``IngestError`` is the base; ``FetchError`` (transport / missing httpx)
and ``ScrapeError`` (HTML-parsing dependency missing or unparsable) derive from
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class IngestError(Exception):
    """Base error for the wowhead ingest flow."""


class FetchError(IngestError):
    """Raised when an HTTP GET fails or the HTTP-client dependency is missing."""


class ScrapeError(IngestError):
    """Raised when the HTML-parsing dependency is missing or HTML is unparsable."""


@dataclass(frozen=True)
class FetchResult:
    """Body text and status code of an HTTP GET.

    ``url`` is the final (post-redirect) URL the body came from, so the
    normalizer can populate ``Document.source_url`` with the canonical URL.
    """

    url: str
    status_code: int
    text: str


class Fetcher(Protocol):
    """Swap point: HTTP GET a URL -> ``FetchResult``.

    Implementations: ``HttpxFetcher`` (real, lazy httpx) and ``FakeFetcher``
    (deterministic, network-free, for tests). Robots and rate-limit are NOT this
    interface's responsibility; they wrap the fetcher in the pipeline.
    """

    def get(self, url: str) -> FetchResult:
        """Perform an HTTP GET for ``url`` and return its body and status.

        Raises
        ------
        FetchError
            On any transport failure (unreachable host, HTTP client error).
        """
        ...
