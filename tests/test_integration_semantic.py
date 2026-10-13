import os

import pytest

from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.factory import get_embedding_model
from app.services.retrieval.semantic_retriever import SemanticRetriever


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TELCOAI_RUN_INTEGRATION") != "1",
    reason="Gerçek model indirmesi için TELCOAI_RUN_INTEGRATION=1 gerekir.",
)
def test_real_model_paraphrase_connection_issue(knowledge_base_path):
    kb = KnowledgeBase(knowledge_base_path)
    embedder = get_embedding_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    retriever = SemanticRetriever(kb, embedder, min_similarity=0.35)
    hits = retriever.retrieve("Bağlantım devamlı kesiliyor.", top_k=1)
    assert hits
    assert hits[0].entry.id == "tech-001"
