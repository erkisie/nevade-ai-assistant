# Nevade AI Assistant

Nevade AI Assistant, e-ticaret ve mağaza satış süreçlerini desteklemek için geliştirilmiş yapay zekâ destekli bir ürün öneri ve müşteri destek uygulamasıdır. Proje, müşteri taleplerini analiz ederek katalogdaki ürünleri; fiyat, stok, ödeme yöntemi, senetli ödeme, havale, taksit ve kullanım amacına göre sıralar. Sistem Gemini LLM ile cevap üretmeyi dener; Gemini kotası dolduğunda veya servis hatası oluştuğunda uygulama kesintiye uğramadan güvenli fallback karar motoru ile çalışmaya devam eder.

## 🚀 Proje Amacı

Bu projenin amacı, Nevade tarzı bir e-ticaret/mağaza sisteminde müşterilere ve mağaza personeline daha hızlı, doğru ve veriye dayalı yanıtlar sunan bir AI destekli asistan geliştirmektir.

Uygulama şu ihtiyaçlara çözüm üretir:

* Müşteri sorularını analiz etme
* Ürün önerisi sunma
* Bütçeye göre ürün filtreleme
* Senetli ödeme, havale ve taksit seçeneklerini karşılaştırma
* Çeyiz paketi gibi paket taleplerini değerlendirme
* Stok ve ödeme bilgilerini düzenli şekilde gösterme
* Mağaza personeline müşteriye söylenebilecek hazır cevap üretme
* Gemini API hatası veya kota problemi olduğunda fallback sistemle çalışmaya devam etme

## 🧠 AI Çalışma Mantığı

Sistem hibrit bir AI yapısına sahiptir.

Öncelikli akış:

1. Kullanıcı sorusu alınır.
2. NLP motoru ile niyet, bütçe, ürün tipi, marka ve ödeme tercihi analiz edilir.
3. Ürün filtresi ve karar motoru çalışır.
4. Gemini LLM ile doğal dilde cevap üretilmeye çalışılır.
5. Gemini kota/hata verirse sistem kapanmaz.
6. Fallback karar motoru doğrulanmış ürün verilerine göre temiz cevap üretir.

Çalışma mantığı:

```text
Gemini aktifse        → Gemini cevabı
Gemini kota dolarsa  → Fallback cevabı
Gemini hata verirse  → Fallback cevabı
```

Bu sayede uygulama API kotası dolsa bile kullanılabilir kalır.

## 🛒 Temel Özellikler

* AI destekli ürün öneri sistemi
* Müşteri ve mağaza personeli modu
* Ürün arama ve filtreleme
* Kategori, marka, fiyat ve ödeme tercihi analizi
* Senetli ödeme hesaplama
* Havale fiyatı ve taksit bilgisi gösterimi
* Çeyiz paketi / paket ürün önerisi
* Sepet sistemi
* Sipariş takip simülasyonu
* Guardrail güvenlik kontrolü
* Hafıza ve kullanıcı davranış kaydı yapısı
* Streamlit tabanlı modern arayüz
* Premium CSS tasarım entegrasyonu
* Gemini API entegrasyonu
* Gemini hata durumunda fallback cevap sistemi

## 🧩 Kullanılan Teknolojiler

* Python
* Streamlit
* Pandas
* Gemini API
* HTML / CSS
* Regex
* CSV tabanlı ürün verisi
* Modüler Python dosya yapısı

## 📁 Proje Yapısı

```text
nevade-ai-assistant/
│
├── app_premium.py
├── assets/
│   └── app_design.css
│
├── data/
│   └── products.csv
│
├── src/
│   ├── decision_engine.py
│   ├── nlp_engine.py
│   ├── product_filter_engine.py
│   ├── package_engine.py
│   ├── semantic_engine.py
│   ├── guardrail_engine.py
│   ├── response_engine.py
│   ├── memory_engine.py
│   ├── metrics_engine.py
│   ├── vision_engine.py
│   └── llm_provider_router.py
│
├── requirements.txt
└── README.md
```

## ⚙️ Kurulum

Öncelikle projeyi klonlayın:

```bash
git clone https://github.com/erkisie/nevade-ai-assistant.git
cd nevade-ai-assistant
```

Sanal ortam oluşturun:

```bash
python -m venv venv
```

Windows için sanal ortamı aktif edin:

```bash
venv\Scripts\activate
```

Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

## 🔑 Gemini API Ayarı

Gemini API kullanmak için API anahtarınızı ortam değişkeni olarak tanımlayın.

PowerShell için:

```powershell
$env:GEMINI_API_KEY="API_KEYINIZI_BURAYA_YAZIN"
```

