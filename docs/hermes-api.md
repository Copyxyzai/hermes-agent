# Hermes Agent FastAPI HTTP API

This document describes the standalone FastAPI surface exposed by the
`hermes_api` package. The API is an outer HTTP layer around the existing Hermes
`AIAgent`; it does not add model tools, change prompt assembly, or duplicate the
agent runtime.

See also the Portuguese API guide: [`docs/hermes-api-pt-br.md`](hermes-api-pt-br.md).

## Base URLs

Local development:

```text
http://127.0.0.1:8000
```

Versioned API prefix:

```text
/api/v1
```

Built-in OpenAPI documentation:

```text
GET /docs
GET /redoc
GET /openapi.json
```

## Starting the server

Install the project with the web dependencies available, then run:

```bash
hermes-api --host 127.0.0.1 --port 8000
```

Development reload mode:

```bash
hermes-api --host 127.0.0.1 --port 8000 --reload
```

The default host is `127.0.0.1` so the API is not exposed on the network by
accident. Bind to `0.0.0.0` only behind your normal production controls.

## Configuration

Secrets remain in the environment. Non-secret behavior belongs in
`~/.hermes/config.yaml` under the `api` key.

### Secret environment variable

```bash
export HERMES_API_TOKEN="replace-with-a-long-random-token"
```

When `HERMES_API_TOKEN` is set, private endpoints require:

```http
Authorization: Bearer replace-with-a-long-random-token
```

When it is not set, the API keeps a frictionless local-development mode.

### `config.yaml` settings

```yaml
api:
  environment: development
  cors_origins:
    - http://localhost:3000
  request_log_enabled: true
  rate_limit_per_minute: 60
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `api.environment` | string | `development` | Deployment label for operators and future policy hooks. |
| `api.cors_origins` | list[string] | `[]` | Explicit browser origins allowed by CORS. Empty means no CORS middleware. |
| `api.request_log_enabled` | bool | `true` | Enables sanitized request-completion logs. |
| `api.rate_limit_per_minute` | int | `0` | Process-local request limit per client host. `0` disables it. |

## Authentication and authorization

The first API surface uses one deployment-owned bearer token:

- If `HERMES_API_TOKEN` is configured, requests to private routes without the
  matching bearer token receive `401 Unauthorized`.
- The valid token maps to an admin principal.
- Destructive operations, currently deleting cached API sessions, require admin
  authorization.

This is intentionally smaller than a user/password/JWT system. Add multi-user
identity only when a concrete Hermes API resource needs it.

## Response format

Successful chat and single-resource responses use a predictable envelope:

```json
{
  "data": {},
  "message": "Operation completed successfully"
}
```

Validation errors and explicit HTTP errors use FastAPI's standard error shape:

```json
{
  "detail": "Error message"
}
```

## Endpoints

### `GET /health`

Liveness check.

Authentication: none.

Response `200 OK`:

```json
{
  "status": "ok"
}
```

### `GET /metrics`

Returns process-local Prometheus-style counters.

Authentication: none.

Response `200 OK` content type: `text/plain`.

Example response:

```text
# HELP hermes_api_requests_total Total HTTP requests handled by the Hermes API.
# TYPE hermes_api_requests_total counter
hermes_api_requests_total 12
# HELP hermes_api_errors_total Total HTTP 5xx responses from the Hermes API.
# TYPE hermes_api_errors_total counter
hermes_api_errors_total 0
```

### `POST /api/v1/chat`

Runs one Hermes chat turn and returns the final response.

Authentication: bearer token required when `HERMES_API_TOKEN` is set.

Request body:

```json
{
  "message": "Explain Hermes Agent in one paragraph.",
  "session_id": "demo-session",
  "model": "gpt-4.1",
  "provider": "openai",
  "enabled_toolsets": ["web"],
  "disabled_toolsets": ["terminal"]
}
```

Fields:

| Field | Required | Description |
| --- | --- | --- |
| `message` | yes | User message. Must be at least one character. |
| `session_id` | no | Reuses a process-local cached `AIAgent` for that session. |
| `model` | no | Optional model override passed to `AIAgent`. |
| `provider` | no | Optional provider override passed to `AIAgent`. |
| `enabled_toolsets` | no | Optional toolset allow-list. Defaults to `['web']`. |
| `disabled_toolsets` | no | Optional toolset block-list. Defaults to `['terminal']`. |

Response `200 OK`:

```json
{
  "data": {
    "response": "Hermes Agent is ...",
    "session_id": "demo-session"
  },
  "message": "Chat completed successfully"
}
```

Common errors:

| Status | Meaning |
| --- | --- |
| `401` | Missing or invalid bearer token when auth is enabled. |
| `422` | Invalid request body, such as an empty `message`. |
| `429` | Process-local rate limit exceeded. |
| `500` | Hermes chat turn failed unexpectedly. |

### `GET /api/v1/sessions`

Lists process-local cached API sessions.

Authentication: bearer token required when `HERMES_API_TOKEN` is set.

Query parameters:

| Parameter | Default | Constraints | Description |
| --- | --- | --- | --- |
| `limit` | `50` | `1 <= limit <= 200` | Maximum number of sessions to return. |
| `offset` | `0` | `offset >= 0` | Number of sessions to skip. |

Response `200 OK`:

```json
{
  "limit": 50,
  "offset": 0,
  "total": 1,
  "data": [
    {
      "session_id": "demo-session",
      "model": "gpt-4.1",
      "provider": "openai",
      "enabled_toolsets": ["web"],
      "disabled_toolsets": ["terminal"]
    }
  ]
}
```

### `GET /api/v1/sessions/{session_id}`

Fetches one process-local cached API session.

Authentication: bearer token required when `HERMES_API_TOKEN` is set.

Response `200 OK`:

```json
{
  "data": {
    "session_id": "demo-session",
    "model": "gpt-4.1",
    "provider": "openai",
    "enabled_toolsets": ["web"],
    "disabled_toolsets": ["terminal"]
  },
  "message": "Session found"
}
```

Error `404 Not Found`:

```json
{
  "detail": "Session not found"
}
```

### `DELETE /api/v1/sessions/{session_id}`

Deletes one process-local cached API session.

Authentication: bearer token required when `HERMES_API_TOKEN` is set.
Authorization: admin principal required.

Response `204 No Content`: empty body.

Error `404 Not Found`:

```json
{
  "detail": "Session not found"
}
```


### `GET /api/v1/mcp/connector`

Returns an MCP client configuration fragment that launches the existing Hermes
stdio MCP server with `hermes mcp serve`. The HTTP API does not host MCP inside
the FastAPI process; it only returns connector metadata for MCP clients.

Authentication: bearer token required when `HERMES_API_TOKEN` is set.

Query parameters:

| Parameter | Default | Constraints | Description |
| --- | --- | --- | --- |
| `server_name` | `hermes` | min length 1 | Key to use inside the returned `mcpServers` object. |
| `command` | `hermes` | min length 1 | Command an MCP client should execute. |
| `verbose` | `false` | bool | Adds `--verbose` to the MCP server args. |

Response `200 OK`:

```json
{
  "data": {
    "server_name": "hermes",
    "transport": "stdio",
    "command": "hermes",
    "args": ["mcp", "serve"],
    "client_config": {
      "mcpServers": {
        "hermes": {
          "command": "hermes",
          "args": ["mcp", "serve"]
        }
      }
    },
    "usage": "hermes mcp serve"
  },
  "message": "MCP connector configuration generated"
}
```

### `GET /api/v1/toolsets`

Lists available Hermes toolsets.

Authentication: none.

Query parameters:

| Parameter | Default | Constraints | Description |
| --- | --- | --- | --- |
| `limit` | `50` | `1 <= limit <= 200` | Maximum number of toolsets to return. |
| `offset` | `0` | `offset >= 0` | Number of toolsets to skip. |
| `name` | omitted | string | Case-insensitive substring filter for toolset names. |
| `order_by` | `name` | currently `name` only | Stable ordering field. |

Response `200 OK`:

```json
{
  "limit": 50,
  "offset": 0,
  "total": 1,
  "data": [
    {
      "name": "web",
      "tools": ["web_search", "web_extract"]
    }
  ]
}
```

## cURL examples

Health:

```bash
curl http://127.0.0.1:8000/health
```

Chat without auth in local-development mode:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello from the API","session_id":"demo"}'
```

