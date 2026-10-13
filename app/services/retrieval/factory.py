from __future__ import annotations

from functools import lru_cache

from app.config import Settings
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.base import Retriever
from app.services.retrieval.embedding import EmbeddingModel, SentenceTransformerEmbedding
from app.services.retrieval.keyword_retriever import KeywordRetriever
from app.services.retrieval.reranker import BGEReranker, Reranker, RerankingRetriever
from app.services.retrieval.semantic_retriever import SemanticRetriever
from app.services.retrieval.sparse_embedding import FastEmbedBM25, SparseEmbeddingModel


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str) -> EmbeddingModel:
    return SentenceTransformerEmbedding(model_name)


@lru_cache(maxsize=2)
def get_sparse_embedding_model(locale: str) -> SparseEmbeddingModel:
    return FastEmbedBM25(locale)


@lru_cache(maxsize=1)
def get_reranker(model_name: str) -> Reranker:
    return BGEReranker(model_name)


def build_retriever(settings: Settings, knowledge_base: KnowledgeBase) -> Retriever:
    strategy = settings.retrieval_strategy.lower()
    if strategy == "keyword":
        retriever: Retriever = KeywordRetriever(
            knowledge_base,
            min_match_score=settings.min_match_score,
            tenant_id=settings.tenant_id,
            locale=settings.locale,
        )
    elif strategy == "semantic":
        embedder = get_embedding_model(settings.embedding_model_name)
        retriever = SemanticRetriever(
            knowledge_base,
            embedder,
            min_similarity=settings.semantic_min_similarity,
            tenant_id=settings.tenant_id,
            locale=settings.locale,
        )
    elif strategy in {"qdrant_hybrid", "qdrant"}:
        from qdrant_client import QdrantClient

        from app.services.retrieval.qdrant_retriever import QdrantRetriever

        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=(
                settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
            ),
            timeout=10,
        )
        retriever = QdrantRetriever(
            client,
            get_embedding_model(settings.embedding_model_name),
            get_sparse_embedding_model(settings.locale),
            collection=settings.qdrant_collection,
            tenant_id=settings.tenant_id,
            locale=settings.locale,
            candidate_k=settings.retrieval_candidate_k,
            min_dense_similarity=settings.semantic_min_similarity,
        )
    else:
        raise ValueError(f"Bilinmeyen retrieval stratejisi: {settings.retrieval_strategy}")
    if settings.reranker_enabled:
        return RerankingRetriever(
            retriever,
            get_reranker(settings.reranker_model),
            candidate_k=settings.retrieval_candidate_k,
        )
    return retriever
