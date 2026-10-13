from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.services.privacy import PrivacyService


class FAQRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    category: str = Field(pattern=r"^[a-z0-9_]{1,100}$")
    question: str = Field(min_length=1, max_length=2000)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    answer: str = Field(min_length=1, max_length=6000)
    question_en: str | None = Field(default=None, min_length=1, max_length=2000)
    keywords_en: list[str] = Field(default_factory=list, max_length=100)
    answer_en: str | None = Field(default=None, min_length=1, max_length=6000)
    tenant_id: str = Field(default="demotel", pattern=r"^[a-z0-9_-]{1,64}$")
    locale: str = Field(default="tr-TR", pattern=r"^[a-z]{2,3}-[A-Z]{2}$")


@dataclass(frozen=True)
class FAQEntry:
    id: str
    category: str
    question: str
    keywords: tuple[str, ...]
    answer: str
    question_en: str | None = None
    keywords_en: tuple[str, ...] = ()
    answer_en: str | None = None
    tenant_id: str = "demotel"
    locale: str = "tr-TR"


class KnowledgeBase:
    """Yerel JSON dosyasından SSS kayıtlarını yükler ve sunar."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: list[FAQEntry] = []
        self._company: str = ""
        self.load()

    @property
    def company(self) -> str:
        return self._company

    @property
    def entries(self) -> list[FAQEntry]:
        return list(self._entries)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self._path.read_bytes()).hexdigest()[:16]

    def scoped(self, tenant_id: str, locale: str) -> KnowledgeBase:
        scoped = object.__new__(KnowledgeBase)
        scoped._path = self._path
        scoped._company = self._company
        scoped._entries = [
            e for e in self._entries if e.tenant_id == tenant_id and e.locale == locale
        ]
        return scoped

    def load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self._company = raw.get("company", "DemoTel")
        records = [
            FAQRecord.model_validate(
                {
                    "tenant_id": raw.get("tenant_id", "demotel"),
                    "locale": raw.get("locale", "tr-TR"),
                    **item,
                }
            )
            for item in raw["entries"]
        ]
        identities = [(r.tenant_id, r.locale, r.id) for r in records]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate FAQ identity within tenant and locale")
        privacy = PrivacyService()
        if any(
            privacy.redact(text).changed
            for r in records
            for text in (
                r.question,
                r.answer,
                " ".join(r.keywords),
                r.question_en or "",
                r.answer_en or "",
                " ".join(r.keywords_en),
            )
        ):
            raise ValueError(
                "Knowledge base contains recognized personal data; redact before ingestion"
            )
        self._entries = [
            FAQEntry(
                id=item["id"],
                category=item["category"],
                question=item["question"],
                keywords=tuple(item.get("keywords", [])),
                answer=item["answer"],
                question_en=item.get("question_en"),
                keywords_en=tuple(item.get("keywords_en", [])),
                answer_en=item.get("answer_en"),
                tenant_id=item.get("tenant_id", raw.get("tenant_id", "demotel")),
                locale=item.get("locale", raw.get("locale", "tr-TR")),
            )
            for item in [record.model_dump() for record in records]
        ]

    def get_by_id(self, entry_id: str) -> FAQEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None
