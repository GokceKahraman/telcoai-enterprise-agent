# Contributing

Use Python 3.12–3.13 and `uv sync --frozen --extra dev`.
Run `make lint`, `make test` and `make evaluate` before proposing a change.
Use synthetic examples in tests, issues and evaluation data.

Keep the default demo runnable without model downloads, paid APIs or databases.
Test tenant/locale filtering, redaction and source grounding when changing retrieval
or workflow logic. When changing indexed text or models, use a new Qdrant collection,
ingest explicitly and retain before/after evaluation reports with input hashes.

Optional service/model tests are marked `integration`. See the README for their
opt-in variables. Include measured results and any unverified integrations in the
pull request; do not interpret a tiny synthetic dataset as production accuracy.
