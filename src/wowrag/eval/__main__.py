"""``python -m wowrag.eval`` entrypoint (R24).

Delegates to ``cli.main`` and propagates its exit code via ``SystemExit`` so the
process returns the proper status. Heavy composition is lazy inside ``cli.main``
(R26), so this module stays free of torch / psycopg / httpx.
"""

from __future__ import annotations

from wowrag.eval.cli import main

raise SystemExit(main())
