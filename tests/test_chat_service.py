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


def test_english_greeting_and_faq_are_fully_localized(keyword_retriever):
    service = ChatService(keyword_retriever)
    greeting = service.reply("Hello, how are you?", locale="en-US")
    bill = service.reply("Where can I pay my bill?", locale="en-US")

    assert greeting.intent == "greeting"
    assert greeting.answer.startswith("I’m doing well")
    assert bill.source is not None
    assert bill.source.entry_id == "bill-001"
    assert bill.source.matched_question == "Where can I pay my bill?"
    assert "The fictional DemoTel bill" in bill.answer
    assert "Faturanızı" not in bill.answer


def test_english_account_actions_are_safely_handed_off(keyword_retriever):
    response = ChatService(keyword_retriever).reply("Please cancel my subscription", locale="en-US")
    assert response.handoff is True
    assert "authenticated customer support representative" in response.answer


def test_chat_semantic_paraphrase_with_mock(knowledge_base, mock_embedder):
    retriever = SemanticRetriever(knowledge_base, mock_embedder, min_similarity=0.0)
    service = ChatService(retriever)
    response = service.reply("Bağlantım devamlı kesiliyor")
    assert response.fallback is False
    assert response.source is not None
    assert response.answer
