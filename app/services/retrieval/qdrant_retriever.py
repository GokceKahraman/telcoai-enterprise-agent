"""Dense/BM25 hybrid search with tenant isolation inside both Qdrant prefetches.

The API adapter is read-only. Collection creation and incremental upserts belong
to the explicit ingestion command, so a restart never destroys or reindexes data.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

import numpy as np

from app.services.knowledge_base import FAQEntry, FAQRecord
from app.services.retrieval.base import RetrievalHit
from app.services.retrieval.embedding import EmbeddingModel
from app.services.retrieval.semantic_retriever import build_document_text
from app.services.retrieval.sparse_embedding import SparseEmbedding, SparseEmbeddingModel

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"


def point_id(entry: FAQEntry) -> str:
    """Stable IDs make re-ingestion idempotent without tenant/locale collisions."""
    import json

    identity = json.dumps([entry.tenant_id, entry.locale, entry.id], ensure_ascii=False)
    return str(uuid5(NAMESPACE_URL, identity))


def _sparse_vector(embedding: SparseEmbedding):
    from qdrant_client import models

    if (
        len(embedding.indices) != len(embedding.values)
        or len(set(embedding.indices)) != len(embedding.indices)
        or any(index < 0 for index in embedding.indices)
        or any(not math.isfinite(value) for value in embedding.values)
    ):
        raise ValueError("Invalid sparse embedding")
    return models.SparseVector(indices=embedding.indices, values=embedding.values)


def _dense_vectors(embedder: EmbeddingModel, texts: list[str]) -> np.ndarray:
    vectors = np.asarray(embedder.encode(texts), dtype=np.float32)
    if vectors.shape != (len(texts), embedder.embedding_dimension) or not np.all(
        np.isfinite(vectors)
    ):
        raise ValueError("Embedding model returned invalid shape or non-finite vectors")
    if np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise ValueError("Dense embeddings must not be zero vectors")
    return vectors


def ensure_collection(client: QdrantClient, collection: str, dimension: int) -> None:
    """Create a collection once; reject incompatible schemas instead of recreating it."""
    from qdrant_client import models

    if dimension < 1:
        raise ValueError("Embedding dimension must be positive")
    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config={
                DENSE_VECTOR: models.VectorParams(size=dimension, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                SPARSE_VECTOR: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
    else:
        parameters = client.get_collection(collection).config.params
        dense = parameters.vectors
        sparse = parameters.sparse_vectors or {}
        if (
            not isinstance(dense, dict)
            or DENSE_VECTOR not in dense
            or dense[DENSE_VECTOR].size != dimension
            or dense[DENSE_VECTOR].distance != models.Distance.COSINE
            or SPARSE_VECTOR not in sparse
            or sparse[SPARSE_VECTOR].modifier != models.Modifier.IDF
        ):
            raise ValueError(
                f"Collection {collection!r} has incompatible vector schema; "
                "select a new collection and ingest before switching the API"
            )

    # Create before upserts so Qdrant can build filter-aware HNSW edges.
    for field in ("tenant_id", "locale", "category"):
        client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )


def ingest_entries(
    client: QdrantClient,
    collection: str,
    entries: list[FAQEntry],
    dense_embedder: EmbeddingModel,
    sparse_embedder: SparseEmbeddingModel,
    *,
    batch_size: int = 64,
) -> int:
    """Incrementally upsert entries; preserve all other tenants and existing points.

    IDs absent from this batch are intentionally retained. Removing withdrawn
    documents is a separate lifecycle operation, never a side effect of ingestion.
    """
    from qdrant_client import models

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    identities = [point_id(entry) for entry in entries]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate entry IDs within a tenant/locale ingestion batch")
    if any(not entry.tenant_id.strip() or not entry.locale.strip() for entry in entries):
        raise ValueError("Entries must have a non-empty tenant_id and locale")
    ensure_collection(client, collection, dense_embedder.embedding_dimension)
    for start in range(0, len(entries), batch_size):
        batch = entries[start : start + batch_size]
        texts = [build_document_text(entry) for entry in batch]
        dense = _dense_vectors(dense_embedder, texts)
        sparse = sparse_embedder.encode_documents(texts)
        if len(sparse) != len(batch):
            raise ValueError("Sparse model returned an incorrect number of vectors")
        points = [
            models.PointStruct(
                id=point_id(entry),
                vector={
                    DENSE_VECTOR: dense_vector.tolist(),
                    SPARSE_VECTOR: _sparse_vector(sparse_vector),
                },
                payload={**asdict(entry), "keywords": list(entry.keywords)},
            )
            for entry, dense_vector, sparse_vector in zip(batch, dense, sparse, strict=True)
        ]
        client.upsert(collection_name=collection, points=points, wait=True)
    return len(entries)


class QdrantRetriever:
    """Server-owned tenant/locale scope; clients can only narrow by FAQ category.

    RRF combines ranks on independent score scales. Its score is useful for
    ordering and is not a calibrated probability that the answer is correct.
    """

    def __init__(
        self,
        client: QdrantClient,
        dense_embedder: EmbeddingModel,
        sparse_embedder: SparseEmbeddingModel,
        *,
        collection: str,
        tenant_id: str,
        locale: str,
        candidate_k: int = 20,
        min_dense_similarity: float = 0.42,
        validate_payload_indexes: bool = True,
    ) -> None:
        if not tenant_id.strip() or not locale.strip():
            raise ValueError("Tenant and locale scope are required")
        if candidate_k < 1:
            raise ValueError("candidate_k must be positive")
        self._client = client
        self._dense_embedder = dense_embedder
        self._sparse_embedder = sparse_embedder
        self._collection = collection
        self._tenant_id = tenant_id
        self._locale = locale
        self._candidate_k = candidate_k
        self._min_dense_similarity = min_dense_similarity
        self._validate_payload_indexes = validate_payload_indexes

    def ready(self) -> bool:
        """Check schema and scoped data without triggering creation or reindexing.

        Local Qdrant has no payload indexes. Unit tests may explicitly disable
        that check; the runtime factory always enforces it for a real server.
        """
        from qdrant_client import models

        if not self._client.collection_exists(self._collection):
            return False
        info = self._client.get_collection(self._collection)
        parameters = info.config.params
        dense = parameters.vectors
        sparse = parameters.sparse_vectors or {}
        if (
            not isinstance(dense, dict)
            or DENSE_VECTOR not in dense
            or dense[DENSE_VECTOR].size != self._dense_embedder.embedding_dimension
            or dense[DENSE_VECTOR].distance != models.Distance.COSINE
            or SPARSE_VECTOR not in sparse
            or sparse[SPARSE_VECTOR].modifier != models.Modifier.IDF
        ):
            return False
        if self._validate_payload_indexes and any(
            field not in info.payload_schema
            or info.payload_schema[field].data_type != models.PayloadSchemaType.KEYWORD
            for field in ("tenant_id", "locale", "category")
        ):
            return False
        return (
            self._client.count(
                collection_name=self._collection, count_filter=self._filter(None), exact=True
            ).count
            > 0
        )

    def close(self) -> None:
        self._client.close()

    def _filter(self, category: str | None):
        from qdrant_client import models

        values = {"tenant_id": self._tenant_id, "locale": self._locale}
        if category is not None:
            values["category"] = category
        return models.Filter(
            must=[
                models.FieldCondition(key=field, match=models.MatchValue(value=value))
                for field, value in values.items()
            ]
        )

    def retrieve(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[RetrievalHit]:
        from qdrant_client import models

        query = query.strip()
        if not query or top_k <= 0:
            return []
        dense = _dense_vectors(self._dense_embedder, [query])[0].tolist()
        sparse = _sparse_vector(self._sparse_embedder.encode_query(query))
        scope = self._filter(category)
        candidate_k = max(top_k, self._candidate_k)
        results = self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                models.Prefetch(
                    query=dense,
                    using=DENSE_VECTOR,
                    filter=scope,
                    score_threshold=self._min_dense_similarity,
                    limit=candidate_k,
                ),
                models.Prefetch(
                    query=sparse,
                    using=SPARSE_VECTOR,
                    filter=scope,
                    limit=candidate_k,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=scope,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        hits: list[RetrievalHit] = []
        for point in results.points:
            payload = point.payload or {}
            # Defense in depth: do not surface incorrectly scoped/malformed payloads.
            if (
                payload.get("tenant_id") != self._tenant_id
                or payload.get("locale") != self._locale
                or (category is not None and payload.get("category") != category)
            ):
                raise ValueError("Qdrant returned a payload outside the configured scope")
            record = FAQRecord.model_validate(payload)
            entry = FAQEntry(
                id=record.id,
                category=record.category,
                question=record.question,
                keywords=tuple(record.keywords),
                answer=record.answer,
                question_en=record.question_en,
                keywords_en=tuple(record.keywords_en),
                answer_en=record.answer_en,
                tenant_id=record.tenant_id,
                locale=record.locale,
            )
            score = float(point.score)
            hits.append(
                RetrievalHit(
                    entry=entry,
                    score=score,
                    confidence=round(max(0.0, min(1.0, score)), 4),
                )
            )
        return hits
