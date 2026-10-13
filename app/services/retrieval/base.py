from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.knowledge_base import FAQEntry


@dataclass(frozen=True)
class RetrievalHit:
    """Tek bir SSS kaydı için arama sonucu."""

    entry: FAQEntry
    score: float
    confidence: float


class Retriever(Protocol):
    """Sorgu → sıralı aday listesi (en ilgili önce)."""

    def retrieve(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[RetrievalHit]: ...
