from __future__ import annotations

from typing import Protocol

import numpy as np


class EmbeddingModel(Protocol):
    """Metin → vektör dönüşümü (testlerde mocklanır)."""

    @property
    def embedding_dimension(self) -> int: ...

    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedding:
    """Hugging Face sentence-transformers modelini uygulama ömründe bir kez yükler."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        sample = self._model.encode(["dimension probe"], normalize_embeddings=True)
        self._dim = int(sample.shape[1])

    @property
    def embedding_dimension(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)