Chat with bearer auth:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Authorization: Bearer replace-with-a-long-random-token' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello from the API","session_id":"demo"}'
```

Get MCP connector config:

```bash
curl 'http://127.0.0.1:8000/api/v1/mcp/connector?server_name=hermes'
```

List toolsets:

```bash
curl 'http://127.0.0.1:8000/api/v1/toolsets?limit=10&name=web'
```

Read metrics:

```bash
curl http://127.0.0.1:8000/metrics
```

## Operational notes

- The API is process-local. Session cache entries live in the current server
  process and are cleared when the process restarts.
- Hermes conversation persistence remains owned by the existing Hermes runtime
  when `AIAgent` is run with a `session_id`.
- The default API tool policy is conservative: enable `web` and disable
  `terminal` unless explicitly overridden per request.
- HTTPS termination is expected at the deployment edge, such as a reverse proxy,
  load balancer, or platform ingress.
- Distributed rate limiting should be handled by deployment infrastructure if
  multiple API processes are running.

## Testing

Run the focused API test suite:

```bash
uv run --with pytest --with fastapi --with uvicorn --with httpx \
  python -m pytest tests/hermes_api/test_app.py -q
```

Run linting:

```bash
uv run --with ruff python -m ruff check hermes_api tests/hermes_api
```

Smoke test the ASGI app without binding a network port:

```bash
uv run --with fastapi --with httpx python - <<'PY'
from fastapi.testclient import TestClient
from hermes_api.app import app

client = TestClient(app)
for path in ["/health", "/metrics", "/openapi.json", "/api/v1/toolsets?limit=1"]:
    response = client.get(path)
    print(path, response.status_code, response.headers.get("content-type"))
PY
```
