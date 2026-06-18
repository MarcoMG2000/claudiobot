"""Tests for the wowhead ingest CLI entrypoint (Slice B): R21, R22, R23, R25.

All network-free: a ``FakeFetcher`` is injected into ``main`` (R29) so the real
``HttpxFetcher`` is never built. Most tests replace the real ``WowheadNormalizer``
with a fake one via monkeypatch to keep the orchestration assertions focused; the
lazy real composition (R25) is verified by a separate import-isolation subprocess
test. One test runs the full real normalizer end-to-end against the HTML fixture
(selectolax is installed by init.sh via requirements.txt, so it runs).
"""

from __future__ import annotations

from pathlib import Path

import wowrag.ingest.wowhead.cli as cli
from wowrag.ingest.wowhead import FakeFetcher, WowheadIngestor
from wowrag.ingest.wowhead.robots import RobotsGate
from wowrag.ingest.wowhead.throttle import RateLimiter
from wowrag.models import Document

UA = "wow-classic-rag-bot/0.1 (+contact)"
HOST = "www.wowhead.com"
HTTPS = f"https://{HOST}"
ROBOTS_URL = f"{HTTPS}/robots.txt"
ROBOTS_BODY = "User-agent: *\nDisallow: /forums\n"

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wowhead"


class FakeNormalizer:
    """Returns a Document without parsing, so the CLI runs without selectolax."""

    def normalize(self, html: str, source_url: str) -> Document | None:
        return Document(
            text=html.strip(), source_url=source_url, title="Fireball", section=""
        )


def _patch_parser_free_ingestor(monkeypatch) -> None:
    """Replace _build_ingestor so the CLI composes a fake (parser-free) normalizer.

    Keeps the injectable-fetcher contract intact while avoiding the real
    selectolax-backed normalizer in the default suite.
    """

    def _build(fetcher, settings):
        robots = RobotsGate(settings.scrape_user_agent, fetcher)
        limiter = RateLimiter(0.0, clock=lambda: 0.0, sleep=lambda _s: None)
        return WowheadIngestor(
            fetcher,
            robots,
            limiter,
            FakeNormalizer(),
            allowed_host=settings.scrape_allowed_host,
            max_pages=settings.scrape_max_pages,
        )

    monkeypatch.setattr(cli, "_build_ingestor", _build)


def _fetcher(url: str) -> FakeFetcher:
    return FakeFetcher({ROBOTS_URL: (200, ROBOTS_BODY), url: (200, "Fireball body")})


# ---------------------------------------------------------------------------
# R22: main([url], fetcher=fake) returns 0 and writes the corpus to --out
# ---------------------------------------------------------------------------


def test_main_runs_with_injected_fetcher(tmp_path, monkeypatch, capsys):  # R22
    """main([url], fetcher=fake) returns 0 and writes out_dir/wowhead.jsonl."""
    _patch_parser_free_ingestor(monkeypatch)
    url = f"{HTTPS}/spell=133"

    rc = cli.main([url, "--out", str(tmp_path)], fetcher=_fetcher(url))

    assert rc == 0
    out_file = tmp_path / "wowhead.jsonl"
    assert out_file.exists()
    lines = [ln for ln in out_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    capsys.readouterr()


# ---------------------------------------------------------------------------
# R23: stdout summary carries the counts
# ---------------------------------------------------------------------------


def test_main_prints_summary(tmp_path, monkeypatch, capsys):  # R23
    """main prints a human-readable summary with the run counts."""
    _patch_parser_free_ingestor(monkeypatch)
    url = f"{HTTPS}/spell=133"

    cli.main([url, "--out", str(tmp_path)], fetcher=_fetcher(url))

    out = capsys.readouterr().out
    assert "wowhead ingest" in out
    assert "urls requested" in out
    assert "documents written" in out


# ---------------------------------------------------------------------------
# R21: without --out, the default output dir is Settings.scrape_corpus_path
# ---------------------------------------------------------------------------


def test_cli_uses_settings_out_default(tmp_path, monkeypatch, capsys):  # R21
    """Without --out, the corpus is written under Settings.scrape_corpus_path."""
    _patch_parser_free_ingestor(monkeypatch)
    out_dir = tmp_path / "configured_corpus"
    monkeypatch.setenv("SCRAPE_CORPUS_PATH", str(out_dir))
    url = f"{HTTPS}/spell=133"

    rc = cli.main([url], fetcher=_fetcher(url))

    assert rc == 0
    assert (out_dir / "wowhead.jsonl").exists()
    capsys.readouterr()


# ---------------------------------------------------------------------------
# R29: the injected fetcher short-circuits real HttpxFetcher construction
# ---------------------------------------------------------------------------


def test_main_does_not_build_real_fetcher_when_injected(
    tmp_path, monkeypatch, capsys
):  # R29
    """With a fetcher injected, _build_fetcher (real httpx) is never called."""
    _patch_parser_free_ingestor(monkeypatch)

    def _boom(_settings):  # pragma: no cover - must never run
        raise AssertionError("real fetcher must not be built when one is injected")

    monkeypatch.setattr(cli, "_build_fetcher", _boom)
    url = f"{HTTPS}/spell=133"

    rc = cli.main([url, "--out", str(tmp_path)], fetcher=_fetcher(url))

    assert rc == 0
    capsys.readouterr()


# ---------------------------------------------------------------------------
# R25: importing the CLI module pulls neither httpx nor selectolax
# ---------------------------------------------------------------------------


def test_import_cli_is_network_free():  # R25
    """Importing wowrag.ingest.wowhead(.cli) pulls no httpx/selectolax.

    Runs in a fresh subprocess so the assertion is independent of what the test
    session already imported. The CLI composes the real fetcher/normalizer lazily
    inside _build_*, so the module imports never pull httpx or selectolax.
    """
    import os
    import subprocess
    import sys

    src = Path(__file__).resolve().parent.parent / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")

    code = (
        "import sys; import wowrag.ingest.wowhead; import wowrag.ingest.wowhead.cli; "
        "heavy = [m for m in ('httpx', 'selectolax') if m in sys.modules]; "
        "assert not heavy, heavy; print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


# ---------------------------------------------------------------------------
# Full CLI with the REAL normalizer over the HTML fixture (selectolax installed)
# ---------------------------------------------------------------------------


def test_main_end_to_end_with_real_normalizer(tmp_path, capsys):  # R22, R20
    """main runs the real selectolax normalizer over the fixture end-to-end."""
    from wowrag.ingest import JsonlCorpusLoader

    url = f"{HTTPS}/spell=133"
    html = (FIXTURES / "spell_fireball.html").read_text(encoding="utf-8")
    fetcher = FakeFetcher({ROBOTS_URL: (200, ROBOTS_BODY), url: (200, html)})

    rc = cli.main([url, "--out", str(tmp_path)], fetcher=fetcher)

    assert rc == 0
    docs = JsonlCorpusLoader().load(tmp_path)
    assert len(docs) == 1
    assert docs[0].title == "Fireball"
    capsys.readouterr()
