"""Tests for DemoTel billing questions."""

import pytest

from app.services.chat_service import ChatService

BILLING_PARAPHRASES = [
    "Aylık ödeme tutarım neden yükseldi?",
    "Bu ay faturam neden daha fazla geldi?",
    "Ödediğim ücret artmış, sebebi nedir?",
    "Aylık internet ücretim yükselmiş.",
    "Faturam her zamankinden yüksek.",
]


@pytest.mark.parametrize("query", BILLING_PARAPHRASES)
def test_billing_increase_retrieves_correct_entry(keyword_retriever, query):
    hits = keyword_retriever.retrieve(query, top_k=3)

    assert hits, query
    assert hits[0].entry.id == "bill-004"


@pytest.mark.parametrize("query", BILLING_PARAPHRASES)
def test_billing_chat_response_is_grounded(keyword_retriever, query):
    response = ChatService(keyword_retriever).reply(query)

    assert response.fallback is False
    assert response.source is not None
    assert response.source.entry_id == "bill-004"

    assert "kesin" in response.answer.lower()
    assert "hesabınıza erişemediğinden" in response.answer


def test_billing_increase_api_response(client):
    response = client.post("/api/v1/chat", json={"message": "Aylık ödeme tutarım neden yükseldi?"})

    assert response.status_code == 200

    payload = response.json()

    assert payload["fallback"] is False
    assert payload["source"]["entry_id"] == "bill-004"
    assert payload["source"]["category"] == "fatura"


def test_unrelated_question_still_falls_back(keyword_retriever):
    response = ChatService(keyword_retriever).reply("Python decorator nasıl yazılır?")

    assert response.fallback is True
    assert response.source is None
