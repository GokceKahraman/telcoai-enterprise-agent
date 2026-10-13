"""Presidio pattern recognition without downloading an NLP model.

Deliberately narrow coverage: e-mail, Turkish phone/ID, IBAN and card numbers.
This is data minimization, not a claim of complete PII detection or legal compliance.
"""

from dataclasses import dataclass

from presidio_analyzer import Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


@dataclass(frozen=True)
class RedactedText:
    text: str
    entities: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.entities)


class PrivacyService:
    def __init__(self) -> None:
        patterns = {
            "EMAIL_ADDRESS": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
            "TR_PHONE": (
                r"(?<!\d)(?:\+?90[\s.-]?)?0?\(?5\d{2}\)?[\s.-]?"
                r"\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)"
            ),
            "TR_ID": r"(?<!\d)\d{11}(?!\d)",
            "IBAN": r"\bTR[\s-]?(?:\d[\s-]?){24}\b",
            "CREDIT_CARD": r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
        }
        self._recognizers = [
            PatternRecognizer(
                supported_entity=entity,
                supported_language="tr",
                patterns=[Pattern(name=entity, regex=regex, score=0.85)],
            )
            for entity, regex in patterns.items()
        ]
        self._anonymizer = AnonymizerEngine()

    def redact(self, text: str) -> RedactedText:
        results = []
        for recognizer in self._recognizers:
            results.extend(recognizer.analyze(text, entities=recognizer.supported_entities))
        if not results:
            return RedactedText(text, ())
        operators = {
            entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
            for entity in {result.entity_type for result in results}
        }
        entities = tuple(sorted(operators))
        safe = self._anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
        return RedactedText(safe.text, entities)
