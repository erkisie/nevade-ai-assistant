import re
import pandas as pd


# =====================================================
# PRODUCT FILTER ENGINE
# Amaç:
# Kullanıcı net ürün tipi söylediyse başka ürünlerin karışmasını engeller.
# =====================================================


def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }

    for tr_char, simple_char in replacements.items():
        text = text.replace(tr_char, simple_char)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


PACKAGE_WORDS = [
    "ceyiz",
    "çeyiz",
    "paket",
    "set",
    "ev diziyorum",
    "ev kuruyorum",
    "evleniyorum",
    "dugun",
    "düğün",
    "beyaz esya paketi",
    "beyaz eşya paketi",
]


PRODUCT_TYPE_KEYWORDS = {
    "buzdolabi": [
        "buzdolabi",
        "buz dolabi",
        "buzdolabı",
        "buz dolabı",
        "no frost",
        "mini buzdolabi",
        "mini buzdolabı",
        "mini bar",
        "minibar",
        "sogutucu",
        "soğutucu",
        "derin dondurucu",
        "icecek saklama",
        "içecek saklama",
        "soguk icecek",
        "soğuk içecek",
    ],

    "camasir_makinesi": [
        "camasir makinesi",
        "çamaşır makinesi",
        "camasir",
        "çamaşır",
        "yikama makinesi",
        "yıkama makinesi",
    ],

    "bulasik_makinesi": [
        "bulasik makinesi",
        "bulaşık makinesi",
        "bulasik",
        "bulaşık",
    ],

    "televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "akilli tv",
        "akıllı tv",
        "led tv",
        "oled",
        "qled",
        "inc tv",
        "inç tv",
    ],

    "supurge": [
        "supurge",
        "süpürge",
        "elektrikli supurge",
        "elektrikli süpürge",
        "dikey supurge",
        "dikey süpürge",
        "robot supurge",
        "robot süpürge",
        "temizlik",
    ],

    "laptop": [
        "laptop",
        "notebook",
        "bilgisayar",
        "oyun bilgisayari",
        "oyun bilgisayarı",
        "ogrenci bilgisayari",
        "öğrenci bilgisayarı",
        "gaming",
    ],

    "telefon": [
        "telefon",
        "cep telefonu",
        "iphone",
        "samsung galaxy",
        "galaxy",
        "android",
        "akilli telefon",
        "akıllı telefon",
    ],

    "klima": [
        "klima",
        "inverter klima",
        "sogutma",
        "soğutma",
        "isitma",
        "ısıtma",
    ],

    "firin": [
        "firin",
        "fırın",
        "ankastre",
        "ankastre firin",
        "ankastre fırın",
        "ocak",
    ],
}


def is_package_query(question):
    q = normalize_text(question)

    for word in PACKAGE_WORDS:
        if normalize_text(word) in q:
            return True

    return False


def detect_product_types(question):
    """
    Kullanıcı sorusundan net ürün tipi çıkarır.
    """

    q = normalize_text(question)
    detected = []

    for product_type, keywords in PRODUCT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                detected.append(product_type)
                break

    cleaned = []

    for item in detected:
        if item not in cleaned:
            cleaned.append(item)

    return cleaned


def row_to_search_text(row):
    fields = [
        "product_name",
        "category",
        "brand",
        "description",
        "features",
        "use_case",
        "payment_options",
    ]

    parts = []

    for field in fields:
        try:
            value = row.get(field, "")
        except Exception:
            value = ""

        if value is not None:
            parts.append(str(value))

    return normalize_text(" ".join(parts))


