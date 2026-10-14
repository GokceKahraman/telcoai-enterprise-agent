# TelcoAI development roadmap

This roadmap is for the independent DemoTel portfolio project. DemoTel, its content, billing records, and support actions are fictional. The work demonstrates engineering decisions and measured behavior; it does not claim access to an operator or production customer data.

## Recommended retrieval choices

The project already implements keyword search, local multilingual semantic search, Qdrant dense-plus-BM25 hybrid search with RRF, and optional BGE re-ranking. There is no need to build another standalone semantic-search chatbot.

- **Semantic search** is useful when a customer describes an FAQ in different words.
- **BM25 keyword search** helps with exact product names, terms, and identifiers.
- **Hybrid search** combines both candidate lists; the existing Qdrant integration fuses them with RRF.
- **Re-ranking** can reorder a smaller candidate list by query relevance, at additional model and latency cost.

Which option works best for DemoTel must be measured against the same FAQ corpus and labeled questions. Keep the lightweight keyword mode available for an offline demo. Use the optional model-backed modes when their dependencies are installed and the benchmark justifies the extra cost.

## Step 1: compare search modes (development matrix measured; v1 regression only)

`data/evaluation/retrieval_holdout_v1.json` contains a new set of paraphrases, one for each of the 40 fictional FAQ records, and unsupported questions from both telecom and unrelated topics. Its labels are separate from `data/evaluation/retrieval_eval.json`, the current development set.

The existing benchmark accepts a dataset path, so the suite can be used without changing the retrieval implementation:

```bash
uv run --frozen --no-sync python scripts/evaluate_retrieval.py \
  --dataset data/evaluation/retrieval_holdout_v1.json \
  --strategy keyword \
  --output artifacts/holdout-keyword.json
```

The [same-data development matrix](retrieval-comparison.md) compares keyword, dense semantic, BM25 sparse, and Qdrant dense+BM25 hybrid on one 54-relevant/10-unsupported dataset and one 40-entry corpus. It records Hit@1/3, MRR, unsupported acceptance, p50/p95 latency and every failure. The BGE reranker row is marked unmeasured because its weights were unavailable in the run environment. The [report JSON](search-matrix-development.json) includes matching dataset and corpus hashes. The guarded workflow evaluator separately reports relevant-query fallbacks, unsupported answers, and source agreement.

The v1 labels were first evaluated with unchanged retrieval configuration. They exposed unsafe FAQ answers for live/account-specific requests, so v1 was subsequently used to check a new policy guard. **v1 is now an exploratory regression set, not an untouched final holdout.** Author a new independently labeled v2 before claiming an unbiased final comparison. The reports contain dataset and corpus hashes; the [comparison](holdout-comparison-v1.json) refuses to combine mismatched inputs. These synthetic examples are portfolio measurements, not production accuracy claims.

After development-set tuning, the keyword baseline at threshold 2.0 reports Hit@1 87.0%, Hit@3 98.1%, MRR@10 0.927 and raw OOD false acceptance 10%. The complete guarded workflow reports source Hit@1 85.2%, 0/10 OOD false answers and exact grounding for 53/53 sourced responses. See the [evaluation evidence](evaluation.md#keyword-retrieval-tuning-on-the-development-set). These are development-set results, not a final generalization estimate.

## Step 2: fix the failures found by evaluation

The development-set pass added curated Turkish FAQ aliases, suffix-aware prefix matching, and a stricter keyword threshold. This raised raw keyword Hit@1 from 59.3% to 87.0% and reduced raw OOD acceptance from 20% to 10%; the complete guarded workflow kept OOD false answers at 0/10. These values were measured on the same development set used to guide the changes. The v1 policy fix remains regression evidence only. Keep inspecting individual failures and create v2 before claiming independent accuracy.

Review individual failed queries before changing search. Group errors into wrong FAQ selection, reasonable top-three but wrong first result, unsupported-query false acceptance, and unnecessary fallback. Choose the smallest correction for each group: improve FAQ question/keyword coverage, normalize Turkish spelling, adjust dense thresholds, change candidate counts, or try the existing reranker. Keep a short before/after report with the same development dataset and configuration.

Keep evaluation coverage for both search and the complete guarded workflow. Search ranking alone does not show whether the assistant abstains when it lacks account-specific or current information. Preserve an explicit unsupported-query group and inspect every false answer.

## Step 3: demonstrate one safe telecom action

Implemented as separate synthetic demo endpoints and a chat UI action. The fixture includes only fictional account IDs, codes and bill amounts. The service validates a demo code, scopes bill and ticket reads to that account, stores a prepared draft, and requires an explicit confirmation with an idempotency key before writing a SQLite ticket. The reference can be looked up after restart. Missing records, wrong account, expired/duplicate confirmation and database timeouts have defined responses. `compose.yaml` mounts a named volume for ticket persistence. The public FAQ path does not read these records.

## Step 4: show service behavior clearly

The search matrix, [error analysis](retrieval-comparison.md), [short demo narration](demo-narration-tr.md) and existing architecture diagram are checked in. A short recording, a completed reranker measurement and independently authored v2 set remain open portfolio deliverables.

Use the existing Docker, Compose, and CI setup to produce a repeatable demo. Add a brief recording of the search comparison and safe support journey. Report model downloads, latency, and fallbacks honestly. Keep paid LLM judging opt-in.

Before external customer data or a real operator API is considered, the project needs verified user identity and authorization, tenant isolation, TLS and rate limits, reviewed privacy and retention behavior, stronger PII validation, and operational monitoring. The current project is a synthetic portfolio demo.

## Later complementary portfolio work

After the two main demos are clearer, build a small Turkish support-intent classification experiment: compare a TF-IDF baseline with a fine-tuned Transformer, use a separate evaluation split, and publish class-level errors. It would add supervised NLP evidence alongside TelcoAI's retrieval work. The existing Whisper project is speech recognition; describe it as ASR and report WER only where the actual measured values and evaluation split are available.
