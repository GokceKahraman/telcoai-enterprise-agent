#!/usr/bin/env python3
"""Compare keyword, dense, BM25, hybrid and hybrid+BGE on identical inputs."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import warnings
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.factory import get_embedding_model, get_sparse_embedding_model
from app.services.retrieval.keyword_retriever import KeywordRetriever
from app.services.retrieval.qdrant_retriever import QdrantRetriever, ingest_entries
from app.services.retrieval.reranker import BGEReranker, RerankingRetriever
from app.services.retrieval.semantic_retriever import (
    DOCUMENT_REPRESENTATION_VERSION,
    SemanticRetriever,
)
from scripts.evaluate_retrieval import evaluate_strategy, load_dataset, sha256_file, validate_labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/evaluation/retrieval_eval.json"
    )
    parser.add_argument("--knowledge-base", type=Path, default=ROOT / "data/knowledge_base.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/search-matrix-development.json")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--skip-reranker", action="store_true", help="Skip optional BGE model")
    args = parser.parse_args()
    if args.top_k < 3 or args.repeats < 1:
        parser.error("--top-k must be at least 3 and --repeats must be positive")

    settings = get_settings()
    dataset = load_dataset(args.dataset)
    kb = KnowledgeBase(args.knowledge_base).scoped(settings.tenant_id, settings.locale)
    validate_labels(dataset, kb)

    from qdrant_client import QdrantClient

    started = time.perf_counter()
    dense = get_embedding_model(settings.embedding_model_name)
    sparse = get_sparse_embedding_model(settings.locale)
    client = QdrantClient(":memory:")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Payload indexes have no effect in the local")
            ingest_entries(client, "search_matrix", kb.entries, dense, sparse)
        base = QdrantRetriever(
            client,
            dense,
            sparse,
            collection="search_matrix",
            tenant_id=settings.tenant_id,
            locale=settings.locale,
            candidate_k=max(settings.retrieval_candidate_k, args.top_k),
            min_dense_similarity=settings.semantic_min_similarity,
            validate_payload_indexes=False,
        )
        bm25 = QdrantRetriever(
            client,
            dense,
            sparse,
            collection="search_matrix",
            tenant_id=settings.tenant_id,
            locale=settings.locale,
            candidate_k=max(settings.retrieval_candidate_k, args.top_k),
            min_dense_similarity=settings.semantic_min_similarity,
            validate_payload_indexes=False,
            search_mode="bm25",
        )
        strategies = [
            (
                "keyword",
                KeywordRetriever(
                    kb,
                    min_match_score=settings.min_match_score,
                    tenant_id=settings.tenant_id,
                    locale=settings.locale,
                ),
            ),
            (
                "semantic",
                SemanticRetriever(
                    kb,
                    dense,
                    min_similarity=settings.semantic_min_similarity,
                    tenant_id=settings.tenant_id,
                    locale=settings.locale,
                ),
            ),
            ("bm25", bm25),
            ("hybrid", base),
        ]
        skipped_strategies = []
        if args.skip_reranker:
            skipped_strategies.append(
                {"name": "hybrid_bge_reranker", "reason": "Explicitly skipped via --skip-reranker."}
            )
        else:
            try:
                reranker = BGEReranker(settings.reranker_model)
            except (OSError, ImportError, RuntimeError):
                skipped_strategies.append(
                    {
                        "name": "hybrid_bge_reranker",
                        "reason": "BGE weights were not cached and could not be downloaded "
                        "in this environment.",
                    }
                )
            else:
                strategies.append(
                    (
                        "hybrid_bge_reranker",
                        RerankingRetriever(
                            base,
                            reranker,
                            candidate_k=max(settings.retrieval_candidate_k, args.top_k),
                        ),
                    )
                )

        reports = []
        init_ms = (time.perf_counter() - started) * 1000
        for name, retriever in strategies:
            metrics, queries = evaluate_strategy(
                name, retriever, dataset, top_k=args.top_k, repeats=args.repeats
            )
            reports.append({"metrics": asdict(metrics), "queries": queries})
        report = {
            "schema_version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "purpose": "development_comparison_same_dataset_and_corpus",
            "dataset": {
                "path": args.dataset.name,
                "sha256": sha256_file(args.dataset),
                "version": dataset.get("version"),
            },
            "corpus": {
                "path": args.knowledge_base.name,
                "sha256": sha256_file(args.knowledge_base),
                "entries": len(kb.entries),
            },
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "qdrant_mode": "in_memory_local_query_engine",
            },
            "configuration": {
                "top_k": args.top_k,
                "repeats": args.repeats,
                "semantic_min_similarity": settings.semantic_min_similarity,
                "min_match_score": settings.min_match_score,
                "embedding_model": settings.embedding_model_name,
                "sparse_model": "Qdrant/bm25",
                "reranker_model": settings.reranker_model,
                "candidate_k": max(settings.retrieval_candidate_k, args.top_k),
                "tenant_id": settings.tenant_id,
                "locale": settings.locale,
                "document_representation_version": DOCUMENT_REPRESENTATION_VERSION,
            },
            "initialization_ms": init_ms,
            "strategies": reports,
            "skipped_strategies": skipped_strategies,
            "limitations": [
                "The development set guided retrieval changes; this matrix is tuning evidence, "
                "not independent validation.",
                "Use a newly authored v2 set for an unbiased final estimate; v1 is only "
                "known-regression replay evidence.",
                "Synthetic 40-entry FAQ corpus; local in-memory Qdrant does not measure "
                "payload-index or network performance.",
                "Latency excludes service transport, guardrails, generation, tracing and "
                "cache overhead.",
            ],
        }
    finally:
        client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Dataset SHA-256: {report['dataset']['sha256']}")
    print(f"Corpus SHA-256:  {report['corpus']['sha256']}")
    for item in reports:
        m = item["metrics"]
        print(
            f"{m['name']}: Hit@1 {m['hit_at_1']:.1%} · Hit@3 {m['hit_at_3']:.1%} · "
            f"MRR@{m['mrr_cutoff']} {m['mrr']:.3f} · OOD accept {m['ood_false_accept_rate']:.1%} · "
            f"p50 {m['latency_p50_ms']:.1f} ms · failures "
            f"{sum(bool(q['failure_type']) for q in item['queries'] if q['repeat'] == 0)}"
        )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
