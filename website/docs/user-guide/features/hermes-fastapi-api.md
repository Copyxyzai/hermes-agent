---
sidebar_position: 15
title: "FastAPI HTTP API"
description: "Run Hermes Agent chat turns and inspect API resources over a versioned FastAPI surface"
---

# FastAPI HTTP API

The `hermes-api` server exposes Hermes Agent through a small, versioned FastAPI
HTTP surface. It is an outer API layer around the existing `AIAgent`; it does
not add model tools, change prompt assembly, or duplicate the agent runtime.

Use this API when you want direct HTTP access to Hermes chat turns, cached API
sessions, toolset discovery, metrics, and MCP connector metadata. If you need an
OpenAI-compatible `/v1/chat/completions` server for existing chat frontends, use
the [API Server](/user-guide/features/api-server) instead.

Repository Portuguese guide: `docs/hermes-api-pt-br.md`.

## Quick start

Start the FastAPI server locally:

```bash
hermes-api --host 127.0.0.1 --port 8000
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Other generated docs and schema endpoints:

```text
GET /redoc
GET /openapi.json
```

The default bind host is `127.0.0.1`. Bind to `0.0.0.0` only behind your normal
production controls, such as a reverse proxy, platform ingress, or private
network boundary.

## Configuration

Secrets stay in the environment:

```bash
export HERMES_API_TOKEN="replace-with-a-long-random-token"
```

When `HERMES_API_TOKEN` is configured, private endpoints require:

```http
Authorization: Bearer replace-with-a-long-random-token
```

Non-secret behavior belongs in `~/.hermes/config.yaml`:

```yaml
api:
  environment: development
  cors_origins:
    - http://localhost:3000
  request_log_enabled: true
  rate_limit_per_minute: 60
```

| Key | Default | Description |
| --- | --- | --- |
| `api.environment` | `development` | Deployment label for operators and future policy hooks. |
| `api.cors_origins` | `[]` | Explicit browser origins allowed by CORS. Empty means no CORS middleware. |
| `api.request_log_enabled` | `true` | Enables sanitized request-completion logs. |
| `api.rate_limit_per_minute` | `0` | Process-local request limit per client host. `0` disables it. |

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Liveness check. |
| `GET` | `/metrics` | No | Process-local Prometheus-style counters. |
| `POST` | `/api/v1/chat` | Optional bearer token | Run one Hermes chat turn. |
| `GET` | `/api/v1/sessions` | Optional bearer token | List cached API sessions. |
| `GET` | `/api/v1/sessions/{session_id}` | Optional bearer token | Inspect one cached API session. |
| `DELETE` | `/api/v1/sessions/{session_id}` | Admin | Delete one cached API session. |
| `GET` | `/api/v1/mcp/connector` | Optional bearer token | Generate MCP client connector config. |
| `GET` | `/api/v1/toolsets` | No | List available Hermes toolsets. |

“Optional bearer token” means the route is open in local-development mode when
`HERMES_API_TOKEN` is not set, and private when the token is configured.

## Chat endpoint

`POST /api/v1/chat` runs one Hermes chat turn and returns the final response.

Request:

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

Response:

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

## Sessions

List process-local cached API sessions:

```bash
curl 'http://127.0.0.1:8000/api/v1/sessions?limit=50&offset=0'
```

Fetch one session:

```bash
curl http://127.0.0.1:8000/api/v1/sessions/demo-session
```

Delete one session:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/sessions/demo-session \
  -H 'Authorization: Bearer replace-with-a-long-random-token'
```

The API session cache is process-local. Entries are cleared when the FastAPI
process restarts. Hermes conversation persistence remains owned by the existing
Hermes runtime when `AIAgent` runs with a `session_id`.

## Toolsets

List toolsets:

```bash
curl 'http://127.0.0.1:8000/api/v1/toolsets?limit=10&name=web'
```

Example response:

```json
{
  "limit": 10,
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

## MCP connector

The MCP connector endpoint returns a config fragment for MCP clients that should
launch Hermes' existing stdio MCP server with `hermes mcp serve`. The FastAPI
process does not host MCP itself.

```bash
curl 'http://127.0.0.1:8000/api/v1/mcp/connector?server_name=hermes&verbose=false'
```

Response:

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

## Metrics

Read process-local metrics:

```bash
curl http://127.0.0.1:8000/metrics
```

Example:

```text
# HELP hermes_api_requests_total Total HTTP requests handled by the Hermes API.
# TYPE hermes_api_requests_total counter
hermes_api_requests_total 12
# HELP hermes_api_errors_total Total HTTP 5xx responses from the Hermes API.
# TYPE hermes_api_errors_total counter
hermes_api_errors_total 0
```

## Operational notes

- The default API tool policy is conservative: enable `web` and disable
  `terminal` unless explicitly overridden per request.
- HTTPS termination is expected at the deployment edge, not inside this
  lightweight FastAPI process.
- Distributed rate limiting should be handled by deployment infrastructure if
  multiple API processes are running.
- For full source-level reference and testing commands, see
  `docs/hermes-api.md` in the repository.
