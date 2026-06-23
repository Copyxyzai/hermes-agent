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
