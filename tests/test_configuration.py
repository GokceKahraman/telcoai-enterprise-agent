import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    "configuration",
    [
        {"retrieval_strategy": "invented"},
        {"semantic_cache_enabled": True, "retrieval_strategy": "keyword"},
        {"session_max_messages": 3},
        {"reranker_enabled": True, "retrieval_strategy": "keyword"},
        {"retrieval_top_k": 20, "retrieval_candidate_k": 3},
        {"tenant_id": "../another-tenant"},
    ],
)
def test_invalid_runtime_configuration_fails_early(configuration):
    with pytest.raises(ValidationError):
        Settings(**configuration)
