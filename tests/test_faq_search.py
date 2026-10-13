def test_search_finds_package_pricing(keyword_retriever):
    hits = keyword_retriever.retrieve("Ev internet paket fiyatları ne kadar?", top_k=1)
    assert hits
    assert hits[0].entry.id == "price-001"


def test_search_finds_technical_support(keyword_retriever):
    hits = keyword_retriever.retrieve("Modem kırmızı yanıyor internet yok", top_k=1)
    assert hits
    assert hits[0].entry.category == "teknik_destek"


def test_search_returns_empty_for_unrelated(keyword_retriever):
    hits = keyword_retriever.retrieve("xyz rastgele konu", top_k=3)
    assert hits == []


def test_connection_drop_is_covered_by_updated_faq(keyword_retriever):
    hits = keyword_retriever.retrieve("Sürekli kesinti yaşıyorum", top_k=1)
    assert hits
    assert hits[0].entry.id == "tech-001"
