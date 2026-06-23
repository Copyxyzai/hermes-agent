"""Config-file-driven settings for the Hermes Agent HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from hermes_cli.config import get_config_path


@dataclass(frozen=True)
class ApiSettings:
    """Runtime settings loaded from ``~/.hermes/config.yaml``."""

    environment: str = "development"
    cors_origins: tuple[str, ...] = ()
    request_log_enabled: bool = True
    rate_limit_per_minute: int = 0


def _read_config() -> dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _api_config(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("api", {})
    return value if isinstance(value, dict) else {}


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()


def get_settings() -> ApiSettings:
    """Load non-secret API settings from Hermes ``config.yaml``.

    ``HERMES_API_TOKEN`` remains the only API-specific environment variable and
    is intentionally limited to a secret credential. Behavioral settings belong
    in ``config.yaml`` under the ``api`` key.
    """

    api_config = _api_config(_read_config())
    return ApiSettings(
        environment=str(api_config.get("environment", "development")),
        cors_origins=_string_tuple(api_config.get("cors_origins")),
        request_log_enabled=bool(api_config.get("request_log_enabled", True)),
        rate_limit_per_minute=max(int(api_config.get("rate_limit_per_minute", 0)), 0),
    )
