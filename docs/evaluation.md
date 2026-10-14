# Evaluation methodology

Evaluation reports are evidence about a particular run, not a claim of production quality. The expanded development set has 54 relevant paraphrases and 10 unrelated queries across the 40-entry fictional FAQ corpus. All labels can be inspected in `data/evaluation/retrieval_eval.json`. It is not a held-out test set.

## v1 reserved set, now exploratory

`data/evaluation/retrieval_holdout_v1.json` has 40 relevant and 20 unsupported synthetic queries. The corpus and dataset hashes match across the checked-in [keyword](holdout-keyword-evaluation.json), [dense](holdout-semantic-evaluation.json) and [local hybrid](holdout-hybrid-evaluation.json) reports. The [comparison JSON](holdout-comparison-v1.json) lists per-query failures. `scripts/compare_retrieval.py` rejects reports with different input hashes or label counts.

| Raw retrieval | Hit@1 | Hit@3 | Unsupported accepted |
| --- | ---: | ---: | ---: |
| Keyword | 80% | 87.5% | 60% |
| Dense | 77.5% | 82.5% | 35% |
| Local Qdrant hybrid | 85% | 92.5% | 90% |

The guarded keyword workflow initially answered 8/20 unsupported requests. After a broad account/live-information policy guard, the [keyword](holdout-keyword-workflow-after-guard.json), [dense](holdout-semantic-workflow-evaluation.json) and [hybrid](holdout-hybrid-workflow-evaluation.json) workflows answered 0/20; relevant source Hit@1 was 57.5%, 60% and 65% respectively. Ten relevant queries fell back in the keyword workflow. The v1 queries were inspected during this safety fix, so these after-guard results are regression evidence and **not a fresh held-out estimate**. Create v2 independently before claiming final generalization. Local timings exclude network service latency; no remote Qdrant index behavior or real customer data is measured.

### Known regression replay (v1 is not an independent test)

The Turkish search-tuning change caused a known v1 workflow regression: unsupported query `x17`, “Yeni televizyon paketimde hangi spor kanalları var?”, was answered from `pkg-001` (“Ev internet paketleriniz nelerdir?”). The broad `paket` support stem admitted a TV subscription request, and suffix-aware retrieval matched `paketimde` to the generic `paket` FAQ keyword strongly enough to pass the 2.0 threshold. The narrow policy correction explicitly rejects TV/channel package requests before applying generic telecom terms; ordinary internet-package questions still use the FAQ path. V1 was replayed to reproduce and verify this one regression only. Its 1/20 before-fix and post-fix regression-check counts must not be presented as final success metrics or independent validation; v1 was already inspected and influenced policy changes. Author a fresh v2 set before reporting generalization.

## Offline retrieval benchmark

For a same-input comparison across keyword, dense semantic, BM25 sparse, Qdrant dense+BM25 hybrid and optional BGE reranking, run:

```bash
uv sync --frozen --extra dev --extra semantic
uv run --frozen --no-sync python scripts/evaluate_search_matrix.py
```

The [comparison notes](retrieval-comparison.md) summarize the current development measurements and show representative errors. The JSON report records matching data hashes and per-query rankings. If BGE weights are unavailable, the script records the skipped reranker and still completes the other methods. This development set has guided tuning; it is not independent validation. The v1 dataset is only for replaying the known policy regression, and a new v2 is needed for unbiased validation.

```bash
uv sync --frozen --extra dev
uv run --frozen --no-sync python scripts/evaluate_retrieval.py
```

Keyword is the CLI default regardless of the application’s selected retrieval strategy. For model/service comparisons, install the semantic extra, ingest the current corpus for Qdrant and select an explicit strategy:

```bash
uv sync --frozen --extra dev --extra semantic
uv run --frozen --no-sync python scripts/evaluate_retrieval.py --strategy semantic --semantic-threshold 0.45
uv run --frozen --no-sync python scripts/evaluate_retrieval.py --strategy qdrant_hybrid --repeats 3 --output artifacts/hybrid-evaluation.json
```

The evaluator rejects duplicate query IDs, empty query/label groups and references to nonexistent FAQ IDs. It includes every query in each repeat.

| Metric | Definition |
| --- | --- |
| Hit@1 / Hit@3 | Fraction of relevant trials with any expected FAQ ID in the first 1 / 3 results |
| MRR@k | Mean of `1 / rank` of the first expected ID; zero when absent within the configured cutoff (default 10) |
| OOD false acceptance | Fraction of unrelated trials returning any result; lower is better |
| Latency p50 / p95 | Linear-interpolated percentiles of `retrieve()` timings for relevant and unrelated queries |

