import json

import httpx
import pytest

from app.config import Settings
from app.services.generation import StructuredGenerator


def generator_for(draft, captured=None, guardrails=False):
    def handler(request):
        if captured is not None:
            captured.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(draft)}}]})

    return StructuredGenerator(
        Settings(guardrails_enabled=guardrails),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_structured_source_selection(keyword_retriever):
    hits = keyword_retriever.retrieve("Faturamı nereden ödeyebilirim?")
    captured = []
    draft = {
        "source_id": hits[0].entry.id,
        "answer": "Faturanızı DemoTel uygulamasından ödeyebilirsiniz.",
    }
    generator = generator_for(draft, captured)
    selected, answer = generator.respond("Fatura ödeme", hits)
    assert selected.entry.id == "bill-001"
    assert answer == draft["answer"]
    schema = captured[0]["response_format"]["json_schema"]
    assert schema["strict"] and schema["schema"]["additionalProperties"] is False


def test_generation_uses_masked_recent_conversation(keyword_retriever):
    hits = keyword_retriever.retrieve("Faturamı nereden ödeyebilirim?")
    captured = []
    draft = {"source_id": hits[0].entry.id, "answer": "Faturanızı uygulamadan ödeyebilirsiniz."}
    generator_for(draft, captured).respond(
        "Peki nasıl?", hits, [{"role": "user", "content": "demo@example.com kullanıyorum"}]
    )
    sent = captured[0]["messages"][1]["content"]
    assert "<EMAIL_ADDRESS>" in sent
    assert "demo@example.com" not in sent


@pytest.mark.parametrize(
    "draft",
    [
        {"source_id": "imaginary", "answer": "new fee"},
        {"source_id": "bill-001", "answer": "", "extra": "invalid"},
        {"source_id": "bill-001", "answer": "x" * 1201},
    ],
)
def test_hallucinated_source_or_answer_is_rejected(keyword_retriever, draft):
    hits = keyword_retriever.retrieve("Faturamı nereden ödeyebilirim?")
    with pytest.raises(ValueError):
        generator_for(draft).select("fatura", hits)


def test_optional_guardrails_parses_valid_structure(keyword_retriever):
    pytest.importorskip("guardrails")
    hits = keyword_retriever.retrieve("Faturamı nereden ödeyebilirim?")
    draft = {
        "source_id": hits[0].entry.id,
        "answer": "Faturanızı DemoTel uygulamasından ödeyebilirsiniz.",
    }
    selected, answer = generator_for(draft, guardrails=True).respond("fatura", hits)
    assert selected.entry.id == "bill-001"
    assert answer == draft["answer"]
