# TelcoAI development roadmap

This roadmap is for the independent DemoTel portfolio project. DemoTel, its content, billing records, and support actions are fictional. The work demonstrates engineering decisions and measured behavior; it does not claim access to an operator or production customer data.

## Recommended retrieval choices

The project already implements keyword search, local multilingual semantic search, Qdrant dense-plus-BM25 hybrid search with RRF, and optional BGE re-ranking. There is no need to build another standalone semantic-search chatbot.

- **Semantic search** is useful when a customer describes an FAQ in different words.
- **BM25 keyword search** helps with exact product names, terms, and identifiers.
- **Hybrid search** combines both candidate lists; the existing Qdrant integration fuses them with RRF.
- **Re-ranking** can reorder a smaller candidate list by query relevance, at additional model and latency cost.

Which option works best for DemoTel must be measured against the same FAQ corpus and labeled questions. Keep the lightweight keyword mode available for an offline demo. Use the optional model-backed modes when their dependencies are installed and the benchmark justifies the extra cost.

## Step 1: compare search modes (v1 measured)

`data/evaluation/retrieval_holdout_v1.json` contains a new set of paraphrases, one for each of the 40 fictional FAQ records, and unsupported questions from both telecom and unrelated topics. Its labels are separate from `data/evaluation/retrieval_eval.json`, the current development set.

The existing benchmark accepts a dataset path, so the suite can be used without changing the retrieval implementation:

```bash
uv run --frozen --no-sync python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval_holdout_v1.json \
  --strategy keyword \
  --output artifacts/holdout-keyword.json
```

Run semantic retrieval after installing the optional model extra. Run hybrid retrieval with the existing local Qdrant evaluator. Compare Hit@1/3, MRR, unsupported-query false acceptance, latency, and individual failures. The current benchmark reports Hit@1/3, MRR, false acceptance, latency percentiles, and per-query results. The guarded workflow evaluator separately reports relevant-query fallbacks, unsupported answers, and source agreement.

The v1 labels were first evaluated with unchanged retrieval configuration. They exposed unsafe FAQ answers for live/account-specific requests, so v1 was subsequently used to check a new policy guard. **v1 is now an exploratory regression set, not an untouched final holdout.** Author a new independently labeled v2 before claiming an unbiased final comparison. The reports contain dataset and corpus hashes; the [comparison](holdout-comparison-v1.json) refuses to combine mismatched inputs. These synthetic examples are portfolio measurements, not production accuracy claims.

The existing development run reports keyword Hit@1 of 59.3% and local semantic Hit@1 of 74.1% on its current small synthetic set. These numbers help identify a comparison to run; they do not choose a production default or predict results on the new suite. The old hybrid score uses a smaller corpus and a different dataset, so it is not directly comparable.

## Step 2: fix the failures found by evaluation

The first v1 keyword workflow answered 8/20 unsupported queries. A general rule now routes requests for live status, account balances and write operations to handoff before FAQ retrieval. The [before](holdout-keyword-workflow-evaluation.json) and [after](holdout-keyword-workflow-after-guard.json) reports show 8/20 to 0/20 on v1, with 23/40 relevant source hits in both runs. This is a targeted safety regression result, not independent test accuracy. Search quality and the ten relevant fallbacks still need development-set analysis.

Review individual failed queries before changing search. Group errors into wrong FAQ selection, reasonable top-three but wrong first result, unsupported-query false acceptance, and unnecessary fallback. Choose the smallest correction for each group: improve FAQ question/keyword coverage, normalize Turkish spelling, adjust dense thresholds, change candidate counts, or try the existing reranker. Keep a short before/after report with the same development dataset and configuration.

Add evaluation coverage for both search and the complete guarded workflow. Search ranking alone does not show whether the assistant abstains when it lacks account-specific or current information. Preserve an explicit unsupported-query group and inspect every false answer.

## Step 3: demonstrate one safe telecom action

Implemented as separate synthetic demo endpoints and a chat UI action. The fixture includes only fictional account IDs, codes and bill amounts. The service validates a demo code, scopes bill and ticket reads to that account, stores a prepared draft, and requires an explicit confirmation with an idempotency key before writing a SQLite ticket. The reference can be looked up after restart. Missing records, wrong account, expired/duplicate confirmation and database timeouts have defined responses. `compose.yaml` mounts a named volume for ticket persistence. The public FAQ path does not read these records.

Add a small local mock API and one customer-support journey, such as inspecting a fictional bill and preparing a support ticket. Keep public FAQ questions on the RAG path. Read account-specific facts from the mock API, validate access and inputs, and require confirmation before a write action. Store only synthetic records.

The demo should show the source or API result, the user's approval step, and a durable result reference. Handle missing records, authorization failure, timeouts, and duplicate requests. Do not describe this mock as a real billing or CRM integration.

## Step 4: show service behavior clearly

The comparison reports and existing architecture diagram are checked in. A short recording and independently authored v2 set remain open portfolio deliverables.

Use the existing Docker, Compose, and CI setup to produce a repeatable demo. Add an evaluation report for the selected configuration, a short architecture diagram, and a brief recording of the search comparison and safe support journey. Report model downloads, latency, and fallbacks honestly. Keep paid LLM judging opt-in.

Before external customer data or a real operator API is considered, the project needs verified user identity and authorization, tenant isolation, TLS and rate limits, reviewed privacy and retention behavior, stronger PII validation, and operational monitoring. The current project is a synthetic portfolio demo.

## Later complementary portfolio work

After the two main demos are clearer, build a small Turkish support-intent classification experiment: compare a TF-IDF baseline with a fine-tuned Transformer, use a separate evaluation split, and publish class-level errors. It would add supervised NLP evidence alongside TelcoAI's retrieval work. The existing Whisper project is speech recognition; describe it as ASR and report WER only where the actual measured values and evaluation split are available.
