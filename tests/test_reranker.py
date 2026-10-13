from __future__ import annotations

import pytest

from app.services.retrieval.base import RetrievalHit
from app.services.retrieval.reranker import RerankingRetriever


class CandidateRetriever:
    def __init__(self, entries):
        self.entries = entries
        self.request = None

    def retrieve(self, query, top_k=3, category=None):
        self.request = (query, top_k, category)
        return [RetrievalHit(entry=entry, score=1.0, confidence=0.5) for entry in self.entries]


class FixedReranker:
    def __init__(self, scores):
        self.scores = scores

    def score(self, query, documents):
        return self.scores


def test_reranking_changes_order_and_preserves_category_scope(knowledge_base):
    first, second = knowledge_base.entries[:2]
    candidates = CandidateRetriever([first, second])
    retriever = RerankingRetriever(candidates, FixedReranker([0.1, 0.9]), candidate_k=20)
    hits = retriever.retrieve("fatura", top_k=1, category="billing")
    assert candidates.request == ("fatura", 20, "billing")
    assert hits[0].entry == second
    assert hits[0].confidence == 0.9


@pytest.mark.parametrize("scores", [[float("nan"), 0.4], [0.5], [1.2, 0.4]])
def test_invalid_reranker_scores_fail_closed(knowledge_base, scores):
    candidates = CandidateRetriever(knowledge_base.entries[:2])
    retriever = RerankingRetriever(candidates, FixedReranker(scores))
    with pytest.raises(ValueError, match="finite sigmoid score"):
        retriever.retrieve("fatura")


def test_empty_query_does_not_call_candidate_retriever(knowledge_base):
    candidates = CandidateRetriever(knowledge_base.entries[:2])
    retriever = RerankingRetriever(candidates, FixedReranker([]))
    assert retriever.retrieve("   ") == []
    assert candidates.request is None
