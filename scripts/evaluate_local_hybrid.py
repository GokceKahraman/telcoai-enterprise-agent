#!/usr/bin/env python3
"""Measure real dense/BM25 models against Qdrant's in-memory query engine.

This isolates retrieval quality from server transport. It does not exercise
server-side payload-index performance; those checks have a separate integration
test. First run downloads multilingual MiniLM and small BM25 tokenizer resources.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.chat_service import ChatService
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.factory import get_embedding_model, get_sparse_embedding_model
from app.services.retrieval.qdrant_retriever import QdrantRetriever, ingest_entries
from app.services.retrieval.semantic_retriever import DOCUMENT_REPRESENTATION_VERSION
from app.services.store import MemoryStore
from scripts.evaluate_retrieval import (
    evaluate_strategy,
    load_dataset,
    path_label,
    sha256_file,
    validate_labels,
)
from scripts.evaluate_workflow import evaluate_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/evaluation/retrieval_eval.json"
    )
    parser.add_argument("--knowledge-base", type=Path, default=ROOT / "data/knowledge_base.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/hybrid-evaluation.json")
    parser.add_argument(
        "--workflow-output", type=Path, help="Also measure the guarded ChatService over real models"
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.top_k < 3 or args.repeats < 1:
        parser.error("--top-k must be at least 3 and --repeats must be positive")
    settings = get_settings()
    dataset = load_dataset(args.dataset)
    knowledge_base = KnowledgeBase(args.knowledge_base).scoped(settings.tenant_id, settings.locale)
    validate_labels(dataset, knowledge_base)

    from qdrant_client import QdrantClient

    started = time.perf_counter()
    dense = get_embedding_model(settings.embedding_model_name)
    sparse = get_sparse_embedding_model(settings.locale)
    client = QdrantClient(":memory:")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Payload indexes have no effect in the local")
            ingest_entries(client, "measured_faq", knowledge_base.entries, dense, sparse)
        retriever = QdrantRetriever(
            client,
            dense,
            sparse,
            collection="measured_faq",
            tenant_id=settings.tenant_id,
            locale=settings.locale,
            candidate_k=settings.retrieval_candidate_k,
            min_dense_similarity=settings.semantic_min_similarity,
            validate_payload_indexes=False,
        )
        if not retriever.ready():
            raise RuntimeError("In-memory corpus is not ready after explicit ingestion")
        initialization_ms = (time.perf_counter() - started) * 1000
        metrics, records = evaluate_strategy(
            "qdrant_hybrid", retriever, dataset, top_k=args.top_k, repeats=args.repeats
        )
        workflow_metrics = workflow_records = None
        if args.workflow_output:
            workflow_settings = settings.model_copy(
                update={
                    "retrieval_strategy": "qdrant_hybrid",
                    "generation_backend": "extractive",
                    "guardrails_enabled": False,
                    "langfuse_enabled": False,
                    "semantic_cache_enabled": False,
                    "reranker_enabled": False,
                }
            )

            def service_factory() -> ChatService:
                return ChatService(
                    retriever,
                    top_k=settings.retrieval_top_k,
                    settings=workflow_settings,
                    store=MemoryStore(),
                )

            service_factory().reply("Fatura ödeme kanalları")
            workflow_metrics, workflow_records = evaluate_workflow(
                service_factory, knowledge_base, dataset, repeats=args.repeats
            )
    finally:
        client.close()
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "path": path_label(args.dataset),
            "sha256": sha256_file(args.dataset),
            "version": dataset.get("version"),
        },
        "corpus": {
            "path": path_label(args.knowledge_base),
            "sha256": sha256_file(args.knowledge_base),
            "entries": len(knowledge_base.entries),
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "qdrant_mode": "in_memory_local_query_engine",
            "packages": {
                name: version(name)
                for name in ("qdrant-client", "sentence-transformers", "fastembed")
            },
        },
        "configuration": {
            "strategy": "qdrant_hybrid",
            "fusion": "RRF",
            "document_representation_version": DOCUMENT_REPRESENTATION_VERSION,
            "top_k": args.top_k,
            "repeats": args.repeats,
            "semantic_min_similarity": settings.semantic_min_similarity,
            "embedding_model": settings.embedding_model_name,
            "sparse_model": "Qdrant/bm25",
            "candidate_k": settings.retrieval_candidate_k,
            "reranker_enabled": False,
            "tenant_id": settings.tenant_id,
            "locale": settings.locale,
        },
        "initialization_ms": initialization_ms,
        "metrics": asdict(metrics),
        "queries": records,
        "limitations": [
            "Synthetic, small FAQ corpus; results do not establish production quality.",
            "Real model embeddings and Qdrant local queries; no remote server transport or HNSW.",
            "Local Qdrant has no payload indexes; validation requires opt-in server integration.",
            "Latency excludes construction/warmup, privacy, cache and graph overhead.",
            "No BGE reranker was enabled or downloaded in this measurement.",
            "Retriever scores and model confidence are not calibrated probabilities.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"qdrant_hybrid: Hit@1={metrics.hit_at_1:.1%} Hit@3={metrics.hit_at_3:.1%} "
        f"MRR@{metrics.mrr_cutoff}={metrics.mrr:.4f} "
        f"OOD false acceptance={metrics.ood_false_accept_rate:.1%}"
    )
    print(f"Report: {args.output}")
    if args.workflow_output:
        workflow_report = {
            **report,
            "evaluation_layer": "guarded_chat_service",
            "configuration": {
                **report["configuration"],
                "top_k": settings.retrieval_top_k,
                "generation_backend": "extractive",
                "storage_backend": "fresh_memory_per_query",
                "session_cache_isolation": True,
                "langfuse_enabled": False,
            },
            "metrics": workflow_metrics,
            "queries": workflow_records,
            "raw_retrieval_report": path_label(args.output),
            "limitations": [
                "Small synthetic development dataset; no heldout or production quality claim.",
                "Source grounding means exact masked FAQ agreement, not answer relevance.",
                "Fresh service/session/cache per query; no multi-turn or cache evaluation.",
                "Latency includes ChatService, excluding graph construction and API transport.",
                "Local Qdrant has no payload indexes; server integration was not executed.",
                "Domain rules may reject supported queries; larger OOD sets are needed.",
                "LLM, Langfuse, Redis and BGE reranking are disabled in this measurement.",
            ],
        }
        args.workflow_output.parent.mkdir(parents=True, exist_ok=True)
        args.workflow_output.write_text(
            json.dumps(workflow_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"workflow/qdrant_hybrid: Source Hit@1={workflow_metrics['source_hit_at_1']:.1%}; "
            f"OOD false answer={workflow_metrics['ood_false_answer_rate']:.1%}"
        )
        print(f"Workflow report: {args.workflow_output}")


if __name__ == "__main__":
    main()
