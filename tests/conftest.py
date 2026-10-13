import hashlib
import os

# API testleri model indirmeden çalışsın — main importundan önce strateji seçilir.
os.environ.setdefault("TELCOAI_RETRIEVAL_STRATEGY", "keyword")

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.chat_service import ChatService
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.keyword_retriever import KeywordRetriever


@pytest.fixture
def knowledge_base_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"


@pytest.fixture
def knowledge_base(knowledge_base_path: Path) -> KnowledgeBase:
    return KnowledgeBase(knowledge_base_path)


@pytest.fixture
def keyword_retriever(knowledge_base: KnowledgeBase) -> KeywordRetriever:
    return KeywordRetriever(knowledge_base, min_match_score=1.0)


@pytest.fixture
def chat_service(keyword_retriever: KeywordRetriever) -> ChatService:
    return ChatService(keyword_retriever, top_k=3)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


class DeterministicMockEmbedder:
    """Unit testler için sabit boyutlu, tekrarlanabilir vektörler."""

    def __init__(self, dimension: int = 16) -> None:
        self._dimension = dimension

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        rows = [self._vector_for(text) for text in texts]
        return np.vstack(rows)

    def _vector_for(self, text: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dimension).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm


@pytest.fixture
def mock_embedder() -> DeterministicMockEmbedder:
    return DeterministicMockEmbedder(dimension=32)
