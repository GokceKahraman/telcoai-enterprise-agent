# DemoTel conversation and website design

This guide documents the synthetic customer journeys shipped with the portfolio demo. DemoTel, its plans, fees, app and service policies are fictional. The dialogues are original examples informed by public telecom self-service patterns; they are not transcripts and do not reproduce another operator's branded copy.

## Research notes

Public operator support experiences commonly combine topic navigation and search with self-service account tasks. Turkcell's support hub groups help into topics such as plan/usage, billing, roaming and device troubleshooting; its app page describes assistant support alongside request creation and tracking. Vodafone describes TOBi as a digital assistant available across its app, website and messaging, with help for bills, plans and service tasks. AT&T's internet support pages separate equipment restart, status lights, outages and slow-browsing troubleshooting. These patterns informed the demo's topic-first homepage, floating web assistant, short suggested questions, ordered troubleshooting, privacy reminders and explicit human-support boundary.

- [Turkcell support hub](https://www.turkcell.com.tr/destek)
- [Turkcell app and AI assistant overview](https://www.turkcell.com.tr/servisler/uygulamalar/turkcell-uygulamasi)
- [Vodafone TOBi digital assistant](https://www.vodafone.com.tr/yardim/tobi)
- [AT&T internet troubleshooting](https://www.att.com/support/article-modal/fixed-wireless-internet/KM1010340/)

The design borrows general service-design ideas only: let visitors discover help by topic, allow a natural-language question, explain a safe next step, keep account operations behind authenticated channels, and make a human route visible when the assistant cannot verify something. No claim is made that the fictional DemoTel service or these capabilities belong to a real operator.

## Where the data lives

`data/knowledge_base.json` contains **40 fictional FAQ records** across home internet and mobile plans, example pricing, billing, technical support, contracts, and general/privacy questions. Each record has a stable ID, category, Turkish question, curated query keywords and a grounded answer. The answer text includes practical context such as what to check first, how to tell Wi-Fi coverage from a line issue, and what information is safe to share with official support.

Semantic retrieval encodes each record's question and curated keywords; it ranks by vector similarity and returns the selected FAQ answer as source material. The full answer is not currently embedded. In Qdrant hybrid mode, the same question/keyword representation is searched through dense and BM25 sparse vectors and fused with RRF, then optionally re-ranked. This makes retrieval useful for paraphrases such as “fatura çok gelmiş” matching “Fatura tutarı hangi nedenlerle artabilir?” The returned source card is provenance, not account verification or a guarantee that every generated paraphrase is correct.

The corpus is synthetic. Example prices and setup timings in the seeded catalog are explicitly marked fictional in their answers and on the homepage. Do not interpret them as current market research, an operator offer, or a service-level commitment. Real production content should be reviewed against dated, approved tariff and support documents, carry source metadata and expiry/version dates, and be re-indexed with evaluation after policy changes.

## Example support journeys

These are conversation design examples, not guarantees that an enabled LLM will return the exact wording. In the default extractive mode, answers come directly from the selected FAQ entry. In LLM mode, answers are paraphrased from retrieved source entries and recent redacted history under a structured response contract.

### Natural greeting

**Customer:** Selam!

**DemoTel Asistan:** Merhaba! Ben DemoTel destek asistanıyım. Fatura, internet paketi veya bağlantı sorunun hakkında nasıl yardımcı olabilirim?

**Customer:** İnternetim akşamları yavaşlıyor.

**DemoTel Asistan:** Önce hız testini mümkünse Ethernet kablosuyla, arka plandaki indirme ve yayınları durdurarak tekrarla. Kablolu bağlantı normalse sorun Wi-Fi kapsaması veya yoğunlukla ilgili olabilir; kablolu test de düşükse arıza saatlerini not edip resmi destek kanalına ilet.

### Invoice investigation without pretending to access an account

**Customer:** Bu ay faturam beklediğimden yüksek.

**DemoTel Asistan:** Fatura detayında bu dönemle önceki dönemi karşılaştır. Kampanya indirimi, paket aşımı, tek seferlik cihaz/kurulum bedeli ve ek hizmet satırlarına bak. Ben DemoTel hesabına erişemediğim için artışın kesin nedenini göremem; anlaşılmayan bir kalem varsa resmi fatura itirazı kanalından inceleme isteyebilirsin.

**Customer:** Karttan ödedim ama borç hâlâ görünüyor.

**DemoTel Asistan:** Ödeme kanalında işlemin tamamlandığını ve doğru abonelik için yapıldığını doğrula; tekrar ödeme yapmadan önce ekranı yenileyip işlem referansını sakla. Tutar çekildiği hâlde borç görünüyorsa dekontu yalnızca doğrulanmış resmi destek kanalına ilet. Burada ödeme durumunu sorgulayamıyorum.

### Stepwise connection troubleshooting

**Customer:** Evde bazı odalarda Wi-Fi çekmiyor.

**DemoTel Asistan:** Modemi kapalı dolap veya TV arkasından alıp daha merkezi ve açık bir noktaya koy. Aynı cihazla modem yakınında ve sorun yaşadığın odada ölçüm yapabilir misin?

**Customer:** Modemin yanında iyi, yatak odasında kötü.

**DemoTel Asistan:** Bu fark Wi-Fi kapsamasını düşündürüyor. Modem yerini değiştirip tekrar dene; ev planın ve cihaz desteğin uygunsa mesh erişim noktası seçeneklerini inceleyebilirsin. Modem yanında da kablolu test düşük çıkarsa hat tarafını ayrıca kontrol ettirmek gerekir.

### A safe answer about roaming

**Customer:** Yurt dışında mobil interneti açayım mı?

**DemoTel Asistan:** Önce hattında yurt dışı kullanımın ve gideceğin ülkeye uygun paketin açık olup olmadığını resmi kanaldan doğrula; ücretler ülkeye ve şebekeye göre değişir. Özellikle uçak veya gemide uydu şebekesi yüksek ücret çıkarabilir. Ben hattındaki yetkiyi ya da güncel ücreti göremiyorum.

### Human handoff for an account operation

**Customer:** Aboneliğimi iptal et.

**DemoTel Asistan:** Bu demoda abonelik iptal edemem veya hesap bilgilerini göremem. Taahhüt, dönem sonu faturası ve cihaz koşullarını kontrol ederek başvuruyu yalnızca operatörün resmi uygulaması veya doğrulanmış destek kanalı üzerinden ilet. Başvuru referansını sakla.

### Privacy boundary

**Customer:** Sana telefon numaramı ve kimlik numaramı göndereyim mi?

**DemoTel Asistan:** Hayır, bu sohbette telefon, kimlik, adres, parola, kart bilgisi veya tek kullanımlık kod paylaşma. Bu demo hesabına giriş yapmaz; bazı yaygın kişisel veri biçimlerini maskeleyebilse de her bilgiyi yakalayacağı garanti değildir. Kimlik doğrulamasını yalnızca resmi güvenli kanalda yap.

## Website interaction

The public-facing page presents DemoTel as a fictional consumer telecom brand, with home fiber, mobile connection and support sections. A floating support icon opens the assistant as a dialog; Escape, the close button, or the backdrop closes it. The homepage includes suggested customer phrasings that open the same chat with the question ready to send. On narrow screens the assistant becomes a full-height sheet. The chat still shows source cards and demo/privacy boundaries.

The support UI is a portfolio demonstration, not a customer service endpoint. It has no CRM, live network map, payment, order, coverage, or ticket integration. Those tasks must be routed to real authenticated operator channels.
