"""Transparent local policy checks; no account-changing tools are exposed."""

import re
import unicodedata


class PolicyService:
    @staticmethod
    def normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text).lower().replace("\u0307", "").replace("ı", "i")

    def supported(self, text: str) -> bool:
        """Conservative demo scope; generic prices or advice need telecom context."""
        query = self.normalize(text).replace("wi-fi", "wifi")
        if self.is_smalltalk(text):
            return True
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
        )
        tokens = re.findall(r"[a-zçğöşü0-9]+", query)
        return any(token.startswith(stem) for token in tokens for stem in stems)

    def is_smalltalk(self, text: str) -> bool:
        """Recognize short social turns without sending them to FAQ retrieval."""
        query = re.sub(r"[^a-zçğıöşü ]", " ", self.normalize(text))
        query = " ".join(query.split())
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

    def handoff(self, text: str) -> bool:
        query = self.normalize(text)
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

    def intent(self, text: str) -> str:
        query = self.normalize(text)
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
        return query.startswith(("peki", "bunu", "bunun", "o zaman", "bu durumda"))
