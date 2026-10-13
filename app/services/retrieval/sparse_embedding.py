"""Optional FastEmbed BM25 adapter; importing offline retrieval does not load a model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SparseEmbedding:
    indices: list[int]
    values: list[float]


class SparseEmbeddingModel(Protocol):
    def encode_documents(self, texts: list[str]) -> list[SparseEmbedding]: ...

    def encode_query(self, text: str) -> SparseEmbedding: ...


class FastEmbedBM25:
    """BM25 document weights and query tokens; Qdrant supplies corpus IDF.

    Query and document encoding are intentionally distinct. Both ingestion and
    retrieval must use the same locale/tokenizer. Turkish and English are
    supported by this application's adapter; unsupported locales fail clearly.
    """

    model_name = "Qdrant/bm25"

    def __init__(self, locale: str = "tr-TR") -> None:
        from fastembed import SparseTextEmbedding

        languages = {"tr": "turkish", "en": "english"}
        language = languages.get(locale.split("-", 1)[0].lower())
        if language is None:
            raise ValueError(f"BM25 locale is unsupported: {locale}; use tr-TR or en-US")
        self._model = SparseTextEmbedding(model_name=self.model_name, language=language)

    @staticmethod
    def _convert(embedding: object) -> SparseEmbedding:
        return SparseEmbedding(
            indices=[int(value) for value in embedding.indices],
            values=[float(value) for value in embedding.values],
        )

    def encode_documents(self, texts: list[str]) -> list[SparseEmbedding]:
        return [self._convert(vector) for vector in self._model.embed(texts)]

    def encode_query(self, text: str) -> SparseEmbedding:
        return self._convert(next(iter(self._model.query_embed(text))))
