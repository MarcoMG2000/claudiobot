"""Wowhead ingest flow: courteous transport (fetch + robots + rate-limit).

f11 is the only part of the system that contacts a real external service. This
subpackage isolates that flow: a ``Fetcher`` swap point (HTTP GET only), robots
compliance, rate limiting, an HTML normalizer, the ingest pipeline and a CLI.

Importing this package does NOT eagerly import ``httpx`` or the HTML parser
(``selectolax``): those are lazy imports inside ``HttpxFetcher.__init__`` /
``WowheadNormalizer.__init__``, so the module stays importable network-free and
parser-free for the default test suite (R25).
"""

from wowrag.ingest.wowhead.base import (
    Fetcher,
    FetchError,
    FetchResult,
    IngestError,
    ScrapeError,
)
from wowrag.ingest.wowhead.cli import main
from wowrag.ingest.wowhead.fetcher import FakeFetcher, HttpxFetcher
from wowrag.ingest.wowhead.normalizer import WowheadNormalizer
from wowrag.ingest.wowhead.pipeline import IngestReport, WowheadIngestor
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
    "WowheadNormalizer",
    "WowheadIngestor",
    "IngestReport",
    "main",
]
