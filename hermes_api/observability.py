"""Lightweight in-process observability primitives for the Hermes API."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ApiMetrics:
    """Request counters exposed by the `/metrics` endpoint."""

    total_requests: int = 0
    total_errors: int = 0
    by_path: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, *, path: str, status_code: int) -> None:
        """Record one completed HTTP request."""

        with self._lock:
            self.total_requests += 1
            if status_code >= 500:
                self.total_errors += 1
            self.by_path[path] = self.by_path.get(path, 0) + 1

    def render_prometheus(self) -> str:
        """Render metrics in a Prometheus-compatible text format."""

        with self._lock:
            lines = [
                "# HELP hermes_api_requests_total Total HTTP requests handled by the Hermes API.",
                "# TYPE hermes_api_requests_total counter",
                f"hermes_api_requests_total {self.total_requests}",
                "# HELP hermes_api_errors_total Total HTTP 5xx responses from the Hermes API.",
                "# TYPE hermes_api_errors_total counter",
                f"hermes_api_errors_total {self.total_errors}",
                "# HELP hermes_api_requests_by_path_total HTTP requests grouped by path.",
                "# TYPE hermes_api_requests_by_path_total counter",
            ]
            for path, count in sorted(self.by_path.items()):
                escaped_path = path.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(
                    f'hermes_api_requests_by_path_total{{path="{escaped_path}"}} {count}'
                )
            return "\n".join(lines) + "\n"


metrics = ApiMetrics()
