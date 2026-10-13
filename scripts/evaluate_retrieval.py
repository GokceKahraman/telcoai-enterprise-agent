#!/usr/bin/env python3
"""Reproducible retrieval benchmark; keyword mode needs no model or API key."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.base import RetrievalHit, Retriever
from app.services.retrieval.factory import build_retriever
from app.services.retrieval.semantic_retriever import DOCUMENT_REPRESENTATION_VERSION


@dataclass(frozen=True)
class StrategyMetrics:
    name: str
    hit_at_1: float
    hit_at_3: float
    mrr: float
    mrr_cutoff: int
    ood_false_accept_rate: float
    mean_latency_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    relevant_count: int
    ood_count: int
    repeats: int
    hit1_count: int
    hit3_count: int
    false_accept_count: int


def load_dataset(path: Path) -> dict[str, Any]:
    """Fail early on malformed labels rather than quietly changing denominators."""
    dataset = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for group in ("relevant_queries", "irrelevant_queries"):
        if not isinstance(dataset.get(group), list) or not dataset[group]:
            raise ValueError(f"{group} must be a nonempty list")
        for item in dataset[group]:
            if not isinstance(item.get("query"), str) or not item["query"].strip():
                raise ValueError("Every evaluation item needs a nonempty query")
            identifier = item.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                raise ValueError("Evaluation item IDs must be nonempty and unique")
            seen.add(identifier)
            if group == "relevant_queries":
                expected = item.get("expected_entry_ids")
                if not isinstance(expected, list) or not expected:
                    raise ValueError(f"{identifier}: expected_entry_ids must be nonempty")
                if any(not isinstance(value, str) or not value for value in expected):
                    raise ValueError(f"{identifier}: expected IDs must be nonempty strings")
    return dataset


def validate_labels(dataset: dict[str, Any], knowledge_base: KnowledgeBase) -> None:
    known = {entry.id for entry in knowledge_base.entries}
    missing = {
        identifier
        for item in dataset["relevant_queries"]
        for identifier in item["expected_entry_ids"]
        if identifier not in known
    }
    if missing:
        raise ValueError(f"Evaluation references unknown FAQ IDs: {sorted(missing)}")


def hit_at_k(hits: list[RetrievalHit], expected_ids: list[str], k: int) -> bool:
    return any(hit.entry.id in expected_ids for hit in hits[:k])


def reciprocal_rank(hits: list[RetrievalHit], expected_ids: list[str]) -> float:
    for rank, hit in enumerate(hits, start=1):
        if hit.entry.id in expected_ids:
            return 1.0 / rank
    return 0.0


def percentile(values: list[float], percent: float) -> float:
    """Linear interpolation, with a defined result for one measurement."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_strategy(
    name: str,
    retriever: Retriever,
    dataset: dict[str, Any],
    *,
    warmup_query: str | None = "Fatura ödeme kanalları",
    top_k: int = 10,
    repeats: int = 1,
) -> tuple[StrategyMetrics, list[dict[str, Any]]]:
    if top_k < 3 or repeats < 1:
        raise ValueError("top_k must be at least 3 and repeats must be positive")
    if warmup_query:
        retriever.retrieve(warmup_query, top_k=top_k)
    relevant = dataset["relevant_queries"]
    ood = dataset["irrelevant_queries"]
    hit1 = hit3 = false_accepts = 0
    reciprocal_ranks: list[float] = []
    latencies: list[float] = []
    records: list[dict[str, Any]] = []
    for repeat in range(repeats):
        for group, items in (("relevant", relevant), ("ood", ood)):
            for item in items:
                started = time.perf_counter()
                hits = retriever.retrieve(item["query"], top_k=top_k)
                latency = (time.perf_counter() - started) * 1000
                latencies.append(latency)
                expected = item.get("expected_entry_ids", [])
                if group == "relevant":
                    hit1 += hit_at_k(hits, expected, 1)
                    hit3 += hit_at_k(hits, expected, 3)
                    reciprocal_ranks.append(reciprocal_rank(hits, expected))
                else:
                    false_accepts += bool(hits)
                records.append(
                    {
                        "id": item["id"],
                        "group": group,
                        "repeat": repeat,
                        "expected_entry_ids": expected,
                        "retrieved_entry_ids": [hit.entry.id for hit in hits],
                        "scores": [float(hit.score) for hit in hits],
                        "latency_ms": latency,
                    }
                )
    return (
        StrategyMetrics(
            name=name,
            hit_at_1=hit1 / (len(relevant) * repeats),
            hit_at_3=hit3 / (len(relevant) * repeats),
            mrr=statistics.mean(reciprocal_ranks),
            mrr_cutoff=top_k,
            ood_false_accept_rate=false_accepts / (len(ood) * repeats),
            mean_latency_ms=statistics.mean(latencies),
            latency_p50_ms=percentile(latencies, 50),
            latency_p95_ms=percentile(latencies, 95),
            relevant_count=len(relevant),
            ood_count=len(ood),
            repeats=repeats,
            hit1_count=hit1,
            hit3_count=hit3,
            false_accept_count=false_accepts,
        ),
        records,
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_label(path: Path) -> str:
    """Keep reports portable without exposing the author's home directory."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def log_mlflow(report: dict[str, Any], output: Path, tracking_uri: str) -> None:
    """Optional local/remote experiment tracking; credentials are never parameters."""
    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError("MLflow requires: uv sync --extra eval") from exc
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("telcoai-retrieval")
    with mlflow.start_run(run_name=report["metrics"]["name"]):
        mlflow.log_params(report["configuration"])
        mlflow.log_params(
            {
                "dataset_sha256": report["dataset"]["sha256"],
                "corpus_sha256": report["corpus"]["sha256"],
            }
        )
        mlflow.log_metrics(
            {
                name: value
                for name, value in report["metrics"].items()
                if isinstance(value, (int, float))
            }
        )
        mlflow.log_artifact(str(output))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/evaluation/retrieval_eval.json"
    )
    parser.add_argument("--knowledge-base", type=Path, default=ROOT / "data/knowledge_base.json")
    parser.add_argument(
        "--strategy", choices=("keyword", "semantic", "qdrant_hybrid"), default="keyword"
    )
    parser.add_argument(
        "--keyword-only", action="store_true", help="Compatibility alias for --strategy keyword"
    )
    parser.add_argument("--semantic-threshold", type=float)
    parser.add_argument("--top-k", type=int, default=10, help="MRR cutoff; at least 3")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/retrieval-evaluation.json")
    parser.add_argument(
        "--mlflow-tracking-uri", help="Opt in to MLflow, e.g. sqlite:///artifacts/mlflow.db"
    )
    args = parser.parse_args()
    if args.top_k < 3 or args.repeats < 1:
        parser.error("--top-k must be at least 3 and --repeats must be positive")
    if args.keyword_only and args.strategy != "keyword":
        parser.error("--keyword-only cannot be combined with another strategy")
    updates: dict[str, Any] = {"retrieval_strategy": args.strategy}
    if args.strategy != "qdrant_hybrid":
        updates["reranker_enabled"] = False
    if args.semantic_threshold is not None:
        if not 0 <= args.semantic_threshold <= 1:
            parser.error("--semantic-threshold must be between 0 and 1")
        updates["semantic_min_similarity"] = args.semantic_threshold
    settings = get_settings().model_copy(update=updates)
    dataset = load_dataset(args.dataset)
    knowledge_base = KnowledgeBase(args.knowledge_base).scoped(settings.tenant_id, settings.locale)
    validate_labels(dataset, knowledge_base)
    started = time.perf_counter()
    retriever = build_retriever(settings, knowledge_base)
    initialization_ms = (time.perf_counter() - started) * 1000
    try:
        metrics, records = evaluate_strategy(
            args.strategy, retriever, dataset, top_k=args.top_k, repeats=args.repeats
        )
    finally:
        close = getattr(retriever, "close", None)
        if close:
            close()
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
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "configuration": {
            "strategy": args.strategy,
            "top_k": args.top_k,
            "repeats": args.repeats,
            "min_match_score": settings.min_match_score,
            "semantic_min_similarity": settings.semantic_min_similarity,
            "embedding_model": settings.embedding_model_name,
            "document_representation_version": DOCUMENT_REPRESENTATION_VERSION,
            "candidate_k": settings.retrieval_candidate_k,
            "reranker_enabled": settings.reranker_enabled,
            "reranker_model": settings.reranker_model,
            "qdrant_collection": settings.qdrant_collection,
            "tenant_id": settings.tenant_id,
            "locale": settings.locale,
        },
        "initialization_ms": initialization_ms,
        "metrics": asdict(metrics),
        "queries": records,
        "limitations": [
            "Synthetic, small FAQ corpus; results do not establish production quality.",
            "Latency excludes construction/warmup, transport, privacy, cache and graph overhead.",
            "Qdrant needs an ingested corpus matching local data, tenant and locale; "
            "remote vector-store contents are not hashed.",
            "Retriever scores and model confidence are not calibrated probabilities.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{metrics.name}: {metrics.relevant_count} relevant + "
        f"{metrics.ood_count} OOD; {metrics.repeats} repeat(s)"
    )
    print(
        f"Hit@1={metrics.hit_at_1:.1%} Hit@3={metrics.hit_at_3:.1%} "
        f"MRR@{metrics.mrr_cutoff}={metrics.mrr:.4f}"
    )
    print(
        f"OOD false acceptance={metrics.ood_false_accept_rate:.1%}; "
        f"latency p50={metrics.latency_p50_ms:.2f}ms p95={metrics.latency_p95_ms:.2f}ms"
    )
    print(f"Report: {args.output}")
    if args.mlflow_tracking_uri:
        log_mlflow(report, args.output, args.mlflow_tracking_uri)


if __name__ == "__main__":
    main()
