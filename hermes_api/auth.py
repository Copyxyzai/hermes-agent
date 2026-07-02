"""Authentication and authorization helpers for the Hermes Agent HTTP API."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

API_TOKEN_ENV = "HERMES_API_TOKEN"


@dataclass(frozen=True)
class ApiPrincipal:
    """Authenticated API principal.

    The first API surface supports one deployment-owned bearer token. When the
    token is configured, that caller is authorized as an administrator. When no
    token is configured, localhost/development mode is treated as a local admin
    to preserve the existing frictionless workflow.
    """

    subject: str
    role: str


def require_bearer_token(
    authorization: str | None = Header(default=None),
) -> ApiPrincipal:
    """Require a bearer token when ``HERMES_API_TOKEN`` is configured."""

    expected_token = os.getenv(API_TOKEN_ENV)
    if not expected_token:
        return ApiPrincipal(subject="local", role="admin")

    if authorization != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ApiPrincipal(subject="api-token", role="admin")


def require_admin(
    principal: ApiPrincipal = Depends(require_bearer_token),
) -> ApiPrincipal:
    """Require an authenticated administrator principal."""

    if principal.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return principal
