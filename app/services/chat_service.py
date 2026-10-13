"""A bounded LangGraph workflow, shared by HTTP and gRPC."""

import re
from time import perf_counter
from typing import TypedDict
from uuid import UUID, uuid4

import numpy as np
from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.models.schemas import ChatResponse, SourceInfo
from app.services.policy import PolicyService
from app.services.privacy import PrivacyService
from app.services.retrieval.base import RetrievalHit, Retriever
from app.services.store import MemoryStore, Store, cache_key
from app.services.telemetry import Telemetry

FALLBACK_ANSWER = (
    "Bu soruyu DemoTel bilgi tabanında güvenilir bir kaynakla eşleştiremedim. "
    "Paketler, fatura veya teknik destek hakkında daha açık bir soru yazabilirsiniz. "
    "Hesabınıza özel konular için müşteri temsilcisine başvurun."
)
EN_FALLBACK_ANSWER = (
    "I could not find a reliable answer in the DemoTel knowledge base. Ask a more specific "
    "question about plans, billing or technical support. For account-specific help, contact "
    "customer support."
)
HANDOFF_ANSWER = (
    "Bu işlem için kimlik doğrulaması yapan bir müşteri temsilcisine başvurmalısınız. "
    "Bu demo hesabınıza erişmez, abonelik değiştirmez ve gerçek destek kaydı açmaz. "
    "Kişisel bilgilerinizi burada paylaşmadan DemoTel uygulamasındaki destek kanalını kullanın."
)
EN_HANDOFF_ANSWER = (
    "This request needs an authenticated customer support representative. This demo cannot "
    "access your account, change a subscription or create a real support case. Please use the "
    "support channel in the DemoTel app and do not share personal information here."
)
BLOCKED_ANSWER = (
    "Destek akışının talimatlarını değiştiremiyorum. DemoTel paketleri, "
    "fatura ve teknik destek hakkında yardımcı olabilirim."
)
EN_BLOCKED_ANSWER = (
    "I can’t change the support assistant’s instructions. I can help with DemoTel plans, "
    "billing and technical support."
)


class SupportState(TypedDict, total=False):
    query: str
    locale: str
    category: str | None
    intent: str
    blocked: bool
    out_of_scope: bool
    handoff: bool
    history_context: list[dict[str, str]]
    cacheable: bool
    cache_hit: bool
    semantic_hit: bool
    vector: list[float] | None
    hits: list[RetrievalHit]
    cached: dict | None
    answer: str
    source: SourceInfo | None
    fallback: bool
    steps: list[str]


