# Privacy and security boundaries

The bundled data describes DemoTel, a fictional operator. Do not add real customer records, credentials or company-confidential documents to the GitHub repository or benchmark dataset.

## What masking covers

Microsoft Presidio pattern recognizers and its anonymizer replace supported entities with typed placeholders such as `<EMAIL_ADDRESS>`. The recognizers cover e-mail addresses, Turkish mobile phone formats, 11-digit ID-like numbers, Turkish IBANs and card-like numbers. Input masking runs before retrieval, caching, history and optional model calls; outputs are masked before delivery and storage.

These are deliberately limited pattern recognizers without an NLP-model download. They can miss names, postal addresses, unusual spacing/number formats and contextual sensitive information. They can also mask non-sensitive numeric strings. ID/card recognition is pattern-based and is not identity or account verification. A redaction indicator means that some supported patterns were found; absence of an indicator does not imply absence of PII.

This is a data-minimization implementation, **not a KVKK/GDPR compliance certification**. Deployment with personal data requires a separate legal and technical assessment of purpose, access, retention, processor agreements and deletion.

## Storage and deletion

Default memory storage lasts within one application process and expires entries lazily when accessed. Redis stores redacted session messages with a default 30-minute TTL refreshed by new turns; the history is capped at 40 messages. Response caches have a default 5-minute TTL. Retention values are validated configuration. Redis AOF and database volumes persist across container restarts; TTLs apply to Redis keys, while filesystem backups and AOF rewrite/deletion timing need their own retention policy.

Deleting a session removes its history. Shared FAQ response caches are a distinct store; session deletion does not imply deletion of every cached answer, trace, log, database snapshot or browser-local identifier. Document the retention of any external systems you enable. Use session IDs as private identifiers: this demo does not establish authenticated user ownership of them.

## External connections

Keyword and extractive demo modes call no inference provider. Semantic/hybrid setup downloads model assets. Optional LLM generation sends masked prompts, recent redacted conversation turns and retrieved FAQ evidence to the configured compatible endpoint; review that endpoint before enabling it. Optional Langfuse sends operational metadata (intent, source ID, flags, timing, steps and a generated trace identifier) to its configured service. The adapter sends no chat text or session identifier. Log events avoid raw customer messages, but pattern-based masking alone cannot guarantee no sensitive data reaches these paths.

Ragas export is local and uses synthetic FAQ evaluation inputs. External judging requires an explicit CLI flag, selected model and API key; inputs are sent to the judge and costs may apply. A custom dataset is the operator’s responsibility: the script’s synthetic-data label describes the bundled default dataset, not an arbitrary file.

## Local access and deployment

Compose binds HTTP, gRPC and database ports to `127.0.0.1`. Containers communicate on the Compose network. The API container uses a non-root user. The included Kubernetes services are internal ClusterIP/headless services; port-forwarding is the example access method.

The default demo has no access key and database services have no configured authentication or TLS. For shared environments, configure the optional API key, verified user/session authorization, Redis/Qdrant credentials, TLS, network controls, rate limiting and secret management. The API-key hook is a prototype shared-secret gate. Tenant scope is trusted server configuration, not a client-provided tenant assertion.

Local policy patterns identify several common prompt-injection phrases and sensitive account-action requests. Pattern matching is incomplete. Pydantic validates shape and bounds; it cannot prove that an answer is safe or correct. Run adversarial tests and independent human review before expanding the workflow to account-changing tools.
