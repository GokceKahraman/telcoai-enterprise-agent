import pytest

from app.services.privacy import PrivacyService


@pytest.mark.parametrize(
    "text,entity",
    [
        ("Mailim test@example.com", "EMAIL_ADDRESS"),
        ("Telefon +90 (555) 123 45 67", "TR_PHONE"),
        ("Kimlik 12345678901", "TR_ID"),
        ("IBAN TR12 3456 7890 1234 5678 9012 34", "IBAN"),
        ("Kart 4111 1111 1111 1111", "CREDIT_CARD"),
    ],
)
def test_presidio_masks_patterns(text, entity):
    result = PrivacyService().redact(text)
    assert result.changed and entity in result.entities
    assert text != result.text
    assert "DEFAULT" not in result.entities


def test_non_personal_telecom_numbers_remain_intact():
    text = "100 Mbps 549 TL. Modem 192.168.1.1"
    assert PrivacyService().redact(text).text == text
