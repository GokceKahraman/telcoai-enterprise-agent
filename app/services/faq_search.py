"""Compatibility exports for the original keyword retrieval API."""

from app.services.retrieval.base import RetrievalHit
from app.services.retrieval.keyword_retriever import KeywordRetriever

SearchResult = RetrievalHit
FAQSearchService = KeywordRetriever

__all__ = ["FAQSearchService", "KeywordRetriever", "RetrievalHit", "SearchResult"]
