"""Transport models for the HTTP API (f9).

Only the request needs a dedicated transport model. The response reuses
``wowrag.models.Answer`` directly via ``response_model=Answer`` (no mirror
schema), so the citation/metadata shape stays 1:1 with f8 (R7).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class AskRequest(BaseModel):
    """Body of ``POST /ask``.

    Fields
    ------
    query   : User's question. Non-empty / non-whitespace (validated -> 422).
    persona : Optional persona name. ``None`` -> default resolved by f8/config
              (``Settings.default_persona``); the HTTP layer does not duplicate
              that default logic. (R10, R11)
    """

    query: str
    persona: str | None = None  # nombre de persona; None -> default por config (R10, R11)

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, v: str) -> str:
        # R15: reject empty / whitespace-only query at the transport layer so it
        # surfaces as a clean 422 BEFORE the orchestrator is invoked.
        if not v or not v.strip():
            raise ValueError("query must be a non-empty string")
        return v
