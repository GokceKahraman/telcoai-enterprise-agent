from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: UUID | None = None
    category: Literal["internet_paketleri", "fiyatlandirma", "fatura", "teknik_destek"] | None = (
        None
    )

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Mesaj boş olamaz.")
        return stripped


class SourceInfo(BaseModel):
    entry_id: str
    category: str
    matched_question: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Ranking signal, not probability")


class ChatResponse(BaseModel):
    answer: str
    source: SourceInfo | None = None
    fallback: bool = False
    session_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID = Field(default_factory=uuid4)
    intent: Literal["billing", "technical", "packages", "general", "greeting"] = "general"
    handoff: bool = False
    pii_redacted: bool = False
    safe_message: str = ""
    cache_hit: bool = False
    latency_ms: float = Field(default=0, ge=0)
    steps: list[str] = Field(default_factory=list)


class AnswerDraft(BaseModel):
    """A concise grounded reply tied to one authoritative FAQ source."""

    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=1200)


class SessionMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class SessionHistory(BaseModel):
    session_id: UUID
    messages: list[SessionMessage]
