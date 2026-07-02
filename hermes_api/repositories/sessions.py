"""Repository facade for process-local API chat sessions."""

from __future__ import annotations

from hermes_api.schemas import SessionSummary
from hermes_api.service import session_store


def list_sessions(*, limit: int, offset: int) -> tuple[int, list[SessionSummary]]:
    """Return a paginated view of cached API sessions."""

    summaries = session_store.list_sessions()
    total = len(summaries)
    return total, summaries[offset : offset + limit]


def get_session(session_id: str) -> SessionSummary | None:
    """Return a cached API session by id when it exists."""

    return session_store.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete a cached API session if it exists."""

    return session_store.delete(session_id)
