# TelcoAI development roadmap

This roadmap is for the independent DemoTel portfolio project. DemoTel, its content, billing records, and support actions are fictional. The work demonstrates engineering decisions and measured behavior; it does not claim access to an operator or production customer data.

## Recommended retrieval choices

The project already implements keyword search, local multilingual semantic search, Qdrant dense-plus-BM25 hybrid search with RRF, and optional BGE re-ranking. There is no need to build another standalone semantic-search chatbot.

- **Semantic search** is useful when a customer describes an FAQ in different words.
- **BM25 keyword search** helps with exact product names, terms, and identifiers.
- **Hybrid search** combines both candidate lists; the existing Qdrant integration fuses them with RRF.
- **Re-ranking** can reorder a smaller candidate list by query relevance, at additional model and latency cost.

Which option works best for DemoTel must be measured against the same FAQ corpus and labeled questions. Keep the lightweight keyword mode available for an offline demo. Use the optional model-backed modes when their dependencies are installed and the benchmark justifies the extra cost.

## Step 1: establish a reserved search comparison

`data/evaluation/retrieval_holdout_v1.json` contains a new set of paraphrases, one for each of the 40 fictional FAQ records, and unsupported questions from both telecom and unrelated topics. Its labels are separate from `data/evaluation/retrieval_eval.json`, the current development set.

The existing benchmark accepts a dataset path, so the suite can be used without changing the retrieval implementation:

```bash
uv run --frozen --no-sync python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval_holdout_v1.json \
  --strategy keyword \
  --output artifacts/holdout-keyword.json
```

Run semantic retrieval after installing the optional model extra. Run hybrid retrieval with the existing local Qdrant evaluator. Compare Hit@1/3, MRR, unsupported-query false acceptance, latency, and individual failures. The current benchmark reports Hit@1/3, MRR, false acceptance, latency percentiles, and per-query results. The guarded workflow evaluator separately reports relevant-query fallbacks, unsupported answers, and source agreement.

The holdout is reserved for comparison after choices are settled. Tune thresholds, aliases, and document representation on the development set. Record corpus and dataset hashes with each report, then evaluate the frozen holdout once. If the holdout is later used to tune behavior, version a new holdout before presenting a final comparison. These are synthetic, manually labeled examples; results remain portfolio measurements, not production accuracy claims.

The existing development run reports keyword Hit@1 of 59.3% and local semantic Hit@1 of 74.1% on its current small synthetic set. These numbers help identify a comparison to run; they do not choose a production default or predict results on the new suite. The old hybrid score uses a smaller corpus and a different dataset, so it is not directly comparable.

## Step 2: fix the failures found by evaluation

Review individual failed queries before changing search. Group errors into wrong FAQ selection, reasonable top-three but wrong first result, unsupported-query false acceptance, and unnecessary fallback. Choose the smallest correction for each group: improve FAQ question/keyword coverage, normalize Turkish spelling, adjust dense thresholds, change candidate counts, or try the existing reranker. Keep a short before/after report with the same development dataset and configuration.

Add evaluation coverage for both search and the complete guarded workflow. Search ranking alone does not show whether the assistant abstains when it lacks account-specific or current information. Preserve an explicit unsupported-query group and inspect every false answer.

## Step 3: demonstrate one safe telecom action

Add a small local mock API and one customer-support journey, such as inspecting a fictional bill and preparing a support ticket. Keep public FAQ questions on the RAG path. Read account-specific facts from the mock API, validate access and inputs, and require confirmation before a write action. Store only synthetic records.

The demo should show the source or API result, the user's approval step, and a durable result reference. Handle missing records, authorization failure, timeouts, and duplicate requests. Do not describe this mock as a real billing or CRM integration.

## Step 4: show service behavior clearly

Use the existing Docker, Compose, and CI setup to produce a repeatable demo. Add an evaluation report for the selected configuration, a short architecture diagram, and a brief recording of the search comparison and safe support journey. Report model downloads, latency, and fallbacks honestly. Keep paid LLM judging opt-in.

Before external customer data or a real operator API is considered, the project needs verified user identity and authorization, tenant isolation, TLS and rate limits, reviewed privacy and retention behavior, stronger PII validation, and operational monitoring. The current project is a synthetic portfolio demo.

## Later complementary portfolio work

After the two main demos are clearer, build a small Turkish support-intent classification experiment: compare a TF-IDF baseline with a fine-tuned Transformer, use a separate evaluation split, and publish class-level errors. It would add supervised NLP evidence alongside TelcoAI's retrieval work. The existing Whisper project is speech recognition; describe it as ASR and report WER only where the actual measured values and evaluation split are available.
