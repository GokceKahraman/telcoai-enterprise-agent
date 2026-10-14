import pytest

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


@pytest.mark.parametrize(
    ("query", "locale"),
    [
        ("Mahallemde şu anda internet kesintisi var mı?", "tr-TR"),
        ("Hesabımın kalan internetini kontrol et", "tr-TR"),
        ("Hattıma eSIM tanımla", "tr-TR"),
        ("Bugün kesin kurulum randevusu ver", "tr-TR"),
        ("Show my remaining data balance", "en-US"),
        ("Is there a live outage right now?", "en-US"),
    ],
)
def test_live_or_account_specific_request_bypasses_faq(query, locale):
    class NoSearch:
        def retrieve(self, *args, **kwargs):
            raise AssertionError("Live/account requests must not use FAQ retrieval")

    response = ChatService(NoSearch()).reply(query, locale=locale)
    assert response.handoff is True
    assert response.source is None
    assert response.fallback is True


def test_general_troubleshooting_question_remains_on_faq_path(keyword_retriever):
    response = ChatService(keyword_retriever).reply("Modemde neyi kontrol et?")
    assert response.handoff is False


@pytest.mark.parametrize(
    ("query", "entry_id"),
    [
        ("Evde 6 kişi aynı anda dizi ve toplantı yaparsa neye bakmalıyım?", "pkg-003"),
        ("Taahhüdüm devam ederken alt pakete geçsem ücret çıkar mı?", "price-004"),
        (
            "Karttan çekilmiş ama müşteri ekranında borç hâlâ kapanmamış görünüyor.",
            "bill-006",
        ),
        (
            "Almanya seyahatinde data roaming kullanmadan önce neyi teyit etmeliyim?",
            "tech-011",
        ),
        (
            "Kampanyalı sözleşmem hangi gün sona eriyor nereden görürüm?",
            "taahhut-001",
        ),
        ("Buraya SMS kodumu göndersem hesabımı bulabilir misin?", "general-003"),
        ("Geçen haftaki konuşmamı nereden temizleyebilirim?", "general-004"),
        (
            "Yanıtın hangi destek belgesine dayandığını nasıl görürüm?",
            "general-005",
        ),
    ],
)
def test_supported_faq_paraphrases_are_not_routed_away(keyword_retriever, query, entry_id):
    response = ChatService(keyword_retriever).reply(query)
    assert response.handoff is False
    assert response.fallback is False
    assert response.source is not None
    assert response.source.entry_id == entry_id


def test_chat_semantic_paraphrase_with_mock(knowledge_base, mock_embedder):
    retriever = SemanticRetriever(knowledge_base, mock_embedder, min_similarity=0.0)
    service = ChatService(retriever)
    response = service.reply("Bağlantım devamlı kesiliyor")
    assert response.fallback is False
    assert response.source is not None
    assert response.answer
