import os
import random
import pandas as pd
from urllib.parse import quote_plus


os.makedirs("data", exist_ok=True)
random.seed(42)


def image_url(query, lock_id):
    """
    Demo amaçlı kategori görseli üretir.
    Gerçek ürün fotoğrafı değildir.
    """
    q = quote_plus(query)
    return f"https://loremflickr.com/640/480/{q}?lock={lock_id}"


def price_options(price):
    cash_price = round(price * 0.98)
    bank_transfer_price = round(price * 0.96)
    card_price = price
    installment_3_total = round(price * 1.04)
    installment_6_total = round(price * 1.08)
    installment_9_total = round(price * 1.14)
    senet_total_price = round(price * 1.27)
    senet_monthly_9 = round(senet_total_price / 9)

    return {
        "cash_price": cash_price,
        "bank_transfer_price": bank_transfer_price,
        "card_price": card_price,
        "installment_3_total": installment_3_total,
        "installment_6_total": installment_6_total,
        "installment_9_total": installment_9_total,
        "senet_total_price": senet_total_price,
        "senet_monthly_9": senet_monthly_9,
    }


def make_product(
    product_id,
    product_name,
    category,
    brand,
    price,
    color="",
    processor="",
    ram="",
    storage="",
    screen_size="",
    energy_class="",
    capacity="",
    warranty="2 yıl",
    stock_status="Stokta",
    use_case="",
    features="",
    description="",
    image_query="product"
):
    payments = price_options(price)

    return {
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "brand": brand,
        "price": price,
        "cash_price": payments["cash_price"],
        "bank_transfer_price": payments["bank_transfer_price"],
        "card_price": payments["card_price"],
        "installment_3_total": payments["installment_3_total"],
        "installment_6_total": payments["installment_6_total"],
        "installment_9_total": payments["installment_9_total"],
        "senet_total_price": payments["senet_total_price"],
        "senet_monthly_9": payments["senet_monthly_9"],
        "color": color,
        "processor": processor,
        "ram": ram,
        "storage": storage,
        "screen_size": screen_size,
        "energy_class": energy_class,
        "capacity": capacity,
        "warranty": warranty,
        "stock_status": stock_status,
        "installment_available": "Evet",
        "payment_options": "Peşin, havale, kredi kartı, taksit, senet",
        "use_case": use_case,
        "features": features,
        "description": description,
        "product_link": "",
        "image_link": image_url(image_query, product_id),
    }


products = []
pid = 1001


# =====================================================
# LAPTOP / BİLGİSAYAR
# =====================================================

laptop_data = [
    ("Lenovo", "IdeaPad Slim 3", "Intel i5", "8 GB", "512 GB SSD", "15.6 inç", 21999, "öğrenci, okul, günlük kullanım"),
    ("Lenovo", "ThinkBook 15", "Intel i7", "16 GB", "1 TB SSD", "15.6 inç", 38999, "ofis, iş, çoklu görev"),
    ("HP", "Pavilion 15", "Ryzen 5", "16 GB", "512 GB SSD", "15.6 inç", 28999, "öğrenci, ofis, günlük kullanım"),
    ("HP", "Victus Gaming", "Intel i7", "16 GB", "1 TB SSD", "16 inç", 52999, "oyun, performans, yüksek hız"),
    ("Asus", "VivoBook 15", "Intel i5", "8 GB", "512 GB SSD", "15.6 inç", 24999, "öğrenci, taşınabilir, günlük kullanım"),
    ("Asus", "ZenBook 14", "Ryzen 7", "16 GB", "1 TB SSD", "14 inç", 45999, "hafif, premium, iş kullanımı"),
    ("Apple", "MacBook Air M1", "Apple M1", "8 GB", "256 GB SSD", "13.3 inç", 34999, "öğrenci, hafif, uzun pil"),
    ("Apple", "MacBook Air M2", "Apple M2", "8 GB", "512 GB SSD", "13.6 inç", 48999, "öğrenci, tasarım, premium kullanım"),
    ("Dell", "Inspiron 15", "Intel i5", "16 GB", "512 GB SSD", "15.6 inç", 31999, "ofis, ev, günlük kullanım"),
    ("MSI", "Modern 15", "Ryzen 7", "16 GB", "1 TB SSD", "15.6 inç", 42999, "performans, yazılım, çoklu görev"),
]

for item in laptop_data:
    brand, model, processor, ram, storage, screen, price, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model} Laptop",
        category="Bilgisayar",
        brand=brand,
        price=price,
        color=random.choice(["Gri", "Siyah", "Gümüş", "Mavi"]),
        processor=processor,
        ram=ram,
        storage=storage,
        screen_size=screen,
        use_case=use_case,
        features=f"{processor} işlemci, {ram} RAM, {storage}, {screen} ekran, hızlı ve taşınabilir tasarım",
        description=f"{brand} {model}, {use_case} için uygun, performans ve taşınabilirliği birlikte sunan bir laptop modelidir.",
        image_query="laptop computer"
    ))
    pid += 1


# =====================================================
# TELEFON
# =====================================================

phone_data = [
    ("Apple", "iPhone 13", "4 GB", "128 GB", "6.1 inç", 32999, "günlük kullanım, kamera, sosyal medya"),
    ("Apple", "iPhone 14", "6 GB", "128 GB", "6.1 inç", 41999, "premium telefon, kamera, uzun kullanım"),
    ("Apple", "iPhone 15", "6 GB", "128 GB", "6.1 inç", 52999, "premium telefon, güçlü kamera, hızlı performans"),
    ("Apple", "iPhone 15 Pro", "8 GB", "256 GB", "6.1 inç", 74999, "üst seviye kamera, performans, profesyonel kullanım"),
    ("Samsung", "Galaxy A55", "8 GB", "256 GB", "6.6 inç", 22999, "uygun fiyatlı telefon, günlük kullanım"),
    ("Samsung", "Galaxy S24", "8 GB", "256 GB", "6.2 inç", 52999, "amiral gemisi, kamera, performans"),
    ("Xiaomi", "Redmi Note 13", "8 GB", "256 GB", "6.6 inç", 13999, "uygun fiyatlı telefon, günlük kullanım"),
    ("Xiaomi", "Redmi Note 13 Pro", "12 GB", "512 GB", "6.7 inç", 21999, "fiyat performans, kamera, oyun"),
    ("Oppo", "Reno 11", "8 GB", "256 GB", "6.7 inç", 18999, "kamera, şık tasarım, sosyal medya"),
    ("Realme", "12 Pro", "12 GB", "256 GB", "6.7 inç", 19999, "performans, kamera, günlük kullanım"),
]

for item in phone_data:
    brand, model, ram, storage, screen, price, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model} Telefon",
        category="Telefon",
        brand=brand,
        price=price,
        color=random.choice(["Siyah", "Beyaz", "Mavi", "Yeşil", "Mor"]),
        ram=ram,
        storage=storage,
        screen_size=screen,
        use_case=use_case,
        features=f"{ram} RAM, {storage} depolama, {screen} ekran, güçlü kamera ve hızlı şarj",
        description=f"{brand} {model}, {use_case} için uygun, modern tasarıma sahip bir akıllı telefondur.",
        image_query="smartphone"
    ))
    pid += 1


# =====================================================
# BUZDOLABI
# =====================================================

fridge_data = [
    ("Beko", "No Frost Buzdolabı", 24000, "514 L", "A+", "aile kullanımı, geniş hacim, çeyiz"),
    ("Arçelik", "No Frost Buzdolabı", 31500, "560 L", "A++", "geniş aile, enerji tasarrufu, mutfak"),
    ("Bosch", "Kombi Tipi Buzdolabı", 42999, "480 L", "A++", "sessiz çalışma, enerji verimliliği"),
    ("Siemens", "No Frost Buzdolabı", 45999, "520 L", "A++", "premium mutfak, geniş hacim"),
    ("Samsung", "Gardırop Tipi Buzdolabı", 63999, "620 L", "A++", "büyük aile, yüksek kapasite"),
    ("LG", "Inverter Buzdolabı", 58999, "600 L", "A+++", "enerji tasarrufu, geniş aile"),
    ("Vestel", "Ekonomik Buzdolabı", 19999, "420 L", "A+", "uygun fiyat, günlük kullanım"),
    ("Beko", "Çift Kapılı Buzdolabı", 21999, "450 L", "A+", "çeyiz, uygun fiyat, aile"),
]

for item in fridge_data:
    brand, model, price, capacity, energy, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model}",
        category="Beyaz Eşya",
        brand=brand,
        price=price,
        color=random.choice(["Beyaz", "İnox", "Gri", "Siyah"]),
        energy_class=energy,
        capacity=capacity,
        use_case=use_case,
        features=f"{capacity} kapasite, {energy} enerji sınıfı, no frost soğutma, sessiz motor",
        description=f"{brand} {model}, {use_case} için uygun, geniş hacimli ve enerji verimli bir buzdolabıdır.",
        image_query="refrigerator kitchen"
    ))
    pid += 1


# =====================================================
# ÇAMAŞIR MAKİNESİ
# =====================================================

washer_data = [
    ("Beko", "8 kg Çamaşır Makinesi", 17500, "8 kg", "A+", "çeyiz, günlük yıkama, uygun fiyat"),
    ("Arçelik", "9 kg Çamaşır Makinesi", 21999, "9 kg", "A++", "aile kullanımı, sessiz çalışma"),
    ("Bosch", "10 kg Çamaşır Makinesi", 32999, "10 kg", "A+++", "yüksek kapasite, enerji tasarrufu"),
    ("Siemens", "9 kg Çamaşır Makinesi", 35999, "9 kg", "A++", "premium kullanım, sessiz motor"),
    ("Samsung", "EcoBubble Çamaşır Makinesi", 28999, "9 kg", "A++", "hassas yıkama, aile kullanımı"),
    ("LG", "Inverter Çamaşır Makinesi", 31999, "10 kg", "A+++", "sessiz çalışma, enerji verimliliği"),
    ("Vestel", "7 kg Çamaşır Makinesi", 13999, "7 kg", "A+", "uygun fiyat, küçük aile"),
]

for item in washer_data:
    brand, model, price, capacity, energy, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model}",
        category="Beyaz Eşya",
        brand=brand,
        price=price,
        color=random.choice(["Beyaz", "Gri", "İnox"]),
        energy_class=energy,
        capacity=capacity,
        use_case=use_case,
        features=f"{capacity} yıkama kapasitesi, {energy} enerji sınıfı, hızlı yıkama, sessiz çalışma",
        description=f"{brand} {model}, {use_case} için uygun, tasarruflu ve kullanışlı bir çamaşır makinesidir.",
        image_query="washing machine laundry"
    ))
    pid += 1


# =====================================================
# TELEVİZYON
# =====================================================

tv_data = [
    ("Samsung", "55 inç 4K Smart TV", 26999, "55 inç", "A+", "film, dizi, oyun, salon kullanımı"),
    ("LG", "55 inç OLED TV", 49999, "55 inç", "A", "premium görüntü, sinema deneyimi"),
    ("TCL", "50 inç Android TV", 17999, "50 inç", "A+", "uygun fiyat, akıllı TV"),
    ("Vestel", "43 inç Smart TV", 12999, "43 inç", "A+", "ekonomik televizyon, günlük kullanım"),
    ("Philips", "Ambilight 65 inç TV", 42999, "65 inç", "A", "sinema, büyük ekran, salon"),
    ("Sony", "Bravia 65 inç 4K TV", 54999, "65 inç", "A", "yüksek görüntü kalitesi, oyun"),
    ("Samsung", "65 inç QLED TV", 58999, "65 inç", "A", "premium salon, yüksek parlaklık"),
]

for item in tv_data:
    brand, model, price, screen, energy, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model}",
        category="Televizyon",
        brand=brand,
        price=price,
        color="Siyah",
        screen_size=screen,
        energy_class=energy,
        use_case=use_case,
        features=f"{screen} ekran, 4K çözünürlük, Smart TV, yüksek görüntü kalitesi",
        description=f"{brand} {model}, {use_case} için uygun, net görüntü ve akıllı kullanım sunan bir televizyondur.",
        image_query="television living room"
    ))
    pid += 1


