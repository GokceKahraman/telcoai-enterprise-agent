# Evaluation methodology

Evaluation reports are evidence about a particular run, not a claim of production quality. The expanded development set has 54 relevant paraphrases and 10 unrelated queries across the 40-entry fictional FAQ corpus. All labels can be inspected in `data/evaluation/retrieval_eval.json`. It is not a held-out test set.

## Offline retrieval benchmark

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
