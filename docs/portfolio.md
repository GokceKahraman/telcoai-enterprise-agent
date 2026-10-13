# Portfolio walkthrough

A useful interview demonstration is a short reproducible engineering story, followed by code and measurable limitations. Use synthetic examples throughout.

## Five-minute walkthrough

1. Start the offline demo, ask a billing question and show the source and workflow steps.
2. Add a synthetic phone/e-mail, show typed masking, then show redacted session history and deletion.
3. Request a cancellation to demonstrate a human handoff decision with no real account operation.
4. Run `make evaluate`, inspect the per-query failures and explain why nearest-neighbor search needs abstention testing.
5. Switch to the Qdrant/Redis profile, show explicit ingestion and payload indexes, then compare one dense/BM25 query and repeated-session behavior.

## Code worth discussing

| Topic | Evidence in this repository | Tradeoff to explain |
| --- | --- | --- |
| Workflow orchestration | LangGraph service and typed request/response models | Explicit decisions and testability; optional generation |
| Tenant filtering | Qdrant prefetch/fusion scope plus payload indexes | Server identity still requires a real authentication layer |
| Hybrid search | Dense vectors, query/document BM25 encoding, Qdrant IDF, RRF | Retrieval scores have separate scales and are not confidence probabilities |
| Safe ingestion | Stable point identities, upsert and schema checks | No implicit deletion; model migration uses a new collection |
| Re-ranking | Optional multilingual BGE CrossEncoder | Quality must justify model memory and latency |
| Privacy | Presidio recognizers and redacted persistence | Narrow patterns require false-negative/false-positive evaluation |
| Caching | TTL-bound sessions/exact cache and bounded semantic candidates | Context/provenance compatibility matters; inspect invalidation |
| Evaluation | Labeled retrieval report, input hashes, optional MLflow/Ragas | Small synthetic dataset and judge limitations |
| Delivery | Locked dependencies, CI, non-root Docker and probe examples | Container examples need deployment-specific hardening |

Describe this as an independent prototype built around relevant engineering practices. Avoid claiming knowledge of Etiya’s internal implementation, production traffic, KVKK certification or a deployed result you have not measured. A candid explanation of an observed failure is better evidence than an unsupported accuracy claim.

## GitHub presentation

Keep the repository name and description precise, include the README and architecture/privacy/evaluation documents, and add a screenshot from a real local run. Before publishing, inspect `git diff`, ensure `.env`, caches, model weights and generated local artifacts are ignored, and run the documented checks. The committed evaluation baseline is a transparent single run; keep its data hashes and configuration when comparing future changes.
