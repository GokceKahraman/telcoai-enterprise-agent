# Local verification

## Automated checks

### Latest website and corpus update — 13 October 2026

- Ruff lint and formatting: passed (71 Python files checked).
- JavaScript syntax and HTML parser checks: passed.
- Complete offline suite (`pytest -m "not integration"`): **113 passed, 2 integration tests deselected**. The deselected tests require a live Qdrant server.
- Browser smoke test: homepage loaded, floating assistant opened/closed as a dialog, and “Selam” received a natural Turkish greeting.
- Expanded 40-record corpus loaded and passed schema plus PII-pattern validation.
- Retrieval set expanded to 54 relevant paraphrases and 10 unrelated queries. Current keyword and local dense results are recorded separately in the expanded corpus reports; see [evaluation methodology](evaluation.md) for their limits.
- The optional dense model was already cached locally. Hugging Face metadata checks retried because external network access is unavailable, then the model loaded from its cached weights.

### Earlier baseline verification — 12 October 2026

Python 3.12.15, uv 0.13.0, macOS arm64.

- Ruff lint and formatting: passed.
- JavaScript syntax (`node --check static/js/chat.js`): passed.
- `uv lock --check --offline`: passed; the lock covers all declared extras.
- Editable package installation with development dependencies: passed.
- Complete pytest run with semantic and Guardrails extras: **110 passed, 1 skipped**.
- At that earlier checkpoint, **26 focused tests passed** after the conversational-chat update; the full suite has since been rerun as reported above.
- Application coverage: **90%**, including checked-in generated Protobuf modules.
- The skipped test requires a live Qdrant server to verify actual payload indexes.

Reproduce the default checks:

```bash
uv sync --frozen --extra dev
make lint
make test
make evaluate
make ragas-export
```

Include the optional real embedding model and Guardrails tests:

```bash
uv sync --frozen --extra dev --extra semantic --extra guardrails
TELCOAI_RUN_INTEGRATION=1 uv run --frozen --no-sync pytest --cov=app
```

The embedding model downloads on first use. The recorded full run used previously
downloaded weights in offline mode. Third-party Typer/Guardrails deprecation warnings
were present; the tests completed successfully.

## Integration evidence

- REST contracts, validation, bearer access, masked history, deletion and generic
  dependency failures were exercised through FastAPI TestClient.
- A real local gRPC client/server round trip exercised Protobuf, source selection,
  masking, authentication and invalid-input handling.
- Qdrant's local query engine executed named dense/sparse prefetches and RRF with
  tenant, locale and category scope. Tests checked the payload-index creation calls.
- Real multilingual MiniLM and Turkish BM25 produced the checked-in dense, hybrid
  and guarded-workflow reports. No BGE weights were downloaded.
- Redis behavior was tested with fakeredis, including TTL, namespacing, atomic turn
  appends, history bounds and the bounded semantic-cache candidate index.
- Guardrails AI parsed a valid structured answer; malformed or unsupported citations
  and answer text were rejected through the structured generator's validation.
- MLflow SQLite tracking stored metrics, input hashes and a JSON evaluation artifact.
- Ragas input export completed locally. No external judge was called.
- Browser interaction verified a cited billing answer, typed masking, active status
  and the workflow-details panel. Desktop and mobile layouts were visually inspected.

## Not exercised here

Docker is unavailable on the execution host. Compose and Kubernetes YAML files were
parsed, but containers and cluster workloads were not launched. GitHub Actions includes
Compose configuration, Docker build, container readiness and a separate real-Qdrant
payload-index integration job; those checks have
not run on GitHub yet. Live Redis/Qdrant services, server-side payload indexing/HNSW,
BGE model inference, hosted Langfuse and paid LLM/Ragas calls remain external integration
checks. Adapter and local-engine tests do not establish those services' availability.

The default demo runs without these services. Measured retrieval results describe a
small synthetic development set, not held-out accuracy or production certification.
