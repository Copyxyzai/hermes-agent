"""Pydantic schemas for the Hermes Agent HTTP API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Standard success envelope for API responses."""

    data: DataT
    message: str


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str


class ChatRequest(BaseModel):
    """Request body for a single Hermes chat turn."""

    message: str = Field(..., min_length=1)
    session_id: str | None = None
    model: str | None = None
    provider: str | None = None
    enabled_toolsets: list[str] | None = None
    disabled_toolsets: list[str] | None = None


class ChatResponse(BaseModel):
    """Response body returned after Hermes completes a chat turn."""

    response: str
    session_id: str | None = None


class SessionSummary(BaseModel):
    """Summary of a process-local API chat session."""

    session_id: str
    model: str
    provider: str | None = None
    enabled_toolsets: list[str]
    disabled_toolsets: list[str]


class PaginatedSessionsResponse(BaseModel):
    """Paginated list of process-local API sessions."""

    limit: int
    offset: int
    total: int
    data: list[SessionSummary]


class ToolsetSummary(BaseModel):
    """Description of a Hermes toolset exposed through the API."""

    name: str
    tools: list[str]


class PaginatedToolsetsResponse(BaseModel):
    """Paginated list of Hermes toolsets."""

    limit: int
    offset: int
    total: int
    data: list[ToolsetSummary]
