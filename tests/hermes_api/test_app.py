from fastapi.testclient import TestClient

from hermes_api import service
from hermes_api.app import app


class DummyAgent:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.messages = []
        DummyAgent.created.append(self)

    def chat(self, message: str) -> str:
        self.messages.append(message)
        return f"echo: {message}"


def setup_function():
    DummyAgent.created.clear()
    service.session_store.clear()


def test_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_uses_versioned_route_standard_envelope_and_safe_defaults(monkeypatch):
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    response = client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {
        "data": {"response": "echo: hello", "session_id": None},
        "message": "Chat completed successfully",
    }
    assert DummyAgent.created[0].kwargs["enabled_toolsets"] == ["web"]
    assert DummyAgent.created[0].kwargs["disabled_toolsets"] == ["terminal"]
    assert DummyAgent.created[0].kwargs["quiet_mode"] is True


def test_chat_forwards_overridden_model_provider_and_toolsets(monkeypatch):
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "hello",
            "session_id": "s1",
            "model": "test-model",
            "provider": "test-provider",
            "enabled_toolsets": ["web", "skills"],
            "disabled_toolsets": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"response": "echo: hello", "session_id": "s1"}
    assert DummyAgent.created[0].kwargs["session_id"] == "s1"
    assert DummyAgent.created[0].kwargs["model"] == "test-model"
    assert DummyAgent.created[0].kwargs["provider"] == "test-provider"
    assert DummyAgent.created[0].kwargs["enabled_toolsets"] == ["web", "skills"]
    assert DummyAgent.created[0].kwargs["disabled_toolsets"] == []


def test_chat_reuses_session_agent_and_sessions_can_be_listed_and_deleted(monkeypatch):
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    first = client.post("/api/v1/chat", json={"message": "one", "session_id": "s1"})
    second = client.post("/api/v1/chat", json={"message": "two", "session_id": "s1"})
    listed = client.get("/api/v1/sessions")
    fetched = client.get("/api/v1/sessions/s1")
    deleted = client.delete("/api/v1/sessions/s1")
    missing = client.get("/api/v1/sessions/s1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(DummyAgent.created) == 1
    assert DummyAgent.created[0].messages == ["one", "two"]
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["data"][0]["session_id"] == "s1"
    assert fetched.status_code == 200
    assert fetched.json()["data"]["session_id"] == "s1"
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_chat_requires_bearer_token_when_configured(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "secret")
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    missing = client.post("/api/v1/chat", json={"message": "hello"})
    wrong = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer wrong"},
        json={"message": "hello"},
    )
    ok = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer secret"},
        json={"message": "hello"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200


def test_private_session_routes_require_bearer_token_when_configured(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "secret")
    client = TestClient(app)

    response = client.get("/api/v1/sessions")

    assert response.status_code == 401


def test_chat_validation_rejects_empty_message():
    client = TestClient(app)

    response = client.post("/api/v1/chat", json={"message": ""})

    assert response.status_code == 422


def test_session_agent_is_rebuilt_when_runtime_options_change(monkeypatch):
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    first = client.post(
        "/api/v1/chat",
        json={"message": "one", "session_id": "s1", "model": "first-model"},
    )
    second = client.post(
        "/api/v1/chat",
        json={"message": "two", "session_id": "s1", "model": "second-model"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(DummyAgent.created) == 2
    assert DummyAgent.created[0].kwargs["model"] == "first-model"
    assert DummyAgent.created[1].kwargs["model"] == "second-model"


def test_toolsets_support_pagination_filtering_and_ordering():
    client = TestClient(app)

    response = client.get(
        "/api/v1/toolsets", params={"limit": 5, "offset": 0, "name": "web"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 5
    assert payload["offset"] == 0
    assert payload["total"] >= 1
    assert all("web" in item["name"].lower() for item in payload["data"])


def test_metrics_endpoint_exposes_request_counters():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "hermes_api_requests_total" in response.text
    assert "hermes_api_errors_total" in response.text


def test_session_delete_uses_admin_authorization_when_token_is_configured(monkeypatch):
    monkeypatch.setenv("HERMES_API_TOKEN", "secret")
    monkeypatch.setattr(service, "AIAgent", DummyAgent)
    client = TestClient(app)

    created = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer secret"},
        json={"message": "one", "session_id": "s-auth"},
    )
    missing_auth = client.delete("/api/v1/sessions/s-auth")
    deleted = client.delete(
        "/api/v1/sessions/s-auth",
        headers={"Authorization": "Bearer secret"},
    )

    assert created.status_code == 200
    assert missing_auth.status_code == 401
    assert deleted.status_code == 204


def test_rate_limiter_rejects_requests_after_limit():
    from fastapi import HTTPException

    from hermes_api.rate_limit import RateLimiter

    limiter = RateLimiter()
    limiter.check(key="client", limit_per_minute=1)

    try:
        limiter.check(key="client", limit_per_minute=1)
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("expected rate limit HTTPException")


def test_mcp_connector_returns_client_config():
    client = TestClient(app)

    response = client.get(
        "/api/v1/mcp/connector",
        params={"server_name": "hermes-dev", "verbose": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "MCP connector configuration generated"
    data = payload["data"]
    assert data["server_name"] == "hermes-dev"
    assert data["transport"] == "stdio"
    assert data["command"] == "hermes"
    assert data["args"] == ["mcp", "serve", "--verbose"]
    assert data["client_config"] == {
        "mcpServers": {
            "hermes-dev": {
                "command": "hermes",
                "args": ["mcp", "serve", "--verbose"],
            }
        }
    }


def test_toolsets_return_actual_tool_names_not_metadata_keys():
    client = TestClient(app)

    response = client.get("/api/v1/toolsets", params={"name": "web", "limit": 20})

    assert response.status_code == 200
    items = response.json()["data"]
    web_item = next(item for item in items if item["name"] == "web")
    assert "web_search" in web_item["tools"]
    assert "description" not in web_item["tools"]


def test_api_config_parses_boolean_and_invalid_rate_limit_values():
    from hermes_api.core.config import _bool_value, _non_negative_int

    assert _bool_value("false", True) is False
    assert _bool_value("yes", False) is True
    assert _non_negative_int("bad", 7) == 7
    assert _non_negative_int("-3", 0) == 0
