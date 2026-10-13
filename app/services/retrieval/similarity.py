from __future__ import annotations

import numpy as np


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Satır bazında L2 normalizasyonu — kosinüs benzerliği için dot product yeterli olur."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vectors / norms


def cosine_similarity(query_vector: np.ndarray, document_matrix: np.ndarray) -> np.ndarray:
    """
    query_vector: (d,) veya (1, d)
    document_matrix: (n, d) — satırlar L2-normalize varsayılır (encode aşamasında).
    Dönüş: (n,) benzerlik skorları.
    """
    q = query_vector.reshape(1, -1)
    q = l2_normalize(q)
    return np.dot(document_matrix, q.T).ravel()
