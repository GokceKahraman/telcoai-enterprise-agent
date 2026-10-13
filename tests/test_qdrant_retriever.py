"""Exercise the real Qdrant query engine locally, without any downloaded models."""

from __future__ import annotations

import os
import re
from dataclasses import replace
from uuid import uuid4

import numpy as np
import pytest
from qdrant_client import QdrantClient, models

from app.services.knowledge_base import FAQEntry
from app.services.retrieval.qdrant_retriever import (
    QdrantRetriever,
    ensure_collection,
    ingest_entries,
    point_id,
)
from app.services.retrieval.sparse_embedding import SparseEmbedding

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect in the local Qdrant")


class DenseEncoder:
    embedding_dimension = 2

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            [[0.0, 1.0] if "lexical-only" in text else [1.0, 0.0] for text in texts],
            dtype=np.float32,
        )


class SparseEncoder:
    """Predictable lexical features; Qdrant still performs the actual IDF search."""

    def _encode(self, text: str) -> SparseEmbedding:
        words = set(re.findall(r"[a-z]+", text.lower()))
        indices = sorted({sum(word.encode("utf-8")) for word in words})
        return SparseEmbedding(indices=indices, values=[1.0] * len(indices))

    def encode_documents(self, texts: list[str]) -> list[SparseEmbedding]:
        return [self._encode(text) for text in texts]

    def encode_query(self, text: str) -> SparseEmbedding:
        return self._encode(text)


def entry(entry_id: str, question: str, **kwargs) -> FAQEntry:
    return FAQEntry(
        id=entry_id,
        category=kwargs.pop("category", "billing"),
        question=question,
        keywords=kwargs.pop("keywords", ()),
        answer="approved answer",
        **kwargs,
    )


@pytest.fixture
def qdrant():
    client = QdrantClient(":memory:")
    yield client
    client.close()


def retriever(client: QdrantClient, **kwargs) -> QdrantRetriever:
    return QdrantRetriever(
        client,
        DenseEncoder(),
        SparseEncoder(),
        collection=kwargs.pop("collection", "faq_test"),
        tenant_id=kwargs.pop("tenant_id", "demotel"),
        locale=kwargs.pop("locale", "tr-TR"),
        candidate_k=kwargs.pop("candidate_k", 20),
        min_dense_similarity=0.5,
        validate_payload_indexes=kwargs.pop("validate_payload_indexes", False),
        **kwargs,
    )


def ingest(client: QdrantClient, entries: list[FAQEntry], collection="faq_test") -> int:
    return ingest_entries(
        client, collection, entries, DenseEncoder(), SparseEncoder(), batch_size=2
    )


def test_hybrid_rrf_preserves_dense_only_and_sparse_only_candidates(qdrant):
    ingest(
        qdrant,
        [entry("semantic", "dense semantic document"), entry("lexical", "lexical-only needle")],
    )
    hits = retriever(qdrant).retrieve("needle", top_k=2)
    assert {hit.entry.id for hit in hits} == {"semantic", "lexical"}
    assert all(0 <= hit.confidence <= 1 for hit in hits)


