"""Authentication helpers for the Hermes Agent HTTP API."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status

API_TOKEN_ENV = "HERMES_API_TOKEN"


def require_bearer_token(authorization: str | None = Header(default=None)) -> None:
    """Require a bearer token when ``HERMES_API_TOKEN`` is configured.

    The API remains frictionless for localhost development when no token is set,
    but deployments can opt in by setting a secret token in the environment.
    """

    expected_token = os.getenv(API_TOKEN_ENV)
    if not expected_token:
        return

    if authorization != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
