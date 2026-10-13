from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_session_history_and_delete(client):
    response = client.post(
        "/api/v1/chat", json={"message": "Faturam neden arttı? test@example.com"}
    )
    session = response.json()["session_id"]
    history = client.get(f"/api/v1/sessions/{session}").json()["messages"]
    assert len(history) == 2
    assert "test@example.com" not in str(history)
    assert client.delete(f"/api/v1/sessions/{session}").status_code == 204
    assert client.get(f"/api/v1/sessions/{session}").json()["messages"] == []


def test_api_auth_applies_to_chat_history_and_status():
    app = create_app(Settings(api_key="demo-secret"))
    with TestClient(app) as client:
        for route in ("/api/v1/status", f"/api/v1/sessions/{uuid4()}"):
            assert client.get(route).status_code == 401
            assert (
                client.get(route, headers={"Authorization": "Bearer demo-secret"}).status_code
                == 200
            )
        assert client.post("/api/v1/chat", json={"message": "fatura"}).status_code == 401
        assert client.get("/health").status_code == 200


def test_validation_errors_do_not_echo_sensitive_inputs(client):
    secret = "test@example.com"
    response = client.post("/api/v1/chat", json={"message": secret, "session_id": secret})
    assert response.status_code == 422
    assert secret not in response.text
    response = client.post(
        "/api/v1/chat", json={"message": "fatura", "tenant_id": "another-tenant"}
    )
    assert response.status_code == 422


def test_readiness_and_safe_headers(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {"storage": True, "retrieval": True}
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-request-id"]


def test_dependency_error_returns_generic_503(client, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("secret connection credential")

    monkeypatch.setattr(client.app.state.runtime.service, "reply", broken)
    response = client.post("/api/v1/chat", json={"message": "fatura"})
    assert response.status_code == 503
    assert "secret connection credential" not in response.text