Alternatif olarak `.env` veya Streamlit secrets yapısı kullanılabilir.

## ▶️ Uygulamayı Çalıştırma

```bash
streamlit run app_premium.py
```

Uygulama açıldığında tarayıcı üzerinden kullanılabilir.

Genellikle şu adreste çalışır:

```text
http://localhost:8501
```

## 👤 Demo Kullanıcılar

Projede test amaçlı demo kullanıcı rolleri bulunur:

```text
admin@nevade.com   / 1234
magaza@nevade.com  / 1234
musteri@nevade.com / 1234
```

## 💬 Örnek Kullanım Soruları

Müşteri modu için:

```text
50.000 TL bütçem var çeyiz paketi önerir misin?
Beko buzdolabı senetle olur mu?
Samsung televizyon havale fiyatı ne kadar?
Öğrenci için laptop önerir misin?
En uygun ödeme seçeneği hangisi?
```

Mağaza personeli modu için:

```text
Müşteri senetli buzdolabı soruyor, ne söylemeliyim?
Bu ürün stokta mı?
Havale mi daha avantajlı taksit mi?
NVD-1001 sipariş durumu nedir?
```

## 🧠 Fallback Sistemi

Projede Gemini API kotası dolduğunda uygulama hata verip durmaz. Bunun yerine fallback cevap sistemi devreye girer.

Örnek terminal çıktısı:

```text
Gemini LLM hata: 429 RESOURCE_EXHAUSTED
AI PROVIDER: FALLBACK
```

Bu durumda sistem:

* Ürün verisini kullanır
* Fiyat uydurmaz
* Stok bilgisini mevcut veriden alır
* Ödeme seçeneklerini katalogdaki değerlere göre açıklar
* Kullanıcıya sade ve güvenilir cevap verir

Bu yapı, uygulamanın gerçek kullanımda daha dayanıklı olmasını sağlar.

## 🎨 Arayüz Tasarımı

Uygulama premium bir e-ticaret asistanı görünümü hedefler.

Tasarımda:

* Nevade mavi tonu
* Lacivert
* Turuncu
* Mor
* Pembe geçişler
* Cam efektli paneller
* Modern ürün kartları
* Chat paneli
* Dashboard alanları

kullanılmıştır.

CSS dosyası:

```text
assets/app_design.css
```

## 📊 Ürün Verisi

Ürünler varsayılan olarak şu dosyadan okunur:

```text
data/products.csv
```

CSV dosyası yoksa uygulama demo ürün verisiyle çalışır.

Örnek ürün alanları:

```text
product_id
product_name
category
brand
price
cash_price
bank_transfer_price
card_price
installment_6_total
senet_total_price
senet_monthly_9
stock_status
payment_options
features
description
```

## 🛡️ Güvenlik ve Guardrail

Sistem, kullanıcı sorularını cevaplamadan önce guardrail kontrolünden geçirir.

Bu sayede:

* Alakasız talepler filtrelenir
* Güvensiz içerikler engellenir
* Rakip karşılaştırmaları kontrollü cevaplanır
* Ürün dışı talepler sınırlandırılır
* Yanıltıcı veya uydurma bilgi üretimi azaltılır

## 📌 Projenin Güçlü Yönleri

* Gerçek e-ticaret senaryosuna uygun yapı
* LLM + fallback hibrit mimari
* API kotası dolsa bile çalışmaya devam etme
* Ürün, ödeme ve stok odaklı karar motoru
* Müşteri ve mağaza personeli için ayrı kullanım akışı
* Modüler Python yapısı
* Geliştirilebilir veri ve motor mimarisi
* Modern Streamlit arayüzü

## 🔮 Geliştirilebilir Özellikler

İlerleyen aşamalarda projeye şu özellikler eklenebilir:

* Gerçek veritabanı bağlantısı
* Kullanıcı kayıt sistemi
* Canlı stok entegrasyonu
* Gerçek sipariş API bağlantısı
* Gelişmiş ürün görsel arama
* Daha büyük LLM modeli entegrasyonu
* Admin paneli
* Raporlama ekranları
* Satış performans analitiği
* WhatsApp / web chat entegrasyonu

## 👩‍💻 Geliştirici

Bu proje, staj ve portfolyo çalışması kapsamında geliştirilmiştir.

**Geliştirici:** Elif Erkisi
**GitHub:** [erkisie](https://github.com/erkisie)
**Proje:** Nevade AI Assistant

## 📝 Lisans

Bu proje eğitim, staj ve portfolyo amacıyla geliştirilmiştir. Ticari kullanım için proje sahibinden izin alınması önerilir.
