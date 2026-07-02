"""Internal API models for session resources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionRecord:
    """Process-local cached API session metadata."""

    session_id: str
    model: str
    provider: str | None
    enabled_toolsets: tuple[str, ...]
    disabled_toolsets: tuple[str, ...]
