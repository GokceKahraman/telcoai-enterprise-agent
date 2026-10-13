# Deployment and operations

The default demo uses keyword retrieval, extractive responses and in-memory storage. It needs Python dependencies but no model weights, inference key, database or external trace service. The enterprise integration profile adds Qdrant hybrid search, Redis and semantic caching.

## Configuration reference

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `TELCOAI_RETRIEVAL_STRATEGY` | `keyword` | `keyword`, `semantic`, `qdrant_hybrid` |
| `TELCOAI_TENANT_ID` / `TELCOAI_LOCALE` | `demotel` / `tr-TR` | Server-owned retrieval/storage scope |
| `TELCOAI_RETRIEVAL_TOP_K` / `TELCOAI_RETRIEVAL_CANDIDATE_K` | `3` / `20` | Response candidates / hybrid re-ranking pool |
| `TELCOAI_MIN_MATCH_SCORE` | `1.0` | Keyword acceptance threshold |
| `TELCOAI_SEMANTIC_MIN_SIMILARITY` | `0.42` | Local dense / hybrid dense-branch threshold |
| `TELCOAI_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Dense model used for both ingest and query |
| `TELCOAI_QDRANT_URL` / `TELCOAI_QDRANT_COLLECTION` | `http://localhost:6333` / `telcoai_faq` | Qdrant endpoint and collection |
| `TELCOAI_QDRANT_API_KEY` | Unset | Optional Qdrant authentication |
| `TELCOAI_RERANKER_ENABLED` / `TELCOAI_RERANKER_MODEL` | `false` / `BAAI/bge-reranker-v2-m3` | Optional hybrid candidate re-ranking |
| `TELCOAI_STORAGE_BACKEND` / `TELCOAI_REDIS_URL` | `memory` / `redis://localhost:6379/0` | Session/cache backend |
| `TELCOAI_SESSION_TTL_SECONDS` / `TELCOAI_SESSION_MAX_MESSAGES` | `1800` / `40` | Session retention and message bound |
| `TELCOAI_CACHE_TTL_SECONDS` | `300` | FAQ response cache TTL |
| `TELCOAI_SEMANTIC_CACHE_ENABLED` / `TELCOAI_SEMANTIC_CACHE_THRESHOLD` | `false` / `0.97` | Conservative semantic reuse (requires semantic/hybrid) |
| `TELCOAI_GENERATION_BACKEND` | `extractive` | `extractive` or optional `llm` |
| `TELCOAI_LLM_BASE_URL` / `TELCOAI_LLM_MODEL` | `http://localhost:11434/v1` / `qwen3:8b` | Compatible LLM endpoint and model; the server/model is provisioned separately |
| `TELCOAI_LLM_API_KEY` | Local demo placeholder | Provider credential when required |
| `TELCOAI_GUARDRAILS_ENABLED` | `false` | Enable optional Guardrails AI integration |
| `TELCOAI_LANGFUSE_ENABLED` | `false` | Enable optional tracing |
| `TELCOAI_API_KEY` | Unset | Optional bearer token for protected API operations |
| `TELCOAI_GRPC_HOST` / `TELCOAI_GRPC_PORT` | `127.0.0.1` / `50051` | gRPC binding; Compose uses `0.0.0.0` inside the container |

Settings validate values and incompatible combinations. Credentials use secret types and are excluded from status/evaluation configuration. The example `.env` is local configuration; secrets belong in your environment or deployment secret manager, and `.env` is ignored by Git.

## Compose lifecycle

The README lists default and enterprise startup commands. Ingestion must complete before the enterprise API becomes ready. `depends_on` waits for database health, not collection content. The model cache is a named volume. Initial enterprise setup downloads the embedding and sparse assets; BGE re-ranking downloads additional weights when enabled.

```bash
# Inspect services and recent application logs.
docker compose -f compose.yaml -f compose.enterprise.yaml --profile enterprise ps
docker compose -f compose.yaml -f compose.enterprise.yaml --profile enterprise logs --tail 100 api
# Stop services while preserving volumes.
docker compose -f compose.yaml -f compose.enterprise.yaml --profile enterprise down
```

Avoid adding `--volumes` to routine shutdown: it deletes persisted demo data. Database ports bind to loopback, while internal service addresses use Compose names `qdrant` and `redis`. This local example has no database password/TLS. Add service authentication and network controls before shared deployment.

`/health` is HTTP liveness, `/ready` is dependency readiness. Redis/Qdrant failures should remove the instance from ready traffic and produce controlled service errors. Liveness is separate to avoid a restart loop caused solely by a temporarily unavailable dependency. Startup loads selected models, so allow longer initialization for enterprise mode.

## gRPC

The checked-in contract is `proto/telcoai.proto`; generated bindings are under `app/grpc/generated`. Regenerate bindings after editing the contract:

```bash
uv sync --frozen --extra dev
uv run --frozen --no-sync python scripts/generate_grpc.py
# Local demo listener:
uv run --frozen --no-sync python -m app.grpc.server
# Container demo listener:
docker compose --profile grpc up --build -d grpc
```

For the enterprise gRPC listener, complete enterprise ingestion first, then:

```bash
docker compose -f compose.yaml -f compose.enterprise.yaml --profile enterprise --profile grpc up -d grpc
```

The gRPC service uses the same validated message/session contract and support service as HTTP. If an API key is configured, clients pass `authorization: Bearer <token>` as metadata. The example is an insecure local gRPC transport and a TCP-level Compose health check; shared deployment needs TLS and application-level health/auth controls.

## Optional generation, guardrails and tracing

Set `TELCOAI_GENERATION_BACKEND=llm` and configure an existing OpenAI-compatible endpoint/model. The starter `.env.example` targets a local Ollama OpenAI-compatible endpoint at `http://localhost:11434/v1` and model `qwen3:8b`; install and start that model server separately, then add `--extra guardrails` if structured-output Guardrails validation is wanted. Recent redacted turns and retrieved, redacted FAQ evidence are sent to the configured model. The provider can paraphrase evidence; validate generated answers against an evaluation set before production. When generation is unavailable or invalid, the service falls back to the top retrieved FAQ. This repository does not install or start an LLM server or supply model credentials. Greetings work in the default extractive configuration without an LLM.

```bash
uv sync --frozen --extra dev --extra observability --extra guardrails
```

Langfuse requires `TELCOAI_LANGFUSE_ENABLED=true` and the SDK variables `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`. Guardrails AI requires its extra, `TELCOAI_GENERATION_BACKEND=llm` and `TELCOAI_GUARDRAILS_ENABLED=true`; it validates the structured response containing a retrieved source ID and generated answer. Add `--extra semantic` to the sync command when using dense/hybrid retrieval. These commands install adapters; they do not establish a remote connection by themselves. The default Docker image includes base dependencies; rebuilding with `--build-arg UV_EXTRAS=observability` installs that optional extra. Combining additional optional integrations in a deployed image requires declaring the chosen extras in its build configuration.

## Kubernetes learning examples

`deploy/k8s` includes one API Deployment, internal Services, configuration, optional secret references, HTTP probes, resource bounds and single-replica Qdrant/Redis StatefulSets with PVCs. A default storage class is required. These are local-cluster examples without ingress, HA, backup jobs, database authentication or network policies.

```bash
docker build -t telcoai:demo .
# Load the image into your cluster, for example with kind:
kind load docker-image telcoai:demo
kubectl apply -k deploy/k8s
kubectl -n telcoai rollout status deployment/telcoai-api
kubectl -n telcoai port-forward service/telcoai-api 8000:8000
```

For the enterprise overlay:

```bash
docker build --build-arg UV_EXTRAS=semantic -t telcoai:enterprise .
kind load docker-image telcoai:enterprise
kubectl apply -k deploy/k8s/enterprise
kubectl -n telcoai rollout status statefulset/qdrant
kubectl -n telcoai rollout status statefulset/redis
kubectl apply -f deploy/k8s/ingest-job.yaml
kubectl -n telcoai wait --for=condition=complete job/telcoai-ingest --timeout=600s
kubectl -n telcoai rollout status deployment/telcoai-api
```

A missing collection keeps the API unready until the explicit ingestion job succeeds. Model caches are ephemeral in this Kubernetes example; a restart may download models again. Configure a persistent/prepopulated model cache and deployment-specific startup timeout for larger models. The optional `telcoai-secrets` references are placeholders, not supplied credentials. Setting a Qdrant API key on the API also requires configuring matching authentication on the Qdrant server.

If you changed embedding/tokenizer configuration, select a new collection and ingest it before routing traffic. Reapplying a Job with the same immutable name requires a deliberate job lifecycle change after the previous job finishes; routine API restarts never trigger ingestion.
