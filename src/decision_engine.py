import re
import pandas as pd


# =====================================================
# TEMEL YARDIMCILAR
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


def safe_number(value):
    try:
        if pd.isna(value):
            return 0

        if isinstance(value, str):
            value = (
                value.replace("TL", "")
                .replace("₺", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )

        return float(value)

    except Exception:
        return 0


def money(value):
    return f"{safe_number(value):,.0f} TL".replace(",", ".")


def row_text(row):
    return normalize_text(
        " ".join(
            [
                str(row.get("product_name", "")),
                str(row.get("category", "")),
                str(row.get("brand", "")),
                str(row.get("description", "")),
                str(row.get("features", "")),
                str(row.get("use_case", "")),
                str(row.get("payment_options", "")),
            ]
        )
    )


# =====================================================
# ÜRÜN TİPİ SÖZLÜĞÜ
# =====================================================

PRODUCT_TYPE_RULES = {
    "buzdolabi": [
        "buzdolabi",
        "buz dolabi",
        "no frost",
        "mini buzdolabi",
        "derin dondurucu",
        "sogutucu",
        "soguk icecek",
        "icecek saklama",
    ],
    "camasir_makinesi": [
        "camasir makinesi",
        "camasir",
        "makine",
        "9 kg",
        "7 kg",
        "yikama",
    ],
    "bulasik_makinesi": [
        "bulasik makinesi",
        "bulasik",
        "4 program",
        "programli bulasik",
    ],
    "televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "akilli tv",
        "led tv",
        "oled",
        "qled",
        "inc tv",
    ],
    "supurge": [
        "supurge",
        "elektrikli supurge",
        "dikey supurge",
        "robot supurge",
        "temizlik",
    ],
    "laptop": [
        "laptop",
        "notebook",
        "bilgisayar",
        "oyun bilgisayari",
        "ogrenci bilgisayari",
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
    ],
    "klima": [
        "klima",
        "inverter klima",
        "sogutma",
        "isitma",
    ],
    "firin": [
        "firin",
        "ankastre firin",
        "ocak",
        "ankastre",
    ],
}


CATEGORY_RULES = {
    "beyaz_esya": [
        "beyaz esya",
        "buzdolabi",
        "camasir",
        "bulasik",
        "firin",
        "klima",
    ],
    "elektronik": [
        "elektronik",
        "televizyon",
        "tv",
        "telefon",
        "laptop",
        "bilgisayar",
    ],
    "kucuk_ev_aleti": [
        "kucuk ev aleti",
        "supurge",
        "kahve",
        "robot",
        "temizlik",
    ],
}


PACKAGE_WORDS = [
    "ceyiz",
    "paket",
    "set",
    "ev diziyorum",
    "ev kuruyorum",
    "evleniyorum",
    "dugun",
]


# =====================================================
# SORUDAN ÜRÜN TİPİ ÇIKARMA
# =====================================================

def detect_strict_product_types(query_info):
    """
    Kullanıcı net ürün tipi söylemişse döndürür.
    Örn: buzdolabı, laptop, telefon.
    """

    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("original_query", "")
        or query_info.get("normalized_query", "")
    )

    detected = []

    existing_types = query_info.get("product_types", []) or []

    for product_type in existing_types:
        norm_type = normalize_text(product_type)

        if norm_type:
            detected.append(norm_type)

    for product_type, keywords in PRODUCT_TYPE_RULES.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                detected.append(product_type)
                break

    # tekrarları temizle
    cleaned = []

    for item in detected:
        if item not in cleaned:
            cleaned.append(item)

    return cleaned


def is_package_query(query_info):
    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("original_query", "")
        or query_info.get("normalized_query", "")
    )

    return any(word in q for word in PACKAGE_WORDS)


def detect_category_query(query_info):
    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("original_query", "")
        or query_info.get("normalized_query", "")
    )

    detected = []

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                detected.append(category)
                break

    return detected


# =====================================================
# STRICT FILTER
# =====================================================

def product_type_match(row, product_type):
    text = row_text(row)

    if product_type == "buzdolabi":
        return (
            "buzdolabi" in text
            or "buz dolabi" in text
            or "no frost" in text
            or "sogutucu" in text
            or "mini bar" in text
        )

    if product_type == "camasir_makinesi":
        return "camasir" in text and "bulasik" not in text

    if product_type == "bulasik_makinesi":
        return "bulasik" in text

    if product_type == "televizyon":
        return (
            "televizyon" in text
            or "smart tv" in text
            or " tv " in f" {text} "
            or "akilli tv" in text
        )

    if product_type == "supurge":
        return "supurge" in text or "temizlik" in text

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
        return "firin" in text or "ankastre" in text

    return False


def apply_strict_product_filter(df, query_info):
    """
    En önemli katman:
    Kullanıcı net ürün tipi söylediyse başka ürünler elenir.
    """

    if df.empty:
        return df

    if is_package_query(query_info):
        # Çeyiz/paket isteklerinde farklı kategoriler karışabilir.
        return df

    strict_types = detect_strict_product_types(query_info)

    if not strict_types:
        return df

    filtered_parts = []

    for product_type in strict_types:
        part = df[df.apply(lambda row: product_type_match(row, product_type), axis=1)]

        if not part.empty:
            filtered_parts.append(part)

    if not filtered_parts:
        return df.iloc[0:0]

    filtered = pd.concat(filtered_parts).drop_duplicates()

    return filtered


# =====================================================
# SKORLAMA
# =====================================================

def score_product(row, query_info):
    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("original_query", "")
        or query_info.get("normalized_query", "")
    )

    budget = safe_number(query_info.get("budget", 0))

    brands = query_info.get("brands", []) or []
    product_types = detect_strict_product_types(query_info)
    categories = query_info.get("categories", []) or []
    use_cases = query_info.get("use_cases", []) or []
    payment_priority = query_info.get("payment_priority")
    payments = query_info.get("payments", []) or []

    text = row_text(row)

    score = 0

    # Kelime eşleşmesi
    for token in q.split():
        if len(token) > 2 and token in text:
            score += 4

    # Marka eşleşmesi
    for brand in brands:
        if normalize_text(brand) in text:
            score += 30

    # Ürün tipi eşleşmesi
    for product_type in product_types:
        if product_type_match(row, product_type):
            score += 45
        else:
            score -= 80

    # Kategori eşleşmesi
    for category in categories:
        if normalize_text(category) in text:
            score += 15

    detected_categories = detect_category_query(query_info)

    for category in detected_categories:
        if category == "beyaz_esya" and any(
            word in text for word in ["buzdolabi", "camasir", "bulasik", "firin", "klima"]
        ):
            score += 15

        if category == "elektronik" and any(
            word in text for word in ["telefon", "laptop", "bilgisayar", "televizyon", "tv"]
        ):
            score += 15

        if category == "kucuk_ev_aleti" and any(
            word in text for word in ["supurge", "kahve", "temizlik"]
        ):
            score += 15

    # Kullanım amacı
    for use_case in use_cases:
        uc = normalize_text(use_case)

        if uc in text:
            score += 18

        if uc == "ceyiz" and any(
            word in text for word in ["buzdolabi", "camasir", "bulasik", "televizyon", "supurge"]
        ):
            score += 18

        if uc == "ogrenci" and any(
            word in text for word in ["laptop", "bilgisayar", "telefon", "tablet"]
        ):
            score += 16

    # Bütçe
    price = safe_number(row.get("price", 0))

    if budget:
        if price and price <= budget:
            score += 20
        elif price and price > budget:
            over_ratio = price / budget

            if over_ratio <= 1.10:
                score -= 5
            elif over_ratio <= 1.25:
                score -= 15
            else:
                score -= 35

    # Ödeme tercihleri
    if "senet" in q or "senet" in payments or payment_priority == "lowest_monthly":
        if safe_number(row.get("senet_total_price", 0)) > 0:
            score += 22
        if safe_number(row.get("senet_monthly_9", 0)) > 0:
            score += 12

    if "havale" in q or "havale" in payments or payment_priority == "lowest_total":
        if safe_number(row.get("bank_transfer_price", 0)) > 0:
            score += 22

    if "taksit" in q or "taksit" in payments or payment_priority == "card_installment":
        if safe_number(row.get("installment_6_total", 0)) > 0:
            score += 20

    # Stok
    if normalize_text(row.get("stock_status", "")) == "stokta":
        score += 8

    return score


# =====================================================
# ANA KARAR MOTORU
# =====================================================

def make_decision(products_df, query_info):
    """
    Ana karar motoru.
    LLM'den önce çalışır.
    LLM ürün seçmez, sadece burada seçilen ürünü anlatır.
    """

    if products_df is None or products_df.empty:
        return {
            "result_df": pd.DataFrame(),
            "query_info": query_info,
            "decision": "Ürün verisi bulunamadı.",
            "fallback_answer": "Ürün verisi bulunamadı.",
        }

    df = products_df.copy()

    # 1. Strict ürün tipi filtresi
    strict_types = detect_strict_product_types(query_info)
    package_query = is_package_query(query_info)

    filtered_df = apply_strict_product_filter(df, query_info)

    if filtered_df.empty and strict_types and not package_query:
        return {
            "result_df": pd.DataFrame(),
            "query_info": query_info,
            "decision": (
                f"Kullanıcı net olarak {', '.join(strict_types)} istedi. "
                "Bu ürün tipine uygun katalog ürünü bulunamadı."
            ),
            "fallback_answer": (
                "Talebiniz net bir ürün tipine ait görünüyor ancak katalogda bu ürün tipine uygun ürün bulunamadı."
            ),
        }

    df = filtered_df

    # 2. Skorlama
    df["score"] = df.apply(lambda row: score_product(row, query_info), axis=1)

    # 3. Çok düşük skorları ele
    if strict_types and not package_query:
        df = df[df["score"] > 0]
    else:
        max_score = df["score"].max() if not df.empty else 0

        if max_score > 0:
            df = df[df["score"] >= max_score * 0.35]

    # 4. Sıralama
    if not df.empty:
        df = df.sort_values("score", ascending=False)

    decision_lines = []

    if strict_types and not package_query:
        decision_lines.append(
            f"Strict ürün filtresi aktif: sadece {', '.join(strict_types)} ürünleri değerlendirildi."
        )

    if package_query:
        decision_lines.append("Paket / çeyiz isteği algılandı, çoklu kategori değerlendirmesine izin verildi.")

    if query_info.get("budget"):
        decision_lines.append(f"Bütçe dikkate alındı: {money(query_info.get('budget'))}.")

    if query_info.get("payment_priority"):
        decision_lines.append(f"Ödeme önceliği dikkate alındı: {query_info.get('payment_priority')}.")

    if not decision_lines:
        decision_lines.append("Ürünler niyet, kategori, ödeme ve stok uygunluğuna göre sıralandı.")

    return {
        "result_df": df.head(8),
        "query_info": query_info,
        "decision": " ".join(decision_lines),
        "fallback_answer": "Talebinize göre en uygun ürünler listelendi.",
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    test_df = pd.DataFrame(
        [
            {
                "product_name": "Beko No Frost Buzdolabı 500 L",
                "category": "Beyaz Eşya",
                "brand": "Beko",
                "price": 18500,
                "stock_status": "Stokta",
                "description": "No Frost geniş hacimli buzdolabı",
                "features": "No Frost, sessiz çalışma",
                "use_case": "Çeyiz, ev",
                "bank_transfer_price": 17650,
                "installment_6_total": 19500,
                "senet_total_price": 21900,
                "senet_monthly_9": 2433,
            },
            {
                "product_name": "Samsung 50 inç Akıllı Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "price": 12900,
                "stock_status": "Stokta",
                "description": "Smart TV 4K",
                "features": "4K ekran",
                "use_case": "Salon",
                "bank_transfer_price": 12490,
                "installment_6_total": 13700,
                "senet_total_price": 15900,
                "senet_monthly_9": 1766,
            },
        ]
    )

    test_query = {
        "raw_query": "Buzdolabı senetle olur mu?",
        "normalized_query": "buzdolabi senetle olur mu",
        "budget": None,
        "payments": ["senet"],
        "product_types": ["buzdolabi"],
        "payment_priority": "lowest_monthly",
    }

    result = make_decision(test_df, test_query)

    print(result["decision"])
    print(result["result_df"][["product_name", "score"]])