def product_matches_type(row, product_type):
    text = row_to_search_text(row)

    if product_type == "buzdolabi":
        return (
            "buzdolabi" in text
            or "buz dolabi" in text
            or "no frost" in text
            or "mini bar" in text
            or "minibar" in text
            or "sogutucu" in text
            or "derin dondurucu" in text
        )

    if product_type == "camasir_makinesi":
        return (
            "camasir" in text
            and "bulasik" not in text
        )

    if product_type == "bulasik_makinesi":
        return "bulasik" in text

    if product_type == "televizyon":
        return (
            "televizyon" in text
            or "smart tv" in text
            or "akilli tv" in text
            or "led tv" in text
            or "oled" in text
            or "qled" in text
            or re.search(r"\btv\b", text) is not None
        )

    if product_type == "supurge":
        return (
            "supurge" in text
            or "temizlik" in text
            or "robot supurge" in text
            or "dikey supurge" in text
        )

    if product_type == "laptop":
        return (
            "laptop" in text
            or "notebook" in text
            or "bilgisayar" in text
            or "gaming" in text
        )

    if product_type == "telefon":
        return (
            "telefon" in text
            or "iphone" in text
            or "galaxy" in text
            or "android" in text
        )

    if product_type == "klima":
        return "klima" in text

    if product_type == "firin":
        return (
            "firin" in text
            or "ankastre" in text
            or "ocak" in text
        )

    return False


def strict_filter_products(products_df, question, allow_package_mix=True):
    """
    Ana filtre fonksiyonu.

    products_df: ürün dataframe
    question: kullanıcı sorusu
    allow_package_mix: çeyiz/paket sorgularında kategori karışmasına izin verir
    """

    if products_df is None or products_df.empty:
        return products_df, {
            "active": False,
            "reason": "Ürün tablosu boş.",
            "detected_types": [],
            "package_query": False,
        }

    package_query = is_package_query(question)

    if package_query and allow_package_mix:
        return products_df.copy(), {
            "active": False,
            "reason": "Paket / çeyiz isteği algılandı. Çoklu kategoriye izin verildi.",
            "detected_types": [],
            "package_query": True,
        }

    detected_types = detect_product_types(question)

    if not detected_types:
        return products_df.copy(), {
            "active": False,
            "reason": "Net ürün tipi algılanmadı. Genel arama serbest bırakıldı.",
            "detected_types": [],
            "package_query": False,
        }

    filtered_parts = []

    for product_type in detected_types:
        part = products_df[
            products_df.apply(
                lambda row: product_matches_type(row, product_type),
                axis=1
            )
        ]

        if not part.empty:
            filtered_parts.append(part)

    if not filtered_parts:
        return products_df.iloc[0:0].copy(), {
            "active": True,
            "reason": "Net ürün tipi algılandı ancak katalogda uygun ürün bulunamadı.",
            "detected_types": detected_types,
            "package_query": False,
        }

    filtered_df = pd.concat(filtered_parts).drop_duplicates()

    return filtered_df.copy(), {
        "active": True,
        "reason": f"Strict ürün filtresi aktif. Sadece şu ürün tipleri değerlendirildi: {', '.join(detected_types)}",
        "detected_types": detected_types,
        "package_query": False,
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    test_products = pd.DataFrame(
        [
            {
                "product_name": "Beko No Frost Buzdolabı 500 L",
                "category": "Beyaz Eşya",
                "brand": "Beko",
                "description": "Geniş hacimli No Frost buzdolabı",
                "features": "No Frost, sessiz çalışma",
                "use_case": "Çeyiz ve ev kullanımı",
                "payment_options": "Senet, havale, kredi kartı",
            },
            {
                "product_name": "Samsung 50 inç Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "description": "4K akıllı televizyon",
                "features": "Smart TV, 4K",
                "use_case": "Salon",
                "payment_options": "Senet, havale, kredi kartı",
            },
            {
                "product_name": "Lenovo IdeaPad Laptop",
                "category": "Bilgisayar",
                "brand": "Lenovo",
                "description": "Öğrenci ve ofis için laptop",
                "features": "16 GB RAM, SSD",
                "use_case": "Öğrenci, ofis",
                "payment_options": "Kredi kartı, havale",
            },
        ]
    )

    test_questions = [
        "Buzdolabı senetle olur mu?",
        "Laptop lazım öğrenci için",
        "Televizyon öner",
        "100 bin TL çeyiz paketi yap",
    ]

    for question in test_questions:
        print("\nSORU:", question)
        result_df, info = strict_filter_products(test_products, question)
        print(info)
        print(result_df["product_name"].tolist())