# =====================================================
# EV ELEKTRONİĞİ / KÜÇÜK EV ALETLERİ
# =====================================================

home_data = [
    ("Dyson", "V12 Dikey Süpürge", "Ev Elektroniği", 28999, "kablosuz süpürge, güçlü çekim, pratik temizlik", "vacuum cleaner"),
    ("Philips", "PowerPro Süpürge", "Ev Elektroniği", 8999, "günlük temizlik, uygun fiyat, güçlü emiş", "vacuum cleaner"),
    ("Tefal", "Easy Fry Airfryer", "Ev Elektroniği", 5999, "sağlıklı pişirme, mutfak, pratik kullanım", "air fryer"),
    ("Karaca", "Türk Kahve Makinesi", "Ev Elektroniği", 3499, "kahve, mutfak, pratik kullanım", "coffee machine"),
    ("Arzum", "Çay Makinesi", "Ev Elektroniği", 2499, "çay, mutfak, günlük kullanım", "tea maker"),
    ("Fakir", "Blender Seti", "Ev Elektroniği", 1999, "mutfak hazırlık, pratik kullanım", "blender"),
    ("Philips", "Buharlı Ütü", "Ev Elektroniği", 2999, "kıyafet bakımı, günlük kullanım", "steam iron"),
    ("Xiaomi", "Robot Süpürge", "Ev Elektroniği", 15999, "akıllı temizlik, robot süpürge, ev kullanımı", "robot vacuum"),
    ("Bosch", "Mutfak Robotu", "Ev Elektroniği", 7999, "mutfak, hamur, yemek hazırlık", "food processor"),
    ("Tefal", "Tost Makinesi", "Ev Elektroniği", 2799, "kahvaltı, mutfak, pratik kullanım", "sandwich maker"),
]

for item in home_data:
    brand, model, category, price, use_case, img_query = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=f"{brand} {model}",
        category=category,
        brand=brand,
        price=price,
        color=random.choice(["Siyah", "Beyaz", "Gri", "Kırmızı"]),
        use_case=use_case,
        features=f"{use_case}, kompakt tasarım, kolay kullanım",
        description=f"{brand} {model}, {use_case} için uygun, ev kullanımını kolaylaştıran bir üründür.",
        image_query=img_query
    ))
    pid += 1


# =====================================================
# ÇEYİZ PAKETLERİ / BUNDLE
# =====================================================

bundle_data = [
    ("Beko Çeyiz Beyaz Eşya Paketi", "Beko", 49999, "buzdolabı, çamaşır makinesi, küçük ev aleti, çeyiz"),
    ("Arçelik Yeni Ev Paketi", "Arçelik", 57999, "çeyiz, beyaz eşya, yeni ev kurulum"),
    ("Vestel Ekonomik Çeyiz Paketi", "Vestel", 39999, "uygun fiyat, çeyiz, temel beyaz eşya"),
    ("Bosch Premium Ev Paketi", "Bosch", 72999, "premium beyaz eşya, enerji tasarrufu, aile"),
]

for item in bundle_data:
    name, brand, price, use_case = item
    products.append(make_product(
        product_id=f"P{pid}",
        product_name=name,
        category="Beyaz Eşya",
        brand=brand,
        price=price,
        color="Karışık",
        energy_class="A++",
        capacity="Paket",
        use_case=use_case,
        features="çeyiz paketi, yeni ev kurulumu, beyaz eşya kombinasyonu, ödeme avantajı",
        description=f"{name}, yeni ev kuran veya çeyiz hazırlayan kullanıcılar için hazırlanmış demo ürün paketidir.",
        image_query="home appliances kitchen"
    ))
    pid += 1


df = pd.DataFrame(products)

df.to_csv("data/products.csv", index=False, encoding="utf-8-sig")

print("Türkçe resimli ürün seti oluşturuldu.")
print(f"Toplam ürün sayısı: {len(df)}")
print("Dosya: data/products.csv")