class ChatService:
    def __init__(
        self,
        retriever: Retriever,
        top_k: int = 3,
        *,
        settings: Settings | None = None,
        privacy: PrivacyService | None = None,
        store: Store | None = None,
        fingerprint: str = "demo",
        embedder=None,
        generator=None,
        telemetry: Telemetry | None = None,
    ) -> None:
        self._retriever, self._top_k = retriever, top_k
        self.settings = settings or Settings()
        self.privacy = privacy or PrivacyService()
        self.store = store or MemoryStore()
        self._fingerprint, self._embedder = fingerprint, embedder
        self._generator, self._telemetry = generator, telemetry or Telemetry()
        self._policy = PolicyService()
        graph = StateGraph(SupportState)
        graph.add_node("classify", self._classify)
        graph.add_node("cache_lookup", self._cache_lookup)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("answer", self._answer)
        graph.add_node("validate", self._validate)
        graph.add_edge(START, "classify")
        graph.add_conditional_edges(
            "classify",
            lambda s: (
                "answer"
                if s["blocked"] or s["handoff"] or s["out_of_scope"] or s["intent"] == "greeting"
                else "cache_lookup"
            ),
        )
        graph.add_conditional_edges(
            "cache_lookup",
            lambda s: "answer" if s["cache_hit"] and not s.get("semantic_hit") else "retrieve",
        )
        graph.add_edge("retrieve", "answer")
        graph.add_edge("answer", "validate")
        graph.add_edge("validate", END)
        self.graph = graph.compile()

    def _step(self, state: SupportState, name: str) -> list[str]:
        return [*state.get("steps", []), name]

    def _cache_key(self, query: str, category: str | None = None, locale: str = "tr-TR") -> str:
        return f"{self._fingerprint}:{locale}:{category or 'all'}:{cache_key(query)}"

    def _classify(self, state: SupportState) -> dict:
        query = state["query"]
        locale = state.get("locale", "tr-TR")
        greeting = self._policy.is_smalltalk(query, locale)
        return {
            "intent": "greeting" if greeting else self._policy.intent(query, locale),
            "blocked": self._policy.blocked(query),
            "out_of_scope": not self._policy.supported(query, locale),
            "handoff": self._policy.handoff(query, locale),
            "steps": self._step(state, "classify"),
        }

    def _signature(self, query: str) -> tuple:
        normalized = self._policy.normalize(query)
        negatives = tuple(
            sorted(re.findall(r"\b(?:değil|degil|yok|hayir|istemiyorum|not|no)\b", normalized))
        )
        return tuple(re.findall(r"\d+", normalized)), negatives

    def _cache_lookup(self, state: SupportState) -> dict:
        update = {
            "cache_hit": False,
            "cached": None,
            "vector": None,
            "steps": self._step(state, "cache_lookup"),
        }
        if not state["cacheable"]:
            return update
        cached = self.store.cache_get(
            self._cache_key(state["query"], state.get("category"), state.get("locale", "tr-TR"))
        )
        if cached:
            return {**update, "cache_hit": True, "cached": cached}
        if self.settings.semantic_cache_enabled and self._embedder is not None:
            vector = np.asarray(self._embedder.encode([state["query"]])[0], dtype=float)
            norm = np.linalg.norm(vector)
            if not np.isfinite(norm) or norm == 0:
                return update
            vector = vector / norm
            update["vector"] = vector.tolist()
            for candidate in self.store.candidates():
                if candidate.get("scope") != self._fingerprint or candidate.get(
                    "category"
                ) != state.get("category"):
                    continue
                other = np.asarray(candidate.get("vector", []), dtype=float)
                if other.shape != vector.shape or candidate.get("intent") != state["intent"]:
                    continue
                signature = candidate.get("signature", [])
                if signature != [list(part) for part in self._signature(state["query"])]:
                    continue
                if float(np.dot(vector, other)) >= self.settings.semantic_cache_threshold:
                    return {**update, "cache_hit": True, "semantic_hit": True, "cached": candidate}
        return update

    def _retrieve(self, state: SupportState) -> dict:
        if state.get("category"):
            hits = self._retriever.retrieve(
                state["query"], top_k=self._top_k, category=state["category"]
            )
        else:
            hits = self._retriever.retrieve(state["query"], top_k=self._top_k)
        # Revalidate semantic reuse against the current top citation. Near meaning alone is unsafe.
        accepted = state.get("cache_hit", False)
        if state.get("semantic_hit"):
            accepted = bool(hits and hits[0].entry.id == state["cached"]["source"]["entry_id"])
        return {"hits": hits, "cache_hit": accepted, "steps": self._step(state, "retrieve")}

    def _answer(self, state: SupportState) -> dict:
        english = state.get("locale") == "en-US"
        common = {"source": None, "fallback": True, "steps": self._step(state, "answer")}
        if state["blocked"]:
            return {**common, "answer": EN_BLOCKED_ANSWER if english else BLOCKED_ANSWER}
        if state["handoff"]:
            return {**common, "answer": EN_HANDOFF_ANSWER if english else HANDOFF_ANSWER}
        if state["intent"] == "greeting":
            query = self._policy.normalize(state["query"])
            if english:
                if "thank" in query:
                    answer = "You’re welcome! Is there anything else I can help you with?"
                elif "how are you" in query:
                    answer = (
                        "I’m doing well, thanks for asking! How can I help with your bill, "
                        "mobile plan or internet connection?"
                    )
                elif "bye" in query or "goodbye" in query:
                    answer = (
                        "Goodbye! I’m here whenever you need help with billing, plans or "
                        "technical support."
                    )
                else:
                    answer = (
                        "Hello! I’m the DemoTel support assistant. How can I help with your "
                        "bill, internet plan or connection today?"
                    )
                return {**common, "answer": answer, "fallback": False}
            if "teşekkür" in query or "tesekkur" in query or "sağ ol" in query or "sag ol" in query:
                answer = "Rica ederim! Başka bir konuda yardımcı olabilir miyim?"
            elif "nasılsın" in query or "nasilsin" in query:
                answer = (
                    "İyiyim, teşekkür ederim! Fatura, internet paketi veya teknik bir konuda "
                    "sana nasıl yardımcı olabilirim?"
                )
            elif (
                "görüşürüz" in query
                or "gorusuruz" in query
                or "hoşça kal" in query
                or "hosca kal" in query
            ):
                answer = (
                    "Görüşmek üzere! İhtiyacın olursa fatura, paket ve teknik destek "
                    "konularında buradayım."
                )
            else:
                answer = (
                    "Merhaba! Ben DemoTel destek asistanıyım. Faturanız, internet paketiniz "
                    "veya bağlantı sorununuz hakkında nasıl yardımcı olabilirim?"
                )
            return {**common, "answer": answer, "fallback": False}
        if state["out_of_scope"]:
            return {
                **common,
                "answer": EN_FALLBACK_ANSWER if english else FALLBACK_ANSWER,
                "handoff": True,
            }
        if state.get("cache_hit"):
            cached = state["cached"]
            return {
                **common,
                "answer": cached["answer"],
                "source": SourceInfo.model_validate(cached["source"]),
                "fallback": False,
            }
        hits = state.get("hits", [])
        if not hits:
            return {
                **common,
                "answer": EN_FALLBACK_ANSWER if english else FALLBACK_ANSWER,
                "handoff": True,
            }
        best = hits[0]
        steps = common["steps"]
        if self._generator is not None:
            try:
                if english:
                    best, generated_answer = self._generator.respond(
                        state["query"], hits, state.get("history_context", []), language="en-US"
                    )
                else:
                    best, generated_answer = self._generator.respond(
                        state["query"], hits, state.get("history_context", [])
                    )
                steps = [*steps, "structured_generation"]
            except Exception:
                generated_answer = None
                steps = [*steps, "generation_fallback"]
        else:
            generated_answer = None
        source = SourceInfo(
            entry_id=best.entry.id,
            category=best.entry.category,
            matched_question=(best.entry.question_en or best.entry.question)
            if english
            else best.entry.question,
            confidence=round(float(best.confidence), 4),
        )
        return {
            "answer": generated_answer
            or ((best.entry.answer_en or EN_FALLBACK_ANSWER) if english else best.entry.answer),
            "source": source,
            "fallback": False,
            "steps": steps,
        }

    def _validate(self, state: SupportState) -> dict:
        safe = self.privacy.redact(state["answer"])
        source = state.get("source")
        if source is not None:
            source = source.model_copy(
                update={"matched_question": self.privacy.redact(source.matched_question).text}
            )
        return {"answer": safe.text, "source": source, "steps": self._step(state, "validate")}

    def reply(
        self,
        message: str,
        session_id: UUID | None = None,
        category: str | None = None,
        locale: str = "tr-TR",
    ) -> ChatResponse:
        started = perf_counter()
        session_id = session_id or uuid4()
        # No raw message reaches graph state, history, embeddings, cache or telemetry.
        redacted = self.privacy.redact(message)
        history = self.store.history(session_id)
        query = redacted.text
        if history and self._policy.followup(query):
            previous = next((m.content for m in reversed(history) if m.role == "user"), "")
            query = f"{previous} | {query}"
        history_context = [{"role": item.role, "content": item.content} for item in history[-6:]]
        state = self.graph.invoke(
            {
                "query": query,
                "locale": locale,
                "category": category,
                "history_context": history_context,
                "cacheable": not redacted.changed and not history,
                "steps": ["redact"],
                "cache_hit": False,
            },
            config={"recursion_limit": 12},
        )
        response = ChatResponse(
            answer=state["answer"],
            source=state.get("source"),
            fallback=state["fallback"],
            session_id=session_id,
            intent=state["intent"],
            handoff=state.get("handoff", False),
            pii_redacted=redacted.changed,
            safe_message=redacted.text,
            cache_hit=state.get("cache_hit", False),
            steps=state["steps"],
        )
        self.store.append_turn(session_id, redacted.text, response.answer)
        if (
            state["cacheable"]
            and state["intent"] != "greeting"
            and response.source is not None
            and not response.fallback
            and not response.cache_hit
        ):
            self.store.cache_set(
                self._cache_key(query, category, locale),
                {
                    "answer": response.answer,
                    "source": response.source.model_dump(),
                    "scope": self._fingerprint,
                    "category": category,
                    "intent": response.intent,
                    "vector": state.get("vector"),
                    "signature": [list(part) for part in self._signature(query)],
                },
            )
        response.latency_ms = round((perf_counter() - started) * 1000, 2)
        self._telemetry.record(response)
        return response

    def close(self) -> None:
        self.store.close()
        if self._generator is not None:
            self._generator.close()
        self._telemetry.close()
        close = getattr(self._retriever, "close", None)
        if close:
            close()
