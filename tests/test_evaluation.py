from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from app.services.retrieval.base import RetrievalHit
from scripts.evaluate_ragas import build_samples, judge_samples
from scripts.evaluate_ragas import main as ragas_main
from scripts.evaluate_retrieval import (
    evaluate_strategy,
    hit_at_k,
    load_dataset,
    percentile,
    reciprocal_rank,
    validate_labels,
)


def test_retrieval_metrics_use_ranks_and_ood_denominator(knowledge_base):
    entries = knowledge_base.entries
    first, target = entries[:2]

    class RankedRetriever:
        def retrieve(self, query, top_k=3):
            if query == "miss":
                return []
            if query == "ood":
                return [RetrievalHit(first, 1.0, 0.5)]
            return [RetrievalHit(first, 2.0, 0.6), RetrievalHit(target, 1.0, 0.5)]

    dataset = {
        "relevant_queries": [
            {"id": "a", "query": "ranked", "expected_entry_ids": [target.id]},
            {"id": "b", "query": "miss", "expected_entry_ids": [target.id]},
        ],
        "irrelevant_queries": [{"id": "c", "query": "ood"}, {"id": "d", "query": "miss"}],
    }
    metrics, rows = evaluate_strategy(
        "fake", RankedRetriever(), dataset, warmup_query=None, repeats=2
    )
    assert metrics.hit_at_1 == 0
    assert metrics.hit_at_3 == 0.5
    assert metrics.mrr == 0.25
    assert metrics.ood_false_accept_rate == 0.5
    assert metrics.false_accept_count == 2
    assert len(rows) == 8
    assert metrics.latency_p95_ms >= metrics.latency_p50_ms >= 0


def test_multiple_relevant_labels_and_percentile(knowledge_base):
    hits = [RetrievalHit(entry, 1.0, 0.5) for entry in knowledge_base.entries[:3]]
    expected = [hits[1].entry.id, hits[2].entry.id]
    assert not hit_at_k(hits, expected, 1)
    assert hit_at_k(hits, expected, 3)
    assert reciprocal_rank(hits, expected) == 0.5
    assert reciprocal_rank([], expected) == 0
    assert percentile([40, 10, 30, 20], 50) == 25
    assert percentile([1], 95) == 1


def test_evaluation_labels_must_exist(knowledge_base):
    with pytest.raises(ValueError, match="unknown FAQ"):
        validate_labels({"relevant_queries": [{"expected_entry_ids": ["missing"]}]}, knowledge_base)


def test_duplicate_dataset_ids_are_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "relevant_queries": [{"id": "a", "query": "a", "expected_entry_ids": ["x"]}],
                "irrelevant_queries": [{"id": "a", "query": "b"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        load_dataset(path)


def test_ragas_export_contains_actual_retrieval_and_reference(knowledge_base):
    target = knowledge_base.entries[0]

    class WrongRetriever:
        def retrieve(self, query, top_k=3):
            return [RetrievalHit(knowledge_base.entries[1], 1.0, 0.5)] if query == "hit" else []

    dataset = {
        "relevant_queries": [
            {"id": "a", "query": "hit", "expected_entry_ids": [target.id]},
            {"id": "b", "query": "miss", "expected_entry_ids": [target.id]},
        ]
    }
    samples = build_samples(dataset, knowledge_base, WrongRetriever())
    assert samples[0]["response"] == knowledge_base.entries[1].answer
    assert samples[0]["reference"] == target.answer
    assert samples[0]["response"] != samples[0]["reference"]
    assert samples[1]["response"] == ""
    assert samples[1]["fallback"] is True
    assert samples[1]["retrieved_contexts"] == []


def test_judge_requires_transmission_opt_in_before_creating_outputs(monkeypatch, tmp_path):
    output = tmp_path / "judge.json"
    monkeypatch.setattr(sys, "argv", ["evaluate_ragas", "--judge", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        ragas_main()
    assert error.value.code == 2
    assert not output.exists()


def test_ragas_partial_failures_are_not_counted_as_scores(monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Metric:
        def __init__(self, **kwargs):
            pass

        async def ascore(self, **kwargs):
            if kwargs["user_input"] == "failed":
                raise ValueError("provider details must not enter report")
            return SimpleNamespace(value=0.5)

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=Client))
    monkeypatch.setitem(
        sys.modules, "ragas.llms", SimpleNamespace(llm_factory=lambda *a, **k: None)
    )
    monkeypatch.setitem(
        sys.modules, "ragas.metrics.collections", SimpleNamespace(Faithfulness=Metric)
    )
    samples = [
        {
            "id": str(index),
            "user_input": query,
            "response": "synthetic answer",
            "retrieved_contexts": ["synthetic context"],
            "fallback": fallback,
        }
        for index, (query, fallback) in enumerate(
            [("good", False), ("failed", False), ("empty", True)]
        )
    ]
    report = asyncio.run(judge_samples(samples, "mock-judge"))
    assert report["status"] == "partial_failure"
    assert report["scored_count"] == report["skipped_count"] == report["error_count"] == 1
    assert report["mean_faithfulness"] == 0.5
    assert report["rows"][1] == {"id": "1", "status": "error", "error_type": "ValueError"}
