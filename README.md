# Nevade AI Destekli Ürün Öneri ve Akıllı Alışveriş Asistanı

Bu proje, Nevade.com ürün verilerini kullanarak kullanıcıların doğal dilde yazdığı ihtiyaçlara göre ürün önerileri sunan AI destekli bir ürün öneri sistemidir.

## Proje Amacı

Kullanıcıların ürünleri daha kolay bulmasını sağlamak, doğal dil ile ürün arama deneyimi oluşturmak ve ürün önerilerini daha açıklanabilir hale getirmek amaçlanmıştır.

## Kullanılan Teknolojiler

- Python
- Pandas
- Scikit-learn
- Streamlit
- TF-IDF
- Cosine Similarity
- CSV / Excel veri yapısı

## Özellikler

- CSV ürün listesi okuma
- Doğal dil ile ürün arama
- TF-IDF ve cosine similarity ile ürün önerisi
- Kategori, fiyat ve stok filtresi
- Benzer ürün önerisi
- Favori ve sepet davranışı analizi
- Chatbot tarzı alışveriş asistanı
- Dashboard ve veri analizi
- Öneri sonuçlarını CSV olarak indirme

## Proje Klasör Yapısı

```text
nevade-ai-assistant/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── products.csv
│   └── user_behavior.csv
│
├── src/
│   ├── recommender.py
│   ├── search_engine.py
│   ├── behavior_analysis.py
│   ├── chatbot.py
│   └── dashboard.py
│
└── assets/