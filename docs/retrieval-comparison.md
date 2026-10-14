# Retrieval method comparison

## Scope and method

This is a reproducible **development-set** comparison for the fictional 40-entry FAQ corpus. Every method uses the same 54 relevant and 10 unsupported questions, top-10 cutoff, tenant/locale scope, FAQ labels, and report schema. The exact dataset and corpus SHA-256 values are embedded in [`search-matrix-development.json`](search-matrix-development.json). Run it with:

```bash
uv sync --frozen --extra dev --extra semantic
uv run --frozen --no-sync python scripts/evaluate_search_matrix.py
```

The matrix measures keyword scoring, multilingual dense embeddings, Qdrant BM25 sparse retrieval, dense+BM25 RRF hybrid retrieval, and hybrid candidates followed by BGE cross-encoder reranking. The local Qdrant run uses the same in-memory collection and corpus. Latency is local query latency after warmup; it excludes API transport and response generation.

## Results

| Method | Hit@1 | Hit@3 | MRR@10 | Unsupported accepted | p50 latency | First-rank/missing errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Keyword | 87.0% | 98.1% | 0.927 | 10.0% | 1.4 ms | 8 |
| Dense semantic | 68.5% | 75.9% | 0.734 | 0.0% | 8.3 ms | 17 |
| BM25 sparse | 81.5% | 98.1% | 0.892 | 80.0% | 0.8 ms | 18 |
| Dense + BM25 hybrid (RRF) | 81.5% | 94.4% | 0.888 | 80.0% | 10.9 ms | 18 |
| Hybrid + BGE reranker | Not measured | | | | | |

The BGE model weights were not cached and Hugging Face could not be reached in this environment. The matrix JSON records the skipped method and reason. Run the same command where `BAAI/bge-reranker-v2-m3` is available to complete that row. No reranking score is inferred from the other methods.

These measurements show a useful tradeoff rather than a universal winner: the tuned keyword baseline leads this development set on ranking and latency; dense search abstains on these unsupported queries but misses more relevant paraphrases; BM25 and hybrid retrieve relevant items in their top three often, while also accepting many unsupported questions. Raw retrieval acceptance is not the final chat answer rate: the guarded workflow and policy checks decide whether to answer or abstain.

## Error examples to review

- **Keyword, wrong first result:** “Faturayı geciktirirsem internetim hemen kesilir mi?” expects `bill-008`, but ranks generic package FAQ `pkg-001` first. The correct entry is second.
- **Dense, missing expected FAQ:** “Ödeme kanallarınız neler?” expects `bill-001`, but returns only `pkg-001`. Exact payment-channel vocabulary is weak in this embedding representation.
- **BM25, unsupported false acceptance:** “Araba kiralama fiyatları ne kadar?” returns telecom price entries. Shared words such as “fiyat” are insufficient evidence of telecom intent.
- **Hybrid, unsupported false acceptance:** “Yarın İstanbul'da hava kaç derece olacak?” returns `general-001` and telecom FAQs. RRF preserves candidate recall but is not a domain classifier or abstention policy.

The report contains every failed query ID, expected FAQ ID, selected IDs and latency. The labels and corpus are synthetic, compact and have influenced retrieval tuning; they do not support a production accuracy claim. Create a separately authored v2 evaluation set before estimating generalization. [`retrieval_holdout_v1.json`](../data/evaluation/retrieval_holdout_v1.json) was already used to diagnose and verify the policy regression; v1 is only a known-regression replay, not an independent test set or final success metric.

