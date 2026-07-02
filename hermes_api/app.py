"""FastAPI app exposing Hermes Agent as an HTTP API."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Awaitable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from hermes_api import __version__
from hermes_api.api.v1 import router as v1_router
from hermes_api.core.config import get_settings
from hermes_api.observability import metrics
from hermes_api.rate_limit import rate_limiter
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
async def api_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Apply rate limiting, metrics, and sanitized request-completion logs."""

    started = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"
    try:
        rate_limiter.check(
            key=client_host,
            limit_per_minute=settings.rate_limit_per_minute,
        )
        response = await call_next(request)
    except HTTPException as exc:
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics.record(path=request.url.path, status_code=response.status_code)
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


@app.get("/metrics", response_class=PlainTextResponse, tags=["monitoring"])
def get_metrics() -> str:
    """Return process-local Prometheus-style API metrics."""

    return metrics.render_prometheus()


app.include_router(v1_router)
