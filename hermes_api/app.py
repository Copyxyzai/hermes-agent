"""FastAPI app exposing Hermes Agent as an HTTP API."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from hermes_api import __version__
from hermes_api.api.v1 import router as v1_router
from hermes_api.core.config import get_settings
from hermes_api.schemas import HealthResponse

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Hermes Agent API",
    version=__version__,
    description="HTTP API for running Hermes Agent chat turns and inspecting API resources.",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], object]
) -> Response:
    """Log request method, path, status, and latency without sensitive values."""

    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if settings.request_log_enabled:
        logger.info(
            "Hermes API request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
    return response


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Return a simple liveness response."""

    return HealthResponse(status="ok")


app.include_router(v1_router)
