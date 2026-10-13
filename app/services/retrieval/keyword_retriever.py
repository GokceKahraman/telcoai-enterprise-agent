from __future__ import annotations

import re
import unicodedata

from app.services.knowledge_base import FAQEntry, KnowledgeBase
from app.services.retrieval.base import RetrievalHit

_TOKEN_PATTERN = re.compile(r"[a-z0-9çğıöşü]+", re.IGNORECASE)

_STOPWORDS = frozenset(
    {"nasıl", "ne", "nedir", "hangi", "mi", "mı", "mu", "mü", "bu", "bir", "ve", "için"}
)


class KeywordRetriever:
    """
    Anahtar kelime / token eşleştirmesi (v0.1 davranışı).
    Paraphrase farklı ifadelerde zayıf kalır; baseline ve fallback stratejisi olarak korunur.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        min_match_score: float = 1.0,
        *,
        tenant_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        self._kb = knowledge_base
        self._min_match_score = min_match_score
        self._tenant_id = tenant_id
        self._locale = locale

    def retrieve(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[RetrievalHit]:
        if top_k <= 0:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []

        hits: list[RetrievalHit] = []
        for entry in self._kb.entries:
            if self._tenant_id is not None and entry.tenant_id != self._tenant_id:
                continue
            if self._locale is not None and entry.locale != self._locale:
                continue
            if category is not None and entry.category != category:
                continue
            score = self._score_entry(tokens, query, entry)
            if score < self._min_match_score:
                continue
            confidence = min(1.0, score / 6.0)
            hits.append(RetrievalHit(entry=entry, score=score, confidence=confidence))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def _score_entry(self, user_tokens: set[str], raw_message: str, entry: FAQEntry) -> float:
        score = 0.0
        normalized_message = self._normalize(raw_message)

        question_norm = self._normalize(entry.question)
        if question_norm and question_norm in normalized_message:
            score += 4.0

        entry_tokens = self._tokenize(entry.question) | self._tokenize(" ".join(entry.keywords))
        overlap = user_tokens & entry_tokens
        score += len(overlap) * 1.5

        for keyword in entry.keywords:
            kw = self._normalize(keyword)
            if len(kw) >= 3 and kw in normalized_message:
                score += 1.0

        return score

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        return normalized.replace("İ", "i").replace("I", "ı").casefold().replace("\u0307", "")

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        return set(_TOKEN_PATTERN.findall(cls._normalize(text))) - _STOPWORDS
