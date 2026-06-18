"""``python -m wowrag.ingest.wowhead`` entrypoint (R22).

Delegates to ``cli.main`` and propagates its exit code via ``SystemExit`` so the
process returns the proper status. Heavy composition (httpx / selectolax) is lazy
inside ``cli.main`` (R25), so this module stays free of those dependencies.
"""

from __future__ import annotations

from wowrag.ingest.wowhead.cli import main

raise SystemExit(main())
