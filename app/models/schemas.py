from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


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
    locale: Literal["tr-TR", "en-US"] = "tr-TR"

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


class DemoCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(pattern=r"^DEMO-[0-9]{4}$", max_length=9)
    access_code: SecretStr = Field(min_length=1, max_length=100)


class DemoBillRequest(DemoCredentials):
    pass


class DemoBillItem(BaseModel):
    label: str
    amount_try: str


class DemoBill(BaseModel):
    bill_id: str
    period: str
    amount_try: str
    status: Literal["paid", "unpaid"]
    items: list[DemoBillItem]
    source: Literal["synthetic_demo_billing_fixture"]


class DemoBillsResponse(BaseModel):
    account_id: str
    bills: list[DemoBill]


class DemoPrepareRequest(DemoCredentials):
    bill_id: str = Field(pattern=r"^BILL-[A-Za-z0-9-]{1,40}$")
    issue: Literal["billing_dispute", "payment_not_reflected"]


class DemoDraft(BaseModel):
    draft_id: UUID
    expires_at: datetime
    account_id: str
    bill_id: str
    period: str
    amount_try: str
    issue: Literal["billing_dispute", "payment_not_reflected"]
    source: Literal["synthetic_demo_billing_fixture"]
    requires_confirmation: Literal[True]


class DemoConfirmRequest(DemoCredentials):
    draft_id: UUID
    idempotency_key: UUID


class DemoTicketLookup(DemoCredentials):
    ticket_id: str = Field(pattern=r"^DT-[A-F0-9]{32}$")


class DemoTicket(BaseModel):
    id: str
    draft_id: UUID
    account_id: str
    bill_id: str
    issue: Literal["billing_dispute", "payment_not_reflected"]
    created_at: datetime
    source: Literal["synthetic_demo_ticket_database"] = "synthetic_demo_ticket_database"
