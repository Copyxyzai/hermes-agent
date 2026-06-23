# Hermes Agent FastAPI API

This package exposes Hermes Agent through a modular FastAPI HTTP surface. It is an outer API layer around the existing `AIAgent`; it does not add core model tools.

## Run locally

```bash
hermes-api --host 127.0.0.1 --port 8000
```

OpenAPI documentation is available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`
- `http://127.0.0.1:8000/openapi.json`

## Configuration

Secrets stay in the environment:

- `HERMES_API_TOKEN`: optional bearer token for private routes.

Behavioral API settings belong in `~/.hermes/config.yaml` under the `api` key:

```yaml
api:
  environment: development
  cors_origins:
    - http://localhost:3000
  request_log_enabled: true
  rate_limit_per_minute: 0
```

## Endpoints

- `GET /health`: liveness check.
- `POST /api/v1/chat`: run one Hermes chat turn.
- `GET /api/v1/sessions`: list process-local cached chat sessions.
- `GET /api/v1/sessions/{session_id}`: inspect one cached session.
- `DELETE /api/v1/sessions/{session_id}`: delete one cached session.
- `GET /api/v1/toolsets`: list available Hermes toolsets with pagination and filtering.

## Requirement coverage

Implemented in this package:

- FastAPI app, ASGI entrypoint, OpenAPI docs, health check, versioned routes, resource routers, REST methods, Pydantic schemas, standardized success envelopes, HTTP errors, optional bearer auth, CORS allow-list support, request logging, services, repositories, models, pagination, filters, tests, and README documentation.

Handled by the existing Hermes runtime rather than duplicated here:

- Persistent conversation storage is owned by Hermes `SessionDB` when `AIAgent` runs with a `session_id`.
- External integrations are performed by the Hermes agent/tool/plugin system.
- HTTPS, process supervision, containerization, and network edge rate limiting belong to deployment infrastructure.

Not added intentionally:

- User/password tables, password hashing, JWT issuance, email delivery, file upload, and Alembic migrations. Those are not required for this chat-agent API's current resources and would add speculative surface without a concrete Hermes use case.

## Testing

```bash
uv run --with pytest --with fastapi --with uvicorn --with httpx python -m pytest tests/hermes_api/test_app.py -q
uv run --with ruff python -m ruff check hermes_api tests/hermes_api
```
