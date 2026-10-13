#!/usr/bin/env python3
"""Evaluate guarded support answers separately from raw retrieval rankings."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.chat_service import ChatService
from app.services.knowledge_base import KnowledgeBase
from app.services.privacy import PrivacyService
from app.services.retrieval.factory import build_retriever
from app.services.retrieval.semantic_retriever import DOCUMENT_REPRESENTATION_VERSION
from app.services.store import MemoryStore
from scripts.evaluate_retrieval import (
    load_dataset,
    path_label,
    percentile,
    sha256_file,
    validate_labels,
)


def evaluate_workflow(
    service_factory: Callable[[], ChatService],
    knowledge_base: KnowledgeBase,
    dataset: dict[str, Any],
    *,
    repeats: int = 1,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Each trial gets a fresh graph, session and cache, over a shared retriever."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    privacy = PrivacyService()
    hit1 = ood_false_answers = fallbacks = handoffs = sourced = grounded = 0
    relevant_fallbacks = ood_fallbacks = 0
    latencies: list[float] = []
    records: list[dict[str, Any]] = []
    relevant = dataset["relevant_queries"]
    ood = dataset["irrelevant_queries"]
    for repeat in range(repeats):
        for group, items in (("relevant", relevant), ("ood", ood)):
            for item in items:
                # Graph construction is outside latency; no context/cache leaks between trials.
                service = service_factory()
                started = time.perf_counter()
                response = service.reply(item["query"])
                latency = (time.perf_counter() - started) * 1000
                latencies.append(latency)
                expected = item.get("expected_entry_ids", [])
                source_id = response.source.entry_id if response.source is not None else None
                has_answer = source_id is not None and not response.fallback
                reference = knowledge_base.get_by_id(source_id) if source_id else None
                answer_grounded = (
                    reference is not None
                    and response.answer == privacy.redact(reference.answer).text
                )
                if source_id is not None:
                    sourced += 1
                    grounded += answer_grounded
                if group == "relevant":
                    hit1 += has_answer and source_id in expected
                    relevant_fallbacks += response.fallback
                else:
                    ood_false_answers += has_answer
                    ood_fallbacks += response.fallback
                fallbacks += response.fallback
                handoffs += response.handoff
                records.append(
                    {
                        "id": item["id"],
                        "group": group,
                        "repeat": repeat,
                        "expected_entry_ids": expected,
                        "source_entry_id": source_id,
                        "fallback": response.fallback,
                        "handoff": response.handoff,
                        "grounded": answer_grounded if source_id is not None else None,
                        "cache_hit": response.cache_hit,
                        "steps": response.steps,
                        "latency_ms": latency,
                    }
                )
    return (
        {
            "source_hit_at_1": hit1 / (len(relevant) * repeats),
            "ood_false_answer_rate": ood_false_answers / (len(ood) * repeats),
            "source_grounding_rate": grounded / sourced if sourced else None,
            "relevant_count": len(relevant),
            "ood_count": len(ood),
            "repeats": repeats,
            "hit1_count": hit1,
            "ood_false_answer_count": ood_false_answers,
            "fallback_count": fallbacks,
            "relevant_fallback_count": relevant_fallbacks,
            "ood_fallback_count": ood_fallbacks,
            "handoff_count": handoffs,
            "sourced_count": sourced,
            "grounded_count": grounded,
            "grounding_failure_count": sourced - grounded,
            "mean_latency_ms": statistics.mean(latencies),
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
        },
        records,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/evaluation/retrieval_eval.json"
    )
    parser.add_argument("--knowledge-base", type=Path, default=ROOT / "data/knowledge_base.json")
    parser.add_argument(
        "--strategy", choices=("keyword", "semantic", "qdrant_hybrid"), default="keyword"
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/workflow-evaluation.json")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    settings = get_settings().model_copy(
        update={
            "retrieval_strategy": args.strategy,
            "generation_backend": "extractive",
            "guardrails_enabled": False,
            "langfuse_enabled": False,
            "storage_backend": "memory",
            "semantic_cache_enabled": False,
            "reranker_enabled": False,
        }
    )
    dataset = load_dataset(args.dataset)
    knowledge_base = KnowledgeBase(args.knowledge_base).scoped(settings.tenant_id, settings.locale)
    validate_labels(dataset, knowledge_base)
    started = time.perf_counter()
    retriever = build_retriever(settings, knowledge_base)
    initialization_ms = (time.perf_counter() - started) * 1000

    def service_factory() -> ChatService:
        return ChatService(
            retriever, top_k=settings.retrieval_top_k, settings=settings, store=MemoryStore()
        )

    try:
        # Warm model and workflow without preserving the warmup's session/cache.
        service_factory().reply("Fatura ödeme kanalları")
        metrics, records = evaluate_workflow(
            service_factory, knowledge_base, dataset, repeats=args.repeats
        )
    finally:
        close = getattr(retriever, "close", None)
        if close:
            close()
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "evaluation_layer": "guarded_chat_service",
        "dataset": {"path": path_label(args.dataset), "sha256": sha256_file(args.dataset)},
        "corpus": {
            "path": path_label(args.knowledge_base),
            "sha256": sha256_file(args.knowledge_base),
            "entries": len(knowledge_base.entries),
        },
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "configuration": {
            "strategy": args.strategy,
            "generation_backend": "extractive",
            "storage_backend": "fresh_memory_per_query",
            "session_cache_isolation": True,
            "langfuse_enabled": False,
            "top_k": settings.retrieval_top_k,
            "candidate_k": settings.retrieval_candidate_k,
            "min_match_score": settings.min_match_score,
            "semantic_min_similarity": settings.semantic_min_similarity,
            "embedding_model": settings.embedding_model_name,
            "document_representation_version": DOCUMENT_REPRESENTATION_VERSION,
            "reranker_enabled": False,
            "tenant_id": settings.tenant_id,
            "locale": settings.locale,
        },
        "initialization_ms": initialization_ms,
        "metrics": metrics,
        "queries": records,
        "limitations": [
            "Small synthetic development dataset; no held-out or production quality claim.",
            "Source grounding means exact masked FAQ agreement, not answer relevance.",
            "Fresh service/session/cache per query; no multi-turn or cache performance evaluation.",
            "Latency includes ChatService, excluding graph construction, warmup and API transport.",
            "Domain rules may reject supported queries; human review/larger OOD sets are needed.",
            "LLM generation, Langfuse, Redis and BGE re-ranking are disabled for this measurement.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"workflow/{args.strategy}: Source Hit@1={metrics['source_hit_at_1']:.1%}; "
        f"OOD false answer={metrics['ood_false_answer_rate']:.1%}; "
        f"grounded={metrics['grounded_count']}/{metrics['sourced_count']}"
    )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
