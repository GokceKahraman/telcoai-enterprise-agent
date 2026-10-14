"""Validated configuration; tenant identity is server controlled."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TELCOAI_", env_file=".env", extra="ignore", frozen=True
    )
    app_name: str = "TelcoAI"
    retrieval_strategy: Literal["keyword", "semantic", "qdrant_hybrid"] = "keyword"
    min_match_score: float = Field(default=2.0, ge=0)
    embedding_model_name: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="TELCOAI_EMBEDDING_MODEL",
    )
    semantic_min_similarity: float = Field(default=0.42, ge=0, le=1)
    retrieval_top_k: int = Field(default=3, ge=1, le=20)
    retrieval_candidate_k: int = Field(default=20, ge=3, le=100)
    tenant_id: str = Field(default="demotel", pattern=r"^[a-z0-9_-]{1,64}$")
    locale: str = Field(default="tr-TR", pattern=r"^[a-z]{2,3}-[A-Z]{2}$")
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "telcoai_faq"
    reranker_enabled: bool = False
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    storage_backend: Literal["memory", "redis"] = "memory"
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    session_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    session_max_messages: int = Field(default=40, ge=2, le=200)
    cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    semantic_cache_enabled: bool = False
    semantic_cache_threshold: float = Field(default=0.97, ge=0.9, le=1)
    privacy_mode: Literal["presidio"] = "presidio"
    generation_backend: Literal["extractive", "llm"] = "extractive"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: SecretStr = SecretStr("local-demo")
    llm_model: str = "qwen3:8b"
    llm_timeout_seconds: float = Field(default=20, ge=1, le=120)
    guardrails_enabled: bool = False
    langfuse_enabled: bool = False
    api_key: SecretStr | None = None
    grpc_host: str = "127.0.0.1"
    grpc_port: int = Field(default=50051, ge=1, le=65535)
    demo_actions_enabled: bool = True
    demo_action_db_path: Path = Path("artifacts/demo_actions.sqlite3")

    @model_validator(mode="after")
    def check_modes(self) -> "Settings":
        if self.session_max_messages % 2:
            raise ValueError("session_max_messages must be even to retain complete turns.")
        if self.semantic_cache_enabled and self.retrieval_strategy == "keyword":
            raise ValueError("Semantic cache requires a semantic or qdrant_hybrid retriever.")
        if self.reranker_enabled and self.retrieval_strategy != "qdrant_hybrid":
            raise ValueError("The reranker is supported by qdrant_hybrid retrieval.")
        if self.retrieval_candidate_k < self.retrieval_top_k:
            raise ValueError("retrieval_candidate_k must be >= retrieval_top_k.")
        return self

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def knowledge_base_path(self) -> Path:
        return self.project_root / "data" / "knowledge_base.json"

    @property
    def static_dir(self) -> Path:
        return self.project_root / "static"

    @property
    def evaluation_dataset_path(self) -> Path:
        return self.project_root / "data" / "evaluation" / "retrieval_eval.json"


def get_settings() -> Settings:
    return Settings()
