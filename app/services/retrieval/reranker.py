"""Local cross-encoder reranking with optional, lazily imported model dependencies."""

from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from app.services.retrieval.base import RetrievalHit, Retriever
from app.services.retrieval.semantic_retriever import build_document_text


class Reranker(Protocol):
    def score(self, query: str, documents: list[str]) -> list[float]: ...


class BGEReranker:
    """Multilingual BGE CrossEncoder. First construction may download model weights.

    A one-label CrossEncoder uses sigmoid scores by default. These are model
    relevance scores and require domain evaluation before probabilistic use.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name, num_labels=1, max_length=512)

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        pairs = [(query, document) for document in documents]
        scores = self._model.predict(pairs, show_progress_bar=False, convert_to_numpy=True)
        return np.asarray(scores, dtype=np.float64).reshape(-1).tolist()


class RerankingRetriever:
    """Fetch a larger candidate set, then return cross-encoder relevance order."""

    def __init__(self, retriever: Retriever, reranker: Reranker, candidate_k: int = 20) -> None:
        if candidate_k < 1:
            raise ValueError("candidate_k must be positive")
        self._retriever = retriever
        self._reranker = reranker
        self._candidate_k = candidate_k

    def ready(self) -> bool:
        check = getattr(self._retriever, "ready", None)
        return bool(check()) if check is not None else True

    def close(self) -> None:
        close = getattr(self._retriever, "close", None)
        if close is not None:
            close()

    def retrieve(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[RetrievalHit]:
        if not query.strip() or top_k <= 0:
            return []
        candidates = self._retriever.retrieve(
            query, top_k=max(top_k, self._candidate_k), category=category
        )
        if not candidates:
            return []
        scores = self._reranker.score(query, [build_document_text(hit.entry) for hit in candidates])
        if len(scores) != len(candidates) or any(
            not math.isfinite(score) or not 0 <= score <= 1 for score in scores
        ):
            raise ValueError("Reranker must return one finite sigmoid score per candidate")
        ranked = [
            RetrievalHit(entry=hit.entry, score=score, confidence=round(score, 4))
            for hit, score in zip(candidates, scores, strict=True)
        ]
        return sorted(ranked, key=lambda hit: hit.score, reverse=True)[:top_k]