def test_tenant_locale_filters_apply_before_candidate_limits(qdrant, monkeypatch):
    ingest(
        qdrant,
        [
            entry("safe", "needle"),
            entry("foreign", "needle", tenant_id="other-company"),
            entry("wrong-language", "needle", locale="en-US"),
        ],
    )
    original = qdrant.query_points
    calls = []

    def capture(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(qdrant, "query_points", capture)
    hits = retriever(qdrant, candidate_k=1).retrieve("needle", top_k=1)
    assert [hit.entry.id for hit in hits] == ["safe"]
    assert len(calls) == 1
    request = calls[0]
    assert {branch.using for branch in request["prefetch"]} == {"dense", "sparse"}
    for scope in [request["query_filter"], *[branch.filter for branch in request["prefetch"]]]:
        assert {condition.key: condition.match.value for condition in scope.must} == {
            "tenant_id": "demotel",
            "locale": "tr-TR",
        }


def test_category_filter_narrows_both_hybrid_branches(qdrant):
    ingest(qdrant, [entry("bill", "needle"), entry("tech", "needle", category="technical")])
    hits = retriever(qdrant).retrieve("needle", category="technical")
    assert [hit.entry.id for hit in hits] == ["tech"]
    assert retriever(qdrant).retrieve("needle", category="unknown") == []


def test_bilingual_payload_and_document_text_survive_hybrid_retrieval(qdrant):
    bilingual = entry(
        "billing-en",
        "Faturamı nereden ödeyebilirim?",
        keywords=("needle",),
        question_en="Where can I pay my bill?",
        keywords_en=("bill", "payment"),
        answer_en="Pay in the DemoTel app.",
    )
    ingest(qdrant, [bilingual])

    hit = retriever(qdrant).retrieve("needle")[0]
    assert "Where can I pay my bill?" in bilingual.question_en
    assert hit.entry.question_en == "Where can I pay my bill?"
    assert hit.entry.keywords_en == ("bill", "payment")
    assert hit.entry.answer_en == "Pay in the DemoTel app."


def test_ingestion_is_idempotent_and_preserves_other_tenants(qdrant):
    first = entry("same-id", "original question")
    other = replace(first, tenant_id="other-company")
    translated = replace(first, locale="en-US")
    assert len({point_id(first), point_id(other), point_id(translated)}) == 3
    assert ingest(qdrant, [first, other, translated]) == 3
    assert ingest(qdrant, [replace(first, answer="updated answer")]) == 1
    assert qdrant.count("faq_test", exact=True).count == 3
    points = qdrant.retrieve("faq_test", [point_id(first), point_id(other)])
    answers = {point.payload["tenant_id"]: point.payload["answer"] for point in points}
    assert answers == {"demotel": "updated answer", "other-company": "approved answer"}


def test_payload_indexes_created_before_upsert(qdrant, monkeypatch):
    events = []
    original_index = qdrant.create_payload_index
    original_upsert = qdrant.upsert

    def create_index(**kwargs):
        events.append(("index", kwargs["field_name"], kwargs["field_schema"]))
        return original_index(**kwargs)

    def upsert(**kwargs):
        events.append(("upsert",))
        return original_upsert(**kwargs)

    monkeypatch.setattr(qdrant, "create_payload_index", create_index)
    monkeypatch.setattr(qdrant, "upsert", upsert)
    ingest(qdrant, [entry("one", "needle")])
    assert events == [
        ("index", "tenant_id", models.PayloadSchemaType.KEYWORD),
        ("index", "locale", models.PayloadSchemaType.KEYWORD),
        ("index", "category", models.PayloadSchemaType.KEYWORD),
        ("upsert",),
    ]


def test_incompatible_collection_is_rejected_without_deleting_points(qdrant):
    ingest(qdrant, [entry("one", "needle")])
    with pytest.raises(ValueError, match="incompatible vector schema"):
        ensure_collection(qdrant, "faq_test", dimension=3)
    assert qdrant.count("faq_test", exact=True).count == 1


def test_duplicate_identity_rejected_before_any_database_mutation(qdrant):
    document = entry("one", "needle")
    with pytest.raises(ValueError, match="Duplicate entry IDs"):
        ingest(qdrant, [document, document])
    assert not qdrant.collection_exists("faq_test")


def test_empty_input_does_not_require_collection_or_encode(qdrant):
    search = retriever(qdrant)
    assert not search.ready()
    assert search.retrieve("   ") == []
    assert search.retrieve("needle", top_k=0) == []
    assert not qdrant.collection_exists("faq_test")


def test_retriever_readiness_requires_explicit_ingestion(qdrant):
    search = retriever(qdrant)
    assert not search.ready()
    ingest(qdrant, [entry("one", "needle")])
    assert search.ready()


def test_readiness_requires_scoped_documents_and_compatible_schema(qdrant):
    ingest(qdrant, [entry("foreign", "needle", tenant_id="other-company")])
    assert not retriever(qdrant).ready()
    ingest(qdrant, [entry("one", "needle")])
    assert retriever(qdrant).ready()
    # The dense model must match the existing collection's dimension.
    search = QdrantRetriever(
        qdrant,
        type("DifferentDimension", (), {"embedding_dimension": 3})(),
        SparseEncoder(),
        collection="faq_test",
        tenant_id="demotel",
        locale="tr-TR",
        validate_payload_indexes=False,
    )
    assert not search.ready()


def test_readiness_rejects_missing_or_wrong_payload_index_schema(qdrant, monkeypatch):
    ingest(qdrant, [entry("one", "needle")])
    search = retriever(qdrant, validate_payload_indexes=True)
    assert not search.ready()  # Local Qdrant does not implement payload indexes.
    actual = qdrant.get_collection("faq_test")
    schema = {
        field: models.PayloadIndexInfo(data_type=models.PayloadSchemaType.KEYWORD, points=1)
        for field in ("tenant_id", "locale", "category")
    }
    monkeypatch.setattr(
        qdrant, "get_collection", lambda _: actual.model_copy(update={"payload_schema": schema})
    )
    assert search.ready()
    schema["tenant_id"] = models.PayloadIndexInfo(data_type=models.PayloadSchemaType.TEXT, points=1)
    assert not search.ready()


def test_unrelated_query_returns_no_hits_when_dense_floor_excludes_candidates(qdrant):
    ingest(qdrant, [entry("one", "lexical-only billing document")])
    assert retriever(qdrant).retrieve("astronomy") == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "person@example.com"), ("category", "person@example.com"), ("question", "")],
)
def test_corrupted_qdrant_payload_fails_closed(qdrant, field, value):
    document = entry("one", "needle")
    ingest(qdrant, [document])
    qdrant.set_payload(
        collection_name="faq_test", payload={field: value}, points=[point_id(document)]
    )
    with pytest.raises(ValueError):
        retriever(qdrant).retrieve("needle")


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("TELCOAI_RUN_QDRANT_INTEGRATION") != "1",
    reason="Set TELCOAI_RUN_QDRANT_INTEGRATION=1 for a real Qdrant server",
)
def test_real_server_indexes_and_filtered_hybrid_search():
    client = QdrantClient(url=os.getenv("TELCOAI_QDRANT_URL", "http://localhost:6333"))
    collection = f"telcoai_integration_{uuid4().hex}"
    try:
        ingest(
            client, [entry("one", "needle"), entry("two", "needle", tenant_id="other")], collection
        )
        assert {"tenant_id", "locale", "category"} <= set(
            client.get_collection(collection).payload_schema
        )
        assert retriever(client, collection=collection, validate_payload_indexes=True).ready()
        assert [
            hit.entry.id for hit in retriever(client, collection=collection).retrieve("needle")
        ] == ["one"]
    finally:
        if client.collection_exists(collection):
            client.delete_collection(collection)
        client.close()
