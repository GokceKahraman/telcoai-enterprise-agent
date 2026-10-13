def test_chat_success_with_source(client):
    response = client.post(
        "/api/v1/chat",
        json={"message": "Faturamı nereden ödeyebilirim?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "DemoTel" in data["answer"]
    assert data["fallback"] is False
    assert data["source"]["entry_id"] == "bill-001"
    assert data["source"]["category"] == "fatura"


def test_chat_accepts_english_locale(client):
    response = client.post(
        "/api/v1/chat",
        json={"message": "Where can I pay my bill?", "locale": "en-US"},
    )
    assert response.status_code == 200
    assert response.json()["source"]["entry_id"] == "bill-001"
    assert response.json()["answer"].startswith("The fictional DemoTel bill")


def test_chat_rejects_unsupported_locale(client):
    response = client.post("/api/v1/chat", json={"message": "Hello", "locale": "fr-FR"})
    assert response.status_code == 422


def test_chat_fallback(client):
    response = client.post(
        "/api/v1/chat",
        json={"message": "asdf qwerty zxc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["source"] is None


def test_chat_rejects_empty_message(client):
    response = client.post("/api/v1/chat", json={"message": "   "})
    assert response.status_code == 422


def test_chat_rejects_missing_message(client):
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == 422
