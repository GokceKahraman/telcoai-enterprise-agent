# TelcoAI kısa demo anlatımı

**Yaklaşık 75 saniye**

> “Bu proje, Türkçe telekom destek talepleri için kaynak gösteren ve gerektiğinde yanıt vermekten kaçınan bir destek asistanı. Önce aynı 40 FAQ ve aynı 64 soruluk geliştirme kümesi üzerinde arama yöntemlerini karşılaştırıyorum. Keyword, dense semantic, BM25 ve dense+sparse hibrit sonuçları aynı Hit@1, Hit@3, MRR, destek dışı kabul oranı ve gecikme ölçütleriyle raporlanıyor. Bu veri kümesinde keyword baseline en güçlü sıralamayı verdi; dense arama destek dışı sorularda daha temkinli kaldı. Reranker modeli bu ortamda bulunmadığı için o ölçümü tamamlanmış gibi göstermiyorum.
>
> “Şimdi bir fatura sorusu soruyorum. Asistan, ilgili FAQ kaynağını yanıtla birlikte gösteriyor. Ardından gerçek hesap bilgisi gerektiren bir talep veriyorum: kamuya açık FAQ’ları müşteri hesabı gibi kullanmıyor, kimlik doğrulama ve güvenli demo işlem akışına yönlendiriyor. Destek kaydı için hesap kapsamını kontrol edip taslak hazırlıyor; yazma işlemi açık onay ve idempotency anahtarı istiyor.
>
> “Son olarak izleme ve test çıktısında kaynak eşleşmesini, fallback’i ve destek dışı soruları kontrol ediyorum. Buradaki veri ve kayıtlar sentetik. Geliştirme kümesi tuning için kullanıldı; bağımsız kalite iddiası için yeni bir v2 test kümesi gerekir. Daha önce incelenmiş v1 kümesini yalnızca bilinen regresyonu tekrar oynatmak için kullanıyorum.”

## Ekranda gösterilecek kısa sıra

1. `docs/search-matrix-development.json` içindeki aynı-veri karşılaştırma tablosu.
2. “Ödeme kanallarınız neler?” sorgusu ve FAQ kaynak etiketi.
3. Hesaba özgü soru için güvenli fallback veya DemoTel destek talebi taslağı.
4. Kayıt onayı, başvuru referansı ve `docs/evaluation.md` içindeki sınırlamalar.

