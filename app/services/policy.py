"""Transparent local policy checks; no account-changing tools are exposed."""

import re
import unicodedata


class PolicyService:
    @staticmethod
    def normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text).lower().replace("\u0307", "").replace("ı", "i")

    def supported(self, text: str, locale: str = "tr-TR") -> bool:
        """Conservative demo scope; generic prices or advice need telecom context."""
        query = self.normalize(text).replace("wi-fi", "wifi")
        if self.is_smalltalk(text, locale):
            return True
        if locale == "en-US":
            portfolio_faq_terms = (
                "assistant",
                "chat history",
                "chatbot",
                "personal information",
                "sms code",
                "one-time code",
                "support source",
            )
            if any(term in query for term in portfolio_faq_terms):
                return True
            english_terms = (
                "demotel",
                "internet",
                "wifi",
                "wi-fi",
                "fiber",
                "mobile",
                "data",
                "bill",
                "payment",
                "pay",
                "invoice",
                "subscription",
                "plan",
                "package",
                "price",
                "fee",
                "modem",
                "router",
                "connection",
                "signal",
                "sim",
                "roaming",
                "activation",
                "installation",
                "contract",
                "commitment",
                "outage",
                "speed",
                "gb",
                "mbps",
                "network",
                "customer service",
                "support",
                "account",
                "cancel",
                "refund",
            )
            return any(term in query for term in english_terms)
        stems = (
            "demotel",
            "internet",
            "fiber",
            "mobil",
            "telefon",
            "hat",
            "modem",
            "wifi",
            "wi-fi",
            "kablosuz",
            "fatura",
            "öde",
            "ode",
            "ödeme",
            "odeme",
            "ödedi",
            "tutar",
            "itiraz",
            "taahhüt",
            "taahhut",
            "aboneli",
            "aktivasyon",
            "kurulum",
            "mbps",
            "megabit",
            "gb",
            "kop",
            "kesil",
            "bağlanti",
            "baglanti",
            "ücretim",
            "kampanya",
            "sözleş",
            "taahhüd",
            "paket",
            "roaming",
            "dolaşım",
        )
        tokens = re.findall(r"[a-zçğöşü0-9]+", query)
        general_faq_terms = (
            "asistan",
            "sohbet",
            "konuşma",
            "kişisel bilgi",
            "sms kod",
            "tek kullanımlık kod",
            "destek belgesi",
            "yanıtın kaynağı",
            "bilgi tabanı",
        )
        explicit_support_context = (
            "ayni anda",
            "karttan çekilmiş",
            "borc kapanmamis",
            "data roaming",
            "yurt disi dolasim",
        )
        return (
            any(token.startswith(stem) for token in tokens for stem in stems)
            or any(term in query for term in general_faq_terms)
            or any(term in query for term in explicit_support_context)
        )

    def is_smalltalk(self, text: str, locale: str = "tr-TR") -> bool:
        """Recognize short social turns without sending them to FAQ retrieval."""
        query = re.sub(r"[^a-zçğıöşü ]", " ", self.normalize(text))
        query = " ".join(query.split())
        if locale == "en-US":
            english = {
                "hi",
                "hello",
                "hey",
                "hello there",
                "good morning",
                "good afternoon",
                "good evening",
                "thanks",
                "thank you",
                "thanks a lot",
                "bye",
                "goodbye",
                "how are you",
                "how are you doing",
                "what can you do",
                "how can you help me",
                "can you help me",
                "who are you",
            }
            if query in english:
                return True
            greeting, separator, remainder = query.partition(" ")
            return bool(
                separator
                and greeting in {"hi", "hello", "hey", "good"}
                and remainder
                in {
                    "there",
                    "how are you",
                    "how are you doing",
                    "morning",
                    "afternoon",
                    "evening",
                    "can you help me",
                    "how can you help me",
                    "what can you do",
                }
            )
        phrases = {
            "selam",
            "selamlar",
            "merhaba",
            "hello",
            "hi",
            "hey",
            "günaydın",
            "gunaydin",
            "iyi akşamlar",
            "iyi aksamlar",
            "iyi günler",
            "iyi gunler",
            "iyi geceler",
            "nasılsın",
            "nasilsin",
            "teşekkürler",
            "tesekkurler",
            "teşekkür ederim",
            "tesekkur ederim",
            "sağ ol",
            "sag ol",
            "çok sağ ol",
            "cok sag ol",
            "görüşürüz",
            "gorusuruz",
            "hoşça kal",
            "hosca kal",
        }
        if query in phrases:
            return True
        greeting, separator, remainder = query.partition(" ")
        return bool(
            separator
            and greeting in {"selam", "selamlar", "merhaba", "hello", "hi", "hey"}
            and remainder in {"nasılsın", "nasilsin", "naber", "iyi misin"}
        )

    def blocked(self, text: str) -> bool:
        query = self.normalize(text)
        patterns = [
            r"ignore.{0,30}(previous|instructions|system)",
            r"(önceki|onceki|sistem).{0,30}(talimat|komut).{0,30}(unut|yok say|göster|goster)",
            r"(system prompt|sistem prompt|developer message|jailbreak)",
        ]
        return any(re.search(pattern, query) for pattern in patterns)

    def handoff(self, text: str, locale: str = "tr-TR") -> bool:
        query = self.normalize(text)
        if self.requires_live_account_or_current_data(text, locale):
            return True
        if locale == "en-US":
            return any(
                phrase in query
                for phrase in (
                    "cancel my",
                    "cancel subscription",
                    "close my account",
                    "speak to a person",
                    "human agent",
                    "customer representative",
                    "refund",
                    "change my plan",
                    "upgrade my plan",
                )
            )
        return any(
            phrase in query
            for phrase in (
                "müşteri temsilcisi",
                "musteri temsilcisi",
                "insanla görüş",
                "insanla gorus",
                "aboneliğimi iptal",
                "aboneligimi iptal",
                "hesabimi kapat",
                "iade et",
                "taahhüdümü iptal",
                "taahhudumu iptal",
            )
        )

    def requires_live_account_or_current_data(self, text: str, locale: str = "tr-TR") -> bool:
        """Never answer account operations or live facts from a static FAQ citation."""
        query = self.normalize(text)
        if locale == "en-US":
            current = ("right now", "currently", "today", "live", "latest", "nearest")
            account = (
                "my account balance",
                "my bill amount",
                "my unpaid bill",
                "my balance",
                "my remaining",
                "my usage",
            )
            actions = (
                "check my",
                "show my",
                "book",
                "schedule",
                "activate",
                "assign",
                "calculate my",
                "open my ticket",
                "ticket status",
            )
        else:
            current = (
                "şu anda",
                "su anda",
                "bugün",
                "bugun",
                "canli",
                "anlik",
                "en yakin",
                "son durum",
                "kesin randevu",
            )
            account = (
                "aboneligimde",
                "hesabimin",
                "benim hesab",
                "benim fatura",
                "kalan mobil",
                "kalan internet",
                "hattima",
                "sokak numaram",
            )
            actions = (
                "sorgula",
                "getir",
                "tanimla",
                "randevu ver",
                "hesapla",
                "kayit ac",
                "kaydi ac",
            )
        return any(phrase in query for phrase in (*current, *account)) or any(
            re.search(rf"\b{re.escape(phrase)}\b", query) for phrase in actions
        )

    def intent(self, text: str, locale: str = "tr-TR") -> str:
        query = self.normalize(text)
        if locale == "en-US":
            if any(
                word in query for word in ("bill", "payment", "pay", "invoice", "charge", "refund")
            ):
                return "billing"
            if any(
                word in query
                for word in (
                    "modem",
                    "router",
                    "wifi",
                    "wi-fi",
                    "slow",
                    "disconnect",
                    "connection",
                    "signal",
                    "sim",
                    "roaming",
                    "outage",
                    "password",
                )
            ):
                return "technical"
            if any(
                word in query
                for word in (
                    "plan",
                    "package",
                    "price",
                    "fiber",
                    "mobile",
                    "data",
                    "gb",
                    "mbps",
                    "tariff",
                )
            ):
                return "packages"
            return "general"
        if any(
            word in query for word in ("fatura", "ödeme", "odeme", "tutar", "itiraz", "ücretim")
        ):
            return "billing"
        if any(
            word in query
            for word in (
                "modem",
                "wifi",
                "wi-fi",
                "yavaş",
                "yavas",
                "kop",
                "kirmizi",
                "kesiliyor",
                "parola",
                "şifre",
            )
        ):
            return "technical"
        if any(
            word in query for word in ("paket", "tarife", "fiyat", "mbps", "fiber", "mobil", "gb")
        ):
            return "packages"
        return "general"

    def followup(self, text: str) -> bool:
        query = self.normalize(text).strip()
        return query.startswith(
            (
                "peki",
                "bunu",
                "bunun",
                "o zaman",
                "bu durumda",
                "what about",
                "and ",
                "then",
                "how about",
                "what if",
            )
        )
