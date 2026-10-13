from app.services.chat_service import ChatService
from app.services.retrieval.semantic_retriever import SemanticRetriever


def test_chat_source_metadata(keyword_retriever):
    service = ChatService(keyword_retriever)
    response = service.reply("Faturamı nereden ödeyebilirim?")
    assert response.fallback is False
    assert response.source is not None
    assert response.source.entry_id == "bill-001"
    assert response.source.category == "fatura"


def test_chat_unknown_question_fallback(keyword_retriever):
    service = ChatService(keyword_retriever)
    response = service.reply("asdf qwerty zxc")
    assert response.fallback is True
    assert response.source is None


def test_chat_greeting_is_conversational_and_skips_retrieval(keyword_retriever):
    class NoSearch:
        def retrieve(self, *args, **kwargs):
            raise AssertionError("greetings should bypass RAG retrieval")

    response = ChatService(NoSearch()).reply("Selam, nasılsın?")
    assert response.intent == "greeting"
    assert response.fallback is False
    assert response.source is None
    assert "sana nasıl yardımcı olabilirim" in response.answer


def test_chat_thanks_gets_a_natural_reply(keyword_retriever):
    response = ChatService(keyword_retriever).reply("Teşekkürler")
    assert response.intent == "greeting"
    assert response.answer.startswith("Rica ederim")


def test_chat_semantic_paraphrase_with_mock(knowledge_base, mock_embedder):
    retriever = SemanticRetriever(knowledge_base, mock_embedder, min_similarity=0.0)
    service = ChatService(retriever)
    response = service.reply("Bağlantım devamlı kesiliyor")
    assert response.fallback is False
    assert response.source is not None
    assert response.answer
