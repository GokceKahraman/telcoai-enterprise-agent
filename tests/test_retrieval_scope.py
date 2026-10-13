from dataclasses import replace
from types import SimpleNamespace

from app.config import Settings
from app.services.retrieval.factory import build_retriever
from app.services.retrieval.keyword_retriever import KeywordRetriever
from app.services.retrieval.semantic_retriever import SemanticRetriever


def test_turkish_case_normalization_does_not_split_dotted_i_into_spurious_token():
    assert KeywordRetriever._tokenize("İstanbul") == {"istanbul"}
    assert KeywordRetriever._tokenize("I\u0307stanbul") == {"istanbul"}
    assert KeywordRetriever._tokenize("İNTERNET IŞIK 100 Mbps") == {
        "internet",
        "ışık",
        "100",
        "mbps",
    }
    assert KeywordRetriever._normalize("İÇİN") == KeywordRetriever._normalize("için")


def test_keyword_factory_stays_offline_and_respects_server_scope(knowledge_base, monkeypatch):
    def unexpected_model_load(*args, **kwargs):
        raise AssertionError("Keyword retrieval must not load an embedding or reranker model")

    for name in ("get_embedding_model", "get_sparse_embedding_model", "get_reranker"):
        monkeypatch.setattr(f"app.services.retrieval.factory.{name}", unexpected_model_load)
    first = knowledge_base.entries[0]
    mixed_kb = SimpleNamespace(
        entries=[
            first,
            replace(first, id="foreign", tenant_id="another-company"),
            replace(first, id="translated", locale="en-US"),
        ]
    )
    retriever = build_retriever(Settings(retrieval_strategy="keyword"), mixed_kb)
    assert isinstance(retriever, KeywordRetriever)
    assert [hit.entry.id for hit in retriever.retrieve(first.question)] == [first.id]
    assert retriever.retrieve(first.question, category="missing-category") == []


def test_semantic_scope_with_no_entries_does_not_encode(mock_embedder):
    retriever = SemanticRetriever(
        SimpleNamespace(entries=[]), mock_embedder, tenant_id="demotel", locale="tr-TR"
    )
    assert retriever.retrieve("internet") == []


def test_semantic_category_applied_before_top_k(knowledge_base, monkeypatch, mock_embedder):
    first, second = knowledge_base.entries[:2]
    first = replace(first, category="billing")
    second = replace(second, category="technical")
    retriever = SemanticRetriever(
        SimpleNamespace(entries=[first, second]), mock_embedder, min_similarity=-1.0
    )
    hits = retriever.retrieve(first.question, top_k=1, category="technical")
    assert [hit.entry.id for hit in hits] == [second.id]