Each run measures retriever initialization separately and performs one warmup query. Latency excludes the HTTP/gRPC transport, LangGraph, privacy, response generation and cache. It is an in-process measurement, affected by hardware, model warmup, database state and scheduling. Repeated trials can improve timing estimates but do not create independent new labeled samples.

JSON reports include timestamps, runtime, corpus/dataset SHA-256 hashes, public retrieval configuration, counts, per-query retrieved IDs/scores and limitations. Compare rankings and errors alongside aggregates. Do not compare different thresholds, candidate counts, re-ranking modes or corpus/model versions as though they were the same experiment. Remote Qdrant contents must match the recorded corpus; the report does not hash the remote vector store.

## Recorded development-set results

| Raw retriever | Hit@1 | Hit@3 | MRR@10 | OOD false acceptance | Report |
| --- | --- | --- | --- | --- | --- |
| Keyword, expanded 40-record corpus | 59.3% | 81.5% | 0.702 | 20% | [JSON](keyword-expanded-corpus-evaluation.json) |
| Local dense, expanded 40-record corpus | 74.1% | 85.2% | 0.804 | 10% | [JSON](semantic-expanded-corpus-evaluation.json) |
| Keyword, earlier 11-record corpus | 88% | 96% | 0.930 | 10% | [JSON](evaluation-baseline.json) |
| Local dense, earlier corpus | 92% | 92% | 0.920 | 10% | [JSON](semantic-evaluation.json) |
| Dense + BM25/RRF, earlier corpus | 96% | 100% | 0.973 | 50% | [JSON](hybrid-evaluation.json) |

The three earlier reports use the same 25 relevant/10 OOD labels and an earlier corpus; they are preserved for historical comparison and do not describe the expanded corpus. The expanded dense run used cached MiniLM weights. Local mode does not exercise remote payload indexes, HNSW, server latency or BGE re-ranking. The expanded development scores show that broadening the FAQ corpus created more retrieval ambiguity; the expanded semantic model ranked the expected answer first on 40/54 queries. Improve or re-label the corpus with a separate holdout before presenting a quality claim. Earlier hybrid results also expose a limitation of rank fusion: candidate retrieval alone does not decide whether a query belongs to the support domain.

## Keyword retrieval tuning on the development set

On 2026-10-14, Turkish FAQ aliases and suffix-aware token matching were adjusted using the 54-query development set. At the original threshold of 1.0, Hit@1/Hit@3 were 59.3%/77.8%, MRR@10 was 0.700 and raw OOD false acceptance was 20%. The changes at threshold 1.0 reached 87.0%/98.1% Hit@1/Hit@3 but raised raw OOD false acceptance to 30% ([report](keyword-dev-after-update-evaluation.json)). Raising `TELCOAI_MIN_MATCH_SCORE` to 2.0 preserved those retrieval scores, reduced raw OOD false acceptance to 10%, and gave MRR@10 of 0.927. The pre-change [report](keyword-dev-before-update-evaluation.json) and current [threshold-2 report](keyword-dev-threshold-2-evaluation.json) preserve run details and input hashes.

The complete keyword workflow at threshold 2.0 measured source Hit@1 **85.2% (46/54)**, unsupported false answers **0/10**, and exact grounding for **53/53** sourced responses ([report](keyword-workflow-threshold-2-evaluation.json)). Threshold 1.0 produced the same workflow source Hit@1 on this set, so 2.0 reduces weak raw matches without losing measured relevant answers here. These examples were used to tune the system and are development evidence only. The explored v1 set is not independent validation; keep its regression caveat and author a new v2 before making generalization claims.

## Guarded workflow evaluation

```bash
uv run --frozen --no-sync python scripts/evaluate_workflow.py
# Optional: uses the selected semantic model; install the semantic extra first.
uv run --frozen --no-sync python scripts/evaluate_workflow.py --strategy semantic
```

This evaluator measures `ChatService` including input masking, domain/policy routing, graph execution, retrieval and output validation. Each query gets a fresh service, session and memory cache over the warmed shared retriever. LLM generation, external tracing, Redis and re-ranking are disabled. Latency excludes graph construction, initial warmup and HTTP/gRPC transport. The reports therefore measure extractive grounded workflow behavior, not generated conversational answer quality.

The latest [expanded keyword workflow report](keyword-expanded-workflow-evaluation.json) records source Hit@1 **50% (27/54)**, OOD false answers **0/10**, 9 relevant fallbacks and exact grounding for **45/45** sourced responses. This is a useful signal that the expanded keyword baseline needs more retrieval tuning; the guarded workflow declines unsupported questions rather than inventing an account answer. The older committed keyword and hybrid reports below describe the earlier 25-query corpus and dataset. Their abstention outcomes apply only to the ten bundled OOD examples. Exact agreement with a cited FAQ cannot establish that the citation is the right answer. Re-run `scripts/evaluate_workflow.py` to measure an alternative strategy through the guarded response workflow.

