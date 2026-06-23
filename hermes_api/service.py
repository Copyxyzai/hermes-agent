"""Service layer that adapts FastAPI requests to ``AIAgent`` calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from run_agent import AIAgent
from hermes_api.models.session import SessionRecord
from hermes_api.schemas import SessionSummary

DEFAULT_ENABLED_TOOLSETS = ["web"]
DEFAULT_DISABLED_TOOLSETS = ["terminal"]


@dataclass
class _AgentConfig:
    model: str | None
    provider: str | None
    enabled_toolsets: tuple[str, ...]
    disabled_toolsets: tuple[str, ...]


@dataclass
class _SessionAgent:
    agent: AIAgent
    config: _AgentConfig
    lock: Lock = field(default_factory=Lock)


class AgentSessionStore:
    """In-memory cache of Hermes agents keyed by session id.

    The API is intentionally small and process-local. It prevents concurrent
    turns for the same session from interleaving inside a single ``AIAgent``
    instance while keeping different sessions independent.
    """

    def __init__(self) -> None:
        self._agents: dict[str, _SessionAgent] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        session_id: str,
        *,
        model: str | None = None,
        provider: str | None = None,
        enabled_toolsets: list[str] | None = None,
        disabled_toolsets: list[str] | None = None,
    ) -> _SessionAgent:
        config = _agent_config(
            model=model,
            provider=provider,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )
        with self._lock:
            cached = self._agents.get(session_id)
            if cached is None or cached.config != config:
                cached = _SessionAgent(
                    agent=create_agent(
                        session_id=session_id,
                        model=model,
                        provider=provider,
                        enabled_toolsets=enabled_toolsets,
                        disabled_toolsets=disabled_toolsets,
                    ),
                    config=config,
                )
                self._agents[session_id] = cached
            return cached

    def _to_summary(self, session_id: str, cached: _SessionAgent) -> SessionSummary:
        record = SessionRecord(
            session_id=session_id,
            model=cached.config.model or "",
            provider=cached.config.provider,
            enabled_toolsets=cached.config.enabled_toolsets,
            disabled_toolsets=cached.config.disabled_toolsets,
        )
        return SessionSummary(
            session_id=record.session_id,
            model=record.model,
            provider=record.provider,
            enabled_toolsets=list(record.enabled_toolsets),
            disabled_toolsets=list(record.disabled_toolsets),
        )

    def list_sessions(self) -> list[SessionSummary]:
        """Return summaries for all process-local cached sessions."""

        with self._lock:
            return [
                self._to_summary(session_id, cached)
                for session_id, cached in sorted(self._agents.items())
            ]

    def get(self, session_id: str) -> SessionSummary | None:
        """Return one process-local cached session by id."""

        with self._lock:
            cached = self._agents.get(session_id)
            if cached is None:
                return None
            return self._to_summary(session_id, cached)

    def delete(self, session_id: str) -> bool:
        """Remove a cached session and return whether it existed."""

        with self._lock:
            return self._agents.pop(session_id, None) is not None

    def clear(self) -> None:
        """Clear cached agents; used by tests and future lifecycle hooks."""

        with self._lock:
            self._agents.clear()


session_store = AgentSessionStore()


def _effective_enabled_toolsets(enabled_toolsets: list[str] | None) -> list[str]:
    return (
        enabled_toolsets
        if enabled_toolsets is not None
        else list(DEFAULT_ENABLED_TOOLSETS)
    )


def _effective_disabled_toolsets(disabled_toolsets: list[str] | None) -> list[str]:
    return (
        disabled_toolsets
        if disabled_toolsets is not None
        else list(DEFAULT_DISABLED_TOOLSETS)
    )


def _agent_config(
    *,
    model: str | None,
    provider: str | None,
    enabled_toolsets: list[str] | None,
    disabled_toolsets: list[str] | None,
) -> _AgentConfig:
    return _AgentConfig(
        model=model or "",
        provider=provider,
        enabled_toolsets=tuple(_effective_enabled_toolsets(enabled_toolsets)),
        disabled_toolsets=tuple(_effective_disabled_toolsets(disabled_toolsets)),
    )


def create_agent(
    *,
    session_id: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    enabled_toolsets: list[str] | None = None,
    disabled_toolsets: list[str] | None = None,
) -> AIAgent:
    """Create a conservatively scoped Hermes agent for API traffic."""

    return AIAgent(
        model=model or "",
        provider=provider,
        session_id=session_id,
        enabled_toolsets=_effective_enabled_toolsets(enabled_toolsets),
        disabled_toolsets=_effective_disabled_toolsets(disabled_toolsets),
        quiet_mode=True,
    )


def run_chat(
    *,
    message: str,
    session_id: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    enabled_toolsets: list[str] | None = None,
    disabled_toolsets: list[str] | None = None,
) -> str:
    """Run one chat turn through Hermes and return the final response."""

    if session_id:
        cached = session_store.get_or_create(
            session_id,
            model=model,
            provider=provider,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )
        with cached.lock:
            return cached.agent.chat(message)

    agent = create_agent(
        model=model,
        provider=provider,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
    )
    return agent.chat(message)
