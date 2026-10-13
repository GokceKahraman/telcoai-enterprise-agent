from __future__ import annotations

from types import SimpleNamespace

from scripts.evaluate_workflow import evaluate_workflow


def test_workflow_evaluation_separates_relevance_grounding_and_false_answers(knowledge_base):
    target, wrong = knowledge_base.entries[:2]
    responses = {
        "correct": (target.id, target.answer, False, False),
        "invented": (target.id, "An unsupported account detail", False, False),
        "wrong_ood": (wrong.id, wrong.answer, False, False),
        "abstain": (None, "Unable to answer", True, True),
    }
    services = []

    class Service:
        def __init__(self):
            self.calls = []
            services.append(self)

        def reply(self, query):
            self.calls.append(query)
            entry_id, answer, fallback, handoff = responses[query]
            return SimpleNamespace(
                source=SimpleNamespace(entry_id=entry_id) if entry_id else None,
                answer=answer,
                fallback=fallback,
                handoff=handoff,
                cache_hit=False,
                steps=["test"],
            )

    dataset = {
        "relevant_queries": [
            {"id": "r1", "query": "correct", "expected_entry_ids": [target.id]},
            {"id": "r2", "query": "invented", "expected_entry_ids": [target.id]},
        ],
        "irrelevant_queries": [
            {"id": "o1", "query": "wrong_ood"},
            {"id": "o2", "query": "abstain"},
        ],
    }
    metrics, rows = evaluate_workflow(Service, knowledge_base, dataset, repeats=2)
    assert len(services) == len(rows) == 8
    assert all(len(service.calls) == 1 for service in services)
    assert metrics["source_hit_at_1"] == 1
    assert metrics["ood_false_answer_rate"] == 0.5
    assert metrics["source_grounding_rate"] == 2 / 3
    assert metrics["grounding_failure_count"] == 2
    assert metrics["fallback_count"] == metrics["handoff_count"] == 2
    assert metrics["relevant_fallback_count"] == 0
    assert metrics["ood_fallback_count"] == 2
    assert rows[1]["grounded"] is False
    assert rows[3]["grounded"] is None
