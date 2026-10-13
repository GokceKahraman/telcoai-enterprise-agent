#!/usr/bin/env python3
"""Export synthetic FAQ evaluation inputs; run a paid Ragas judge only with opt-in."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.base import Retriever
from app.services.retrieval.factory import build_retriever
from app.services.retrieval.semantic_retriever import DOCUMENT_REPRESENTATION_VERSION
from scripts.evaluate_retrieval import load_dataset, sha256_file, validate_labels


def build_samples(
    dataset: dict[str, Any], knowledge_base: KnowledgeBase, retriever: Retriever, top_k: int = 3
) -> list[dict[str, Any]]:
    """Measure extracted retrieval answers, not a hypothetical generated answer."""
    samples = []
    for item in dataset["relevant_queries"]:
        hits = retriever.retrieve(item["query"], top_k=top_k)
        references = [
            knowledge_base.get_by_id(identifier) for identifier in item["expected_entry_ids"]
        ]
        samples.append(
            {
                "id": item["id"],
                "user_input": item["query"],
                "response": hits[0].entry.answer if hits else "",
                "retrieved_contexts": [f"{hit.entry.question}\n{hit.entry.answer}" for hit in hits],
                "reference": "\n".join(entry.answer for entry in references if entry is not None),
                "retrieved_entry_ids": [hit.entry.id for hit in hits],
                "expected_entry_ids": item["expected_entry_ids"],
                "fallback": not bool(hits),
            }
        )
    return samples


async def judge_samples(samples: list[dict[str, Any]], model: str) -> dict[str, Any]:
    # This is the current collections API; no paid client is created by export mode.
    try:
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import Faithfulness
    except ImportError as exc:
        raise RuntimeError("Ragas judging requires: uv sync --extra eval") from exc
    rows: list[dict[str, Any]] = []
    async with AsyncOpenAI(timeout=45.0, max_retries=1) as client:
        metric = Faithfulness(llm=llm_factory(model, client=client))
        for sample in samples:
            if sample["fallback"]:
                rows.append(
                    {"id": sample["id"], "status": "skipped", "reason": "no retrieved context"}
                )
                continue
            try:
                result = await metric.ascore(
                    user_input=sample["user_input"],
                    response=sample["response"],
                    retrieved_contexts=sample["retrieved_contexts"],
                )
                score = float(result.value)
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError("Judge returned an invalid faithfulness score")
                rows.append({"id": sample["id"], "status": "scored", "faithfulness": score})
            except Exception as exc:
                # Preserve completed rows without printing provider response/credentials.
                rows.append(
                    {"id": sample["id"], "status": "error", "error_type": type(exc).__name__}
                )
    scores = [row["faithfulness"] for row in rows if row["status"] == "scored"]
    errors = sum(row["status"] == "error" for row in rows)
    return {
        "metric": "faithfulness",
        "judge_model": model,
        "status": "partial_failure" if errors else "completed",
        "requested_count": len(samples),
        "scored_count": len(scores),
        "skipped_count": sum(row["status"] == "skipped" for row in rows),
        "error_count": errors,
        "mean_faithfulness": statistics.mean(scores) if scores else None,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/evaluation/retrieval_eval.json"
    )
    parser.add_argument("--knowledge-base", type=Path, default=ROOT / "data/knowledge_base.json")
    parser.add_argument(
        "--strategy", choices=("keyword", "semantic", "qdrant_hybrid"), default="keyword"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/ragas-inputs.json")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument(
        "--allow-external-judge",
        action="store_true",
        help="Authorize external transmission of selected inputs and paid judge API calls",
    )
    parser.add_argument(
        "--judge-model", help="Required with --judge; choose a model available to your account"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=5,
        help="Maximum inputs; a metric may make multiple API calls per input",
    )
    parser.add_argument(
        "--judge-output", type=Path, default=ROOT / "artifacts/ragas-evaluation.json"
    )
    args = parser.parse_args()
    if args.max_samples < 1:
        parser.error("--max-samples must be positive")
    if args.judge:
        if not args.allow_external_judge:
            parser.error(
                "--judge requires --allow-external-judge; selected inputs leave this machine "
                "and API costs may apply"
            )
        if not args.judge_model:
            parser.error("--judge requires an explicit --judge-model")
        if not os.getenv("OPENAI_API_KEY"):
            parser.error("--judge requires OPENAI_API_KEY")
    dataset = load_dataset(args.dataset)
    updates: dict[str, Any] = {"retrieval_strategy": args.strategy}
    if args.strategy != "qdrant_hybrid":
        updates["reranker_enabled"] = False
    settings = get_settings().model_copy(update=updates)
    knowledge_base = KnowledgeBase(args.knowledge_base).scoped(settings.tenant_id, settings.locale)
    validate_labels(dataset, knowledge_base)
    retriever = build_retriever(settings, knowledge_base)
    try:
        samples = build_samples(dataset, knowledge_base, retriever)
    finally:
        close = getattr(retriever, "close", None)
        if close:
            close()
    export = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "response_mode": "extractive_retrieval",
        "data_origin": (
            "bundled synthetic FAQ benchmark; no live customer/session data"
            if args.dataset.resolve() == (ROOT / "data/evaluation/retrieval_eval.json").resolve()
            and args.knowledge_base.resolve() == (ROOT / "data/knowledge_base.json").resolve()
            else "user-provided files; verify privacy and provenance before external judging"
        ),
        "strategy": args.strategy,
        "document_representation_version": DOCUMENT_REPRESENTATION_VERSION,
        "dataset_sha256": sha256_file(args.dataset),
        "corpus_sha256": sha256_file(args.knowledge_base),
        "samples": samples,
        "limitations": [
            "Faithfulness measures context support, not selection of the correct FAQ.",
            "Answers come from the first FAQ; LangGraph and LLM generation are not evaluated.",
            "Judge agreement/Turkish performance need human review; export mode creates no scores.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Exported {len(export['samples'])} synthetic inputs: {args.output}")
    if not args.judge:
        print("Export only; no judge was called and no Ragas score was produced.")
        return
    judged = asyncio.run(judge_samples(export["samples"][: args.max_samples], args.judge_model))
    judged.update(
        {
            "created_at": datetime.now(UTC).isoformat(),
            "dataset_sha256": export["dataset_sha256"],
            "corpus_sha256": export["corpus_sha256"],
            "response_mode": export["response_mode"],
        }
    )
    args.judge_output.parent.mkdir(parents=True, exist_ok=True)
    args.judge_output.write_text(
        json.dumps(judged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Judge report: {args.judge_output}; "
        f"scored={judged['scored_count']} errors={judged['error_count']}"
    )
    if judged["error_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
