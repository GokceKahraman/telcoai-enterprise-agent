# Architecture and engineering decisions

TelcoAI supports Turkish FAQ assistance for a fictional operator. Its contract returns an answer and source evidence, plus workflow metadata. The same application service backs the HTTP demo and the gRPC adapter.

## Request processing

Supported PII patterns are masked before the message enters LangGraph state. The service reads redacted history and builds follow-up context. The graph then runs local policy/intent routing, cache lookup, retrieval, response selection and output validation/masking. The service stores the resulting redacted turn. Requests for account-changing actions produce a human handoff decision. Queries with no relevant result produce a fallback. Neither path invokes a real account operation.

The default response copies the highest-ranked FAQ and needs no inference API key. Exact greetings, thanks and farewells are handled as small talk without retrieval. Optional LLM mode receives the masked query, up to six recent redacted messages and retrieved FAQ evidence. It returns a concise natural-language answer plus a source ID under a strict Pydantic contract; the ID must match a retrieved candidate. Provider errors or invalid output fall back to the best retrieved FAQ. The model can paraphrase source content, so a valid citation establishes provenance but does not guarantee every generated claim is supported. Review and evaluate generated answers before production use. Stored history is bounded by message count and a refresh-on-write session TTL.

## Retrieval design

`Retriever` decouples routing from the search backend. Keyword retrieval is the offline baseline. Local semantic retrieval computes one document matrix on initialization, embeds the query and uses cosine similarity. Qdrant combines a multilingual dense vector and FastEmbed BM25 sparse vector with reciprocal rank fusion (RRF). Both document encoders use question + curated keywords (`faq-question-keywords-v2`); full answers remain authoritative payload fields. This represents the FAQ intent without diluting it with long answer text.

Qdrant ingestion creates keyword `payload_index` entries on `tenant_id`, `locale` and `category` before upsert. Both dense and sparse prefetches receive the scope filter; the fused query also receives it. Dense similarity filtering controls the dense branch. RRF and sparse scores have different scales, so there is no claim that a fused score represents answer correctness. A sparse match can still accept an unrelated query; OOD false acceptance is measured explicitly.

Qdrant’s sparse BM25 collection uses its IDF modifier. Query encoding and document encoding use their respective model methods. The locale selects a supported sparse tokenizer language. CrossEncoder BGE re-ranking is optional because it adds model memory and inference time; it scores the retrieved candidates rather than the entire corpus.

See the primary references for [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/), [payload indexing](https://qdrant.tech/documentation/manage-data/indexing/) and the [BGE reranker model](https://huggingface.co/BAAI/bge-reranker-v2-m3).

## Collection lifecycle

The API does not recreate or upsert its collection. `scripts/ingest.py` owns ingestion. A point ID is derived from tenant, locale and FAQ ID, so repeating the same ingestion updates matching points and preserves other records. Records absent from a new batch remain stored: withdrawing a document needs an explicit lifecycle operation.

The ingestion command checks vector names, dense dimension/distance and sparse IDF configuration. A model change with the same vector dimension cannot be detected by those shape checks. Use a new collection for embedding-model or tokenizer changes, evaluate it, then switch the API configuration. Corpus hashes in evaluation reports describe the local file; they do not verify every point in a remote collection.

## Storage, cache and observability

Memory storage provides a bounded local demo. Redis enables session persistence across service processes using namespaced keys and TTLs. The semantic cache checks a bounded set of recent cached answers; it does not use a Redis vector index. Its threshold is intentionally conservative and should be tuned on a held-out set. Semantic reuse also checks intent, numeric/negation signatures and the current top citation, so it still performs retrieval; it can avoid optional LLM source selection. Only requests with no prior history and no newly recognized PII are cacheable. Cache namespaces include corpus and retrieval/generation configuration; production corpus lifecycle still requires coordinated invalidation.

Loguru emits queued structured application events. Optional Langfuse records a completed support span with operational metadata and a generated trace identifier. It receives no chat text or session identifier, and it is a separate opt-in connection. Evaluation runs can log metrics, configuration and the JSON report to MLflow. They are separate concerns: traces explain a request, while evaluation reports compare a labeled dataset.

## Deliberate boundaries

LangGraph is the selected workflow framework; its explicit state transitions suit a constrained support flow. CrewAI and AutoGen are alternative frameworks for other agent-coordination designs. This implementation keeps one orchestration framework so routing decisions and state transitions remain clear to review. Guardrails AI is an optional integration alongside the built-in policy and Pydantic checks. No prompt-pattern filter provides complete protection against prompt injection, and the prototype exposes no destructive support tools.

The application owns a single configured tenant/locale. Server-controlled filters help isolate retrieval, but a production multi-tenant gateway would need verified identity and authorization. One optional shared API key cannot replace per-user access control. Kubernetes examples teach deployments, services, probes, resource requests and PVCs; distributed operations and high availability remain deployment work.
