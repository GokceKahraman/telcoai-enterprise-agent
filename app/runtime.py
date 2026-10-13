"""Explicit resource lifecycle; importing the ASGI app does not download models."""

import hashlib
import json
from dataclasses import dataclass

from app.config import Settings
from app.services.chat_service import ChatService
from app.services.generation import StructuredGenerator
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.factory import build_retriever, get_embedding_model
from app.services.retrieval.semantic_retriever import DOCUMENT_REPRESENTATION_VERSION
from app.services.store import MemoryStore, RedisStore
from app.services.telemetry import Telemetry


@dataclass
class Runtime:
    settings: Settings
    knowledge_base: KnowledgeBase
    service: ChatService

    def readiness(self) -> dict[str, bool]:
        checks = {"storage": False, "retrieval": False}
        try:
            checks["storage"] = self.service.store.ready()
        except Exception:
            pass
        try:
            retriever = self.service._retriever
            # Reranking wrapper delegates readiness to its underlying retriever.
            check = getattr(retriever, "ready", None)
            checks["retrieval"] = bool(check()) if check else bool(self.knowledge_base.entries)
        except Exception:
            pass
        return checks

    def close(self) -> None:
        self.service.close()


def build_runtime(settings: Settings) -> Runtime:
    kb = KnowledgeBase(settings.knowledge_base_path).scoped(settings.tenant_id, settings.locale)
    retriever = build_retriever(settings, kb)
    # Version caches by KB, tenant/locale and every retrieval/generation configuration.
    identity = {
        "knowledge": kb.fingerprint,
        "tenant": settings.tenant_id,
        "locale": settings.locale,
        "strategy": settings.retrieval_strategy,
        "dense": settings.embedding_model_name,
        "document_representation": DOCUMENT_REPRESENTATION_VERSION,
        "collection": settings.qdrant_collection,
        "qdrant_url": settings.qdrant_url,
        "threshold": settings.semantic_min_similarity,
        "keyword_threshold": settings.min_match_score,
        "top_k": settings.retrieval_top_k,
        "candidate_k": settings.retrieval_candidate_k,
        "reranker": settings.reranker_model if settings.reranker_enabled else None,
        "generator": settings.generation_backend,
        "llm": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "guardrails": settings.guardrails_enabled,
        "prompt_version": "faq-selector-v1",
        "policy_version": "telecom-scope-v1",
        "semantic_cache": settings.semantic_cache_threshold,
    }
    namespace = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    args = dict(
        session_ttl=settings.session_ttl_seconds,
        cache_ttl=settings.cache_ttl_seconds,
        max_messages=settings.session_max_messages,
    )
    if settings.storage_backend == "redis":
        import redis

        client = redis.Redis.from_url(
            settings.redis_url.get_secret_value(),
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        store = RedisStore(client, namespace=namespace, **args)
    else:
        store = MemoryStore(**args)
    embedder = (
        get_embedding_model(settings.embedding_model_name)
        if settings.semantic_cache_enabled
        else None
    )
    generator = StructuredGenerator(settings) if settings.generation_backend == "llm" else None
    service = ChatService(
        retriever,
        top_k=settings.retrieval_top_k,
        settings=settings,
        store=store,
        fingerprint=namespace,
        embedder=embedder,
        generator=generator,
        telemetry=Telemetry(settings.langfuse_enabled),
    )
    return Runtime(settings, kb, service)
