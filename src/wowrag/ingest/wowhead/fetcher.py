"""Fetcher implementations: HttpxFetcher (real, lazy httpx) and FakeFetcher.

The ``httpx`` import is lazy (inside ``HttpxFetcher.__init__``), so this module
is importable without ``httpx`` installed (R25). Only instantiation requires the
dependency; failing that raises ``FetchError``, not ``ImportError`` (R3). This
mirrors the ``OllamaLLM`` pattern (f7).

``FakeFetcher`` serves a predefined ``url -> FetchResult`` map without any
network access (R4) and records every requested URL, so tests can prove that
URLs disallowed by robots.txt or outside the allowlist are NEVER fetched
(R5, R6).
"""

from __future__ import annotations

from wowrag.ingest.wowhead.base import FetchError, FetchResult


class HttpxFetcher:
    """Real ``Fetcher`` backed by ``httpx``.

    The ``httpx`` import happens inside ``__init__`` (R25); a missing dependency
    raises ``FetchError`` (not ``ImportError``, R3). Every request carries the
    configured ``User-Agent`` header (R10).

    Parameters
    ----------
    user_agent:
        Descriptive, identifiable ``User-Agent`` sent on every request (R10).
    timeout:
        Per-request timeout in seconds. Default: ``30.0``.
    """

    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        try:
            import httpx  # lazy import (R25)
        except ImportError as exc:
            raise FetchError(
                "HTTP client not installed. "
                "Install scrape dependencies: pip install -r requirements-scrape.txt"
            ) from exc  # R3
        self._httpx = httpx
        self._headers = {"User-Agent": user_agent}  # R10
        self._timeout = timeout

    def get(self, url: str) -> FetchResult:
        """GET ``url`` and return its final URL, status code and body text.

        Follows redirects so the returned ``FetchResult.url`` is canonical.

        Raises
        ------
        FetchError
            On any transport failure (unreachable host, client error).
        """
        try:
            resp = self._httpx.get(
                url,
                headers=self._headers,
                timeout=self._timeout,
                follow_redirects=True,
            )
        except Exception as exc:  # connection / transport error (R3 family)
            raise FetchError(f"GET failed for {url}: {exc}") from exc
        return FetchResult(
            url=str(resp.url),
            status_code=resp.status_code,
            text=resp.text,
        )


class FakeFetcher:
    """Network-free ``Fetcher`` for tests (R4).

    Serves a predefined ``url -> FetchResult`` map and records every requested
    URL in ``requested_urls`` (in call order). Tests use the recorded calls to
    prove that disallowed / off-allowlist URLs are NEVER fetched (R5, R6).

    Parameters
    ----------
    responses:
        Mapping of URL to either a ``FetchResult`` or a ``(status_code, text)``
        tuple. Missing URLs raise ``FetchError`` unless ``default_status`` is set.
    default_status:
        If set, unmapped URLs return an empty-body ``FetchResult`` with this
        status code instead of raising (useful to simulate 404s).
    """

    def __init__(
        self,
        responses: dict[str, FetchResult | tuple[int, str]] | None = None,
        *,
        default_status: int | None = None,
    ) -> None:
        self._responses: dict[str, FetchResult] = {}
        for url, value in (responses or {}).items():
            if isinstance(value, FetchResult):
                self._responses[url] = value
            else:
                status, text = value
                self._responses[url] = FetchResult(
                    url=url, status_code=status, text=text
                )
        self._default_status = default_status
        self.requested_urls: list[str] = []

    def get(self, url: str) -> FetchResult:
        """Return the mapped ``FetchResult`` for ``url`` and record the request.

        Raises
        ------
        FetchError
            When ``url`` is unmapped and no ``default_status`` was configured.
        """
        self.requested_urls.append(url)
        result = self._responses.get(url)
        if result is not None:
            return result
        if self._default_status is not None:
            return FetchResult(url=url, status_code=self._default_status, text="")
        raise FetchError(f"FakeFetcher has no response configured for {url}")
