from __future__ import annotations

import numpy as np

from app.services.knowledge_base import FAQEntry, KnowledgeBase
from app.services.retrieval.base import RetrievalHit
from app.services.retrieval.embedding import EmbeddingModel
from app.services.retrieval.similarity import cosine_similarity, l2_normalize

DOCUMENT_REPRESENTATION_VERSION = "faq-question-keywords-v2"


def build_document_text(entry: FAQEntry) -> str:
    """Index FAQ intent without diluting it with a long support answer.

    Questions and curated keywords define the supported query space. The full
    answer is retained in the source payload for exact, grounded responses.
    Dense and BM25 indexing use the same representation and version.
    """
    keywords = " ".join(entry.keywords)
    return f"{entry.question} {keywords}".strip()


class SemanticRetriever:
    """
    Çok dilli embedding + kosinüs benzerliği ile anlamsal arama.
    Doküman vektörleri başlangıçta bir kez hesaplanır; her istekte yalnızca sorgu embed edilir.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        embedder: EmbeddingModel,
        min_similarity: float = 0.42,
        *,
        tenant_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        self._kb = knowledge_base
        self._embedder = embedder
        self._min_similarity = min_similarity
        self._entries: list[FAQEntry] = [
            entry
            for entry in knowledge_base.entries
            if (tenant_id is None or entry.tenant_id == tenant_id)
            and (locale is None or entry.locale == locale)
        ]
        texts = [build_document_text(e) for e in self._entries]
        matrix = (
            embedder.encode(texts)
            if texts
            else np.empty((0, embedder.embedding_dimension), dtype=np.float32)
        )
        self._document_matrix = l2_normalize(np.asarray(matrix, dtype=np.float32))

    @property
    def min_similarity(self) -> float:
        return self._min_similarity

    def retrieve(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[RetrievalHit]:
        stripped = query.strip()
        if not stripped or top_k <= 0 or not self._entries:
            return []

        query_vec = self._embedder.encode([stripped])[0]
        similarities = cosine_similarity(query_vec, self._document_matrix)

        ranked_indices = np.argsort(similarities)[::-1]
        hits: list[RetrievalHit] = []
        for idx in ranked_indices:
            sim = float(similarities[idx])
            if sim < self._min_similarity:
                continue
            entry = self._entries[int(idx)]
            if category is not None and entry.category != category:
                continue
            hits.append(
                RetrievalHit(
                    entry=entry,
                    score=sim,
                    confidence=round(min(1.0, max(0.0, sim)), 4),
                )
            )
            if len(hits) == top_k:
                break
        return hits
