import numpy as np

from app.services.retrieval.semantic_retriever import SemanticRetriever, build_document_text


class FixedVectorEmbedder:
    """Belirli metinler için önceden tanımlı vektörler — sıralama testleri."""

    def __init__(self, vectors: dict[str, np.ndarray]) -> None:
        self._vectors = vectors
        first = next(iter(vectors.values()))
        self._dim = int(first.shape[0])

    @property
    def embedding_dimension(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vectors[t] for t in texts])


def test_build_document_text_includes_question_and_keywords(knowledge_base):
    entry = knowledge_base.entries[0]
    text = build_document_text(entry)
    assert entry.question in text
    assert entry.keywords[0] in text
    assert entry.answer not in text


class _TwoEntryKB:
    def __init__(self, entries: list) -> None:
        self.entries = entries


def test_semantic_retriever_ranks_by_similarity(knowledge_base):
    e0, e1 = knowledge_base.entries[0], knowledge_base.entries[1]
    mini_kb = _TwoEntryKB([e0, e1])
    t0 = build_document_text(e0)
    t1 = build_document_text(e1)
    q = "test query"

    v0 = np.array([1.0, 0.0], dtype=np.float32)
    v1 = np.array([0.0, 1.0], dtype=np.float32)
    vq = np.array([0.95, 0.05], dtype=np.float32)

    embedder = FixedVectorEmbedder({t0: v0, t1: v1, q: vq})
    retriever = SemanticRetriever(mini_kb, embedder, min_similarity=0.0)
    hits = retriever.retrieve(q, top_k=2)
    assert len(hits) == 2
    assert hits[0].entry.id == e0.id
    assert hits[0].score > hits[1].score


def test_semantic_retriever_rejects_below_threshold(knowledge_base, mock_embedder):
    retriever = SemanticRetriever(knowledge_base, mock_embedder, min_similarity=0.99)
    hits = retriever.retrieve("tamamen alakasız bir metin", top_k=3)
    assert hits == []


def test_semantic_retriever_empty_query(knowledge_base, mock_embedder):
    retriever = SemanticRetriever(knowledge_base, mock_embedder, min_similarity=0.0)
    assert retriever.retrieve("   ", top_k=3) == []


def test_mock_embedder_dimension_and_normalization(mock_embedder):
    matrix = mock_embedder.encode(["a", "b"])
    assert matrix.shape == (2, mock_embedder.embedding_dimension)
    norms = np.linalg.norm(matrix, axis=1)
    assert np.allclose(norms, 1.0)
