"""FastAPI application factory for the RAG API (f9).

``create_app`` assembles the app: registers the router (``/ask``, ``/health``)
and adds CORS middleware whose origins/flags come from ``Settings`` (not
hardcoded), so a future in-game frontend can be allow-listed by configuration
(R1, R13, R14).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wowrag.api.routes import router
from wowrag.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI app with routes and CORS registered (R1).

    Parameters
    ----------
    settings:
        Optional ``Settings`` override (used by tests to exercise a closed CORS
        allow-list instead of the ``"*"`` default). ``None`` -> ``Settings()``.

    CORS origins/flags are read from ``Settings`` (R13, R14): they are not
    hardcoded in this module; the ``"*"`` default lives in ``Settings`` and can
    be closed to a fixed allow-list per environment.
    """
    settings = settings or Settings()

    app = FastAPI(title="wow-classic-rag API")

    # R13/R14: CORS from Settings, not hardcoded. "*" is only the explicit default.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    app.include_router(router)
    return app
