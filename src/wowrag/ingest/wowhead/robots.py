"""RobotsGate: robots.txt compliance, consulted before every fetch (R5-R7).

Uses the stdlib ``urllib.robotparser.RobotFileParser`` — NO new dependency. The
host's ``robots.txt`` is fetched through the SAME ``Fetcher`` (so it is subject
to the configured User-Agent and, in the pipeline, the rate limiter), parsed
once and cached per host (R7); subsequent URLs of the same host reuse the cached
parser instead of re-downloading.

Courtesy policy for an inaccessible ``robots.txt`` (see ``design.md`` §11):
**permissive and logged** — if the host publishes no ``robots.txt`` or returns a
non-2xx status / transport error, the URL is treated as allowed and the reason
is logged. This default avoids blocking hosts that simply have no robots file;
an operator can harden it.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from wowrag.ingest.wowhead.base import Fetcher, FetchError

logger = logging.getLogger(__name__)


class RobotsGate:
    """Decides whether a URL may be fetched per the host's robots.txt + UA.

    Caches one ``RobotFileParser`` per host (R7). ``allowed(url)`` is consulted
    BEFORE every real fetch in the pipeline (R5); the pipeline skips the URL when
    it returns ``False`` (R6).

    Parameters
    ----------
    user_agent:
        The User-Agent used to evaluate ``robots.txt`` rules (R5).
    fetcher:
        The same ``Fetcher`` used for content fetches, reused to download
        ``robots.txt`` (so it carries the UA and any upstream rate limit).
    """

    def __init__(self, user_agent: str, fetcher: Fetcher) -> None:
        self._ua = user_agent
        self._fetcher = fetcher
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        """Return whether ``url`` may be fetched for the configured UA (R5).

        Downloads and caches the host's ``robots.txt`` on first use (R7). On an
        inaccessible ``robots.txt`` the URL is treated as allowed and logged
        (permissive policy, ``design.md`` §11).
        """
        parts = urlsplit(url)
        host = parts.netloc
        rp = self._cache.get(host)
        if rp is None:
            rp = self._load(parts.scheme, host)
            self._cache[host] = rp  # R7: cache per host
        return rp.can_fetch(self._ua, url)  # R5

    def _load(self, scheme: str, host: str) -> RobotFileParser:
        """Fetch and parse ``robots.txt`` for ``host`` via the shared Fetcher.

        Returns a permissive parser (allows everything) when robots.txt is
        absent or unreachable (permissive policy, logged).
        """
        rp = RobotFileParser()
        robots_url = urlunsplit((scheme or "https", host, "/robots.txt", "", ""))
        try:
            result = self._fetcher.get(robots_url)
        except FetchError as exc:
            logger.info(
                "robots.txt unreachable for %s (%s); assuming allowed", host, exc
            )
            rp.allow_all = True  # permissive default (design.md §11)
            return rp
        if result.status_code >= 400 or not result.text.strip():
            logger.info(
                "robots.txt missing for %s (status %s); assuming allowed",
                host,
                result.status_code,
            )
            rp.allow_all = True  # permissive default (design.md §11)
            return rp
        rp.parse(result.text.splitlines())
        return rp
