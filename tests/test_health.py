def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "TelcoAI"
    assert body["version"] == "1.0.0"


def test_status_reports_retrieval_and_answer_generation_modes(client):
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["retrieval"] == "keyword"
    assert response.json()["generation"] == "extractive"