To reproduce the local Qdrant measurements without a server (first run downloads model assets):

```bash
uv sync --frozen --extra dev --extra semantic
uv run --frozen --no-sync python scripts/evaluate_local_hybrid.py \
  --output artifacts/hybrid-evaluation.json \
  --workflow-output artifacts/hybrid-workflow-evaluation.json
```

`source_hit_at_1` counts expected source IDs on non-fallback relevant responses. `ood_false_answer_rate` counts OOD responses with a source and `fallback=false`. `source_grounding_rate` checks that the source exists and the returned answer exactly equals its masked authoritative FAQ answer; unsourced responses are excluded and the numerator/denominator are explicit. This separates retrieval relevance, answer provenance and policy abstention.

## Development changes and before/after evidence

[The change audit](retrieval-development-changes.json) records corpus hashes, unchanged labels/thresholds and the document representation version. The technical FAQ’s supported scope was clarified to include both slow connections and dropouts, with relevant aliases; its existing troubleshooting answer stayed unchanged. Dense/BM25 document text now consists of the question and curated keywords, while the authoritative answer stays in the payload. A Turkish dotted/dotless-I normalization issue was also corrected.

The [original keyword baseline](keyword-original-corpus-evaluation.json), [original dense report](semantic-full-document-evaluation.json), [original hybrid report](hybrid-full-document-evaluation.json) and [representation comparison](document-representation-evaluation.json) are retained. After results reflect multiple intentional development changes and a changed corpus hash, so do not attribute all gains to one component. Improvements on this same small set can overfit it; a new held-out set is the next quality test. Retrieval representation/model changes require a new Qdrant collection and explicit re-ingestion before switching the service.

## MLflow

```bash
uv sync --frozen --extra dev --extra eval
uv run --frozen --no-sync python scripts/evaluate_retrieval.py \
  --mlflow-tracking-uri sqlite:///artifacts/mlflow.db
uv run --frozen --no-sync mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db --host 127.0.0.1
```

The script logs numeric metrics, selected public configuration, data hashes and the JSON report to experiment `telcoai-retrieval`. Supplying a tracking URI is an explicit opt-in; pointing it at a remote server transmits those artifacts. Credentials are never logged as experiment parameters. MLflow is an optional dependency and does not run in the HTTP request path.

## Ragas input export and optional judge

```bash
# No judge API call; optional eval dependencies are unnecessary for export.
uv run --frozen --no-sync python scripts/evaluate_ragas.py
```

The export contains each relevant synthetic query, its actual retrieved contexts, the answer copied from the highest-ranked FAQ, a reference answer built from the labels and fallback metadata. `response_mode=extractive_retrieval` identifies exactly what is measured. It is not an evaluation of the optional LLM generation path or the entire graph.

After reviewing `artifacts/ragas-inputs.json`, paid judging is a deliberate action:

```bash
uv sync --frozen --extra dev --extra eval
# Set OPENAI_API_KEY securely in your local environment and choose a supported judge model.
uv run --frozen --no-sync python scripts/evaluate_ragas.py \
  --judge --allow-external-judge --judge-model YOUR_JUDGE_MODEL --max-samples 5
```

The adapter uses Ragas’ [collections-based Faithfulness API](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/) and its [LLM factory](https://docs.ragas.io/en/stable/references/llms/). Faithfulness tests whether answer claims are supported by retrieved context. A faithfully copied **wrong FAQ answer** can score highly: judge metrics complement ID-based retrieval labels and human review. Turkish-language judge agreement has not been established by this repository.

`--max-samples` caps selected inputs, not API calls or money. A faithfulness evaluation can make multiple judge calls per input. Empty-context fallbacks are recorded as skipped; provider/parse errors are recorded individually and cause a nonzero exit after exporting the partial report. The mean uses only successful scores and includes the successful/skipped/error denominators. Export-only mode never produces fabricated judge scores.

## Tests, integration and next dataset

Offline tests use deterministic/mock embeddings and local/fake service adapters. They verify rank/metric arithmetic, privacy behavior, workflow decisions, storage and API contracts without inference keys. Service/model integration tests require their explicit opt-in settings and available services. A mocked service test does not validate a deployed database or external provider.

For a stronger portfolio follow-up, separate development and held-out sets, expand Turkish spelling/paraphrases and adversarial/OOD coverage, test tenant/category isolation, label expected handoff/abstention, measure PII false positives/negatives, then run load tests with concurrency and compare uncached/cached response latency. Threshold tuning on this small benchmark risks overfitting.
