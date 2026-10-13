#!/usr/bin/env python3
"""Explicit, non-destructive Qdrant FAQ ingestion (never run on API startup)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBase
from app.services.retrieval.factory import get_embedding_model, get_sparse_embedding_model
from app.services.retrieval.qdrant_retriever import ingest_entries


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base", type=Path, default=settings.knowledge_base_path)
    parser.add_argument("--tenant-id", default=settings.tenant_id)
    parser.add_argument("--locale", default=settings.locale)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    knowledge_base = KnowledgeBase(args.knowledge_base)
    entries = [
        entry
        for entry in knowledge_base.entries
        if entry.tenant_id == args.tenant_id and entry.locale == args.locale
    ]
    if not entries:
        parser.error("Knowledge base has no entries for the selected tenant/locale")

    # Optional dependencies and model downloads only occur after CLI validation.
    from qdrant_client import QdrantClient

    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        timeout=30,
    )
    try:
        count = ingest_entries(
            client,
            settings.qdrant_collection,
            entries,
            get_embedding_model(settings.embedding_model_name),
            get_sparse_embedding_model(args.locale),
            batch_size=args.batch_size,
        )
    finally:
        client.close()
    print(
        json.dumps(
            {
                "collection": settings.qdrant_collection,
                "tenant_id": args.tenant_id,
                "locale": args.locale,
                "upserted": count,
                "deletion_policy": "retain_existing_points",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
