"""WowheadNormalizer: HTML -> Document (R12-R16, R31).

The HTML-parsing dependency (``selectolax``) is pinned in ``requirements.txt`` and
installed by ``init.sh``, but it is still imported LAZILY inside
``WowheadNormalizer.__init__`` (R25), mirroring the ``HttpxFetcher`` / ``OllamaLLM``
pattern: importing this module does NOT pull ``selectolax`` eagerly. If the parser
is somehow absent, ``__init__`` raises ``ScrapeError`` (not a raw ``ImportError``,
R31) rather than failing at module import time.

``normalize(html, source_url)`` strips boilerplate (nav / ads / scripts / chrome,
R12), extracts the main text (R12), the page ``title`` (R14) and a sub-section
heading or ``""`` (R15), and populates ``source_url`` (R13). When no main text
survives the cleanup it returns ``None`` (R16) so the pipeline skips the page
without building an invalid empty-``text`` ``Document`` (which f1 rejects).

``Document`` is IMPORTED from ``wowrag.models`` — f11 does not touch the schema
(R26).
"""

from __future__ import annotations

import logging
import re

from wowrag.ingest.wowhead.base import ScrapeError
from wowrag.models import Document

logger = logging.getLogger(__name__)

# Boilerplate containers to drop before extracting text (R12). Structural tags
# plus wowhead-style nav/ad/menu selectors. The list is intentionally a module
# constant so it is easy to tune; the HTML fixtures exercise it.
_BOILERPLATE_SELECTORS: tuple[str, ...] = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "#header",
    "#footer",
    "#nav",
    ".nav",
    ".menu",
    ".ad",
    ".ads",
    ".advertisement",
    "[role=navigation]",
    "[role=banner]",
)

# Preferred main-content containers, tried in order; fall back to <body> (R12).
_MAIN_SELECTORS: tuple[str, ...] = (
    "#main-contents",
    "main",
    "article",
    ".text",
    "#main",
)

_WS_RE = re.compile(r"\s+")


class WowheadNormalizer:
    """Parses wowhead HTML into a ``Document`` (R12-R16).

    The parser import is lazy (R25); a missing dependency raises ``ScrapeError``
    (R31). One instance can normalize many pages.
    """

    def __init__(self) -> None:
        try:
            from selectolax.parser import HTMLParser  # lazy import (R25)
        except ImportError as exc:
            raise ScrapeError(
                "HTML parser (selectolax) not installed. "
                "Install dependencies: pip install -r requirements.txt"
            ) from exc  # R31
        self._HTMLParser = HTMLParser

    def normalize(self, html: str, source_url: str) -> Document | None:
        """Turn ``html`` from ``source_url`` into a ``Document`` (or ``None``).

        Returns ``None`` when no main text survives boilerplate removal (R16),
        so the caller skips the page instead of emitting an invalid empty
        ``Document``.
        """
        tree = self._HTMLParser(html)
        title = self._extract_title(tree)  # before stripping (uses <title>/<h1>)
        section = self._extract_section(tree)  # R15
        self._strip_boilerplate(tree)  # R12
        text = self._extract_text(tree)  # R12
        if not text.strip():
            logger.info("no extractable text for %s; skipping", source_url)
            return None  # R16
        return Document(
            text=text,
            source_url=source_url,  # R13
            title=title,  # R14
            section=section,  # R15
        )

    def _strip_boilerplate(self, tree) -> None:
        """Remove nav / ads / scripts / chrome from the tree in place (R12)."""
        for selector in _BOILERPLATE_SELECTORS:
            for node in tree.css(selector):
                node.decompose()

    def _extract_title(self, tree) -> str:
        """Title from the content ``<h1>`` if present, else ``<title>`` (R14)."""
        h1 = tree.css_first("h1")
        if h1 is not None:
            text = _normalize_ws(h1.text())
            if text:
                return text
        title = tree.css_first("title")
        if title is not None:
            return _normalize_ws(title.text())
        return ""

    def _extract_section(self, tree) -> str:
        """First sub-section heading (``<h2>``) within the content, else ``""``.

        Defaults to ``""`` when the page carries no sub-section (R15), matching
        ``Document.section``'s default.
        """
        h2 = tree.css_first("h2")
        if h2 is not None:
            return _normalize_ws(h2.text())
        return ""

    def _extract_text(self, tree) -> str:
        """Main body text with whitespace normalized (R12).

        Prefers a known wowhead content container; falls back to the cleaned
        ``<body>`` so unrecognized layouts still yield text.
        """
        for selector in _MAIN_SELECTORS:
            node = tree.css_first(selector)
            if node is not None:
                text = _normalize_ws(node.text())
                if text:
                    return text
        body = tree.css_first("body")
        if body is not None:
            return _normalize_ws(body.text())
        return _normalize_ws(tree.text())


def _normalize_ws(text: str | None) -> str:
    """Collapse all runs of whitespace to single spaces and strip the ends."""
    if not text:
        return ""
    return _WS_RE.sub(" ", text).strip()
