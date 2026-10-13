import numpy as np

from app.services.retrieval.similarity import cosine_similarity, l2_normalize


def test_l2_normalize_unit_length():
    vectors = np.array([[3.0, 4.0], [0.0, 0.0]], dtype=np.float32)
    normalized = l2_normalize(vectors)
    assert np.isclose(np.linalg.norm(normalized[0]), 1.0)
    assert np.allclose(normalized[1], 0.0)


def test_cosine_similarity_identical_vectors():
    doc = l2_normalize(np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    sim = cosine_similarity(np.array([1.0, 0.0], dtype=np.float32), doc)
    assert np.isclose(sim[0], 1.0)
    assert np.isclose(sim[1], 0.0)


def test_cosine_similarity_ordering():
    doc = l2_normalize(np.array([[1.0, 0.0], [0.7, 0.7], [0.0, 1.0]], dtype=np.float32))
    sim = cosine_similarity(np.array([0.9, 0.1], dtype=np.float32), doc)
    assert sim[0] > sim[1] > sim[2]
