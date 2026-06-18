"""Wowhead ingest flow: courteous transport (fetch + robots + rate-limit).

f11 is the only part of the system that contacts a real external service. This
subpackage isolates that flow: a ``Fetcher`` swap point (HTTP GET only), robots
compliance, and rate limiting. Slice B adds the HTML normalizer, the pipeline
and the CLI.

Importing this package does NOT eagerly import ``httpx`` or the HTML parser:
those are lazy imports inside ``HttpxFetcher.__init__`` / the (Slice B)
normalizer, so the module stays importable network-free for the default test
suite (R25).
"""

from wowrag.ingest.wowhead.base import (
    Fetcher,
    FetchError,
    FetchResult,
    IngestError,
    ScrapeError,
)
from wowrag.ingest.wowhead.fetcher import FakeFetcher, HttpxFetcher
from wowrag.ingest.wowhead.robots import RobotsGate
from wowrag.ingest.wowhead.throttle import RateLimiter

__all__ = [
    "Fetcher",
    "FetchResult",
    "IngestError",
    "FetchError",
    "ScrapeError",
    "HttpxFetcher",
    "FakeFetcher",
    "RobotsGate",
    "RateLimiter",
]
