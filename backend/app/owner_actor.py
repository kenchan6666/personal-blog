from __future__ import annotations

from contextvars import ContextVar

owner_actor: ContextVar[str] = ContextVar("owner_actor", default="session")


def force_draft_if_service(status: str) -> str:
    if owner_actor.get() == "service" and status == "published":
        return "draft"
    return status
