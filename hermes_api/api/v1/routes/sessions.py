"""Session resource routes for the Hermes Agent HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from hermes_api.auth import require_admin, require_bearer_token
from hermes_api.repositories.sessions import delete_session, get_session, list_sessions
from hermes_api.schemas import ApiResponse, PaginatedSessionsResponse, SessionSummary

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    dependencies=[Depends(require_bearer_token)],
)


@router.get(
    "",
    response_model=PaginatedSessionsResponse,
    summary="List cached API chat sessions",
)
def get_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedSessionsResponse:
    """Return process-local API sessions with pagination."""

    total, sessions = list_sessions(limit=limit, offset=offset)
    return PaginatedSessionsResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=sessions,
    )


@router.get(
    "/{session_id}",
    response_model=ApiResponse[SessionSummary],
    summary="Get a cached API chat session",
)
def get_cached_session(session_id: str) -> ApiResponse[SessionSummary]:
    """Return one process-local API session by id."""

    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return ApiResponse(data=session, message="Session found")


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="Delete a cached API chat session",
)
def remove_session(session_id: str) -> Response:
    """Delete one process-local API session."""

    if not delete_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
