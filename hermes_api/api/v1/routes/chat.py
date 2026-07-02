"""Chat routes for the Hermes Agent HTTP API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from hermes_api.auth import require_bearer_token
from hermes_api.schemas import ApiResponse, ChatRequest, ChatResponse
from hermes_api.service import run_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ApiResponse[ChatResponse],
    dependencies=[Depends(require_bearer_token)],
    summary="Run a Hermes chat turn",
)
def chat(payload: ChatRequest) -> ApiResponse[ChatResponse]:
    """Run one Hermes chat turn and return the final response."""

    try:
        response = run_chat(
            message=payload.message,
            session_id=payload.session_id,
            model=payload.model,
            provider=payload.provider,
            enabled_toolsets=payload.enabled_toolsets,
            disabled_toolsets=payload.disabled_toolsets,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Hermes API chat turn failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hermes chat turn failed",
        ) from exc

    return ApiResponse(
        data=ChatResponse(response=response, session_id=payload.session_id),
        message="Chat completed successfully",
    )
