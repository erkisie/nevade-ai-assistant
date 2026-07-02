import pandas as pd

from src.customer_intelligence_engine import normalize_text, safe_number, money


# =====================================================
# CUSTOMER PROFILE ENGINE
# Kişisel alışveriş asistanı için müşteri hafızası
# =====================================================


DEFAULT_PROFILE = {
    "last_intent": None,
    "last_query": None,
    "last_category": None,
    "last_product_type": None,
    "last_budget": None,
    "last_payments": [],
    "last_commerce_risks": [],
    "price_sensitive": False,
    "payment_sensitive": False,
    "easy_use_preference": False,
    "premium_preference": False,
    "cart_rescue_count": 0,
    "conversation_turn": 0,
}


FOLLOW_UP_PATTERNS = {
    "CHEAPER_FOLLOW_UP": [
        "daha ucuz",
        "daha uygunu",
        "ucuzu var mi",
        "ucuzu var mı",
        "bütçeme uygun",
        "butceme uygun",
        "pahali",
        "pahalı",
        "çok pahalı",
        "cok pahali",
    ],
    "PAYMENT_FOLLOW_UP": [
        "senet olur mu",
        "senetli olur mu",
        "taksit olur mu",
        "havale olur mu",
        "kartla olur mu",
        "aylık ne kadar",
        "aylik ne kadar",
        "ödeme nasıl",
        "odeme nasil",
    ],
    "COMPARE_FOLLOW_UP": [
        "hangisi daha iyi",
        "karşılaştır",
        "karsilastir",
        "farkı ne",
        "farki ne",
        "hangisini alayım",
        "hangisini alayim",
    ],
    "PACKAGE_FOLLOW_UP": [
        "paketi ucuzlat",
        "paketi düşür",
        "paketi dusur",
        "bütçeye çek",
        "butceye cek",
        "bir ürün çıkar",
        "bir urun cikar",
    ],
}


PREFERENCE_PATTERNS = {
    "easy_use_preference": [
        "annem",
        "babam",
        "yaşlı",
        "yasli",
        "kolay kullanım",
        "kolay kullanim",
        "basit",
        "karmaşık olmasın",
        "karmasik olmasin",
    ],
    "price_sensitive": [
        "uygun",
        "ucuz",
        "bütçe",
        "butce",
        "ekonomik",
        "pahalı",
        "pahali",
        "limit",
        "yetmedi",
    ],
    "payment_sensitive": [
        "senet",
        "taksit",
        "havale",
        "kart",
        "ödeme",
        "odeme",
        "limit",
    ],
    "premium_preference": [
        "en iyisi",
        "premium",
        "kaliteli",
        "üst model",
        "ust model",
        "performanslı",
        "performansli",
    ],
}


def create_empty_customer_profile():
    return DEFAULT_PROFILE.copy()


def detect_follow_up_type(user_query):
    q = normalize_text(user_query)

    detected = []

    for follow_type, patterns in FOLLOW_UP_PATTERNS.items():
        for pattern in patterns:
            if normalize_text(pattern) in q:
                detected.append(follow_type)
                break

    return detected


def detect_preferences(user_query):
    q = normalize_text(user_query)

    preferences = {
        "price_sensitive": False,
        "payment_sensitive": False,
        "easy_use_preference": False,
        "premium_preference": False,
    }

    for pref, patterns in PREFERENCE_PATTERNS.items():
        for pattern in patterns:
            if normalize_text(pattern) in q:
                preferences[pref] = True
                break

    return preferences


def update_customer_profile(profile, customer_analysis):
    """
    Yeni müşteri mesajına göre profili günceller.
    """

    if profile is None:
        profile = create_empty_customer_profile()

    updated = profile.copy()

    user_query = customer_analysis.get("original_query", "")
    follow_ups = detect_follow_up_type(user_query)
    preferences = detect_preferences(user_query)

    updated["conversation_turn"] = int(updated.get("conversation_turn", 0)) + 1
    updated["last_query"] = user_query

    intent = customer_analysis.get("intent")
    category = customer_analysis.get("category")
    product_type = customer_analysis.get("product_type")
    budget = customer_analysis.get("budget")
    payments = customer_analysis.get("payments", [])
    risks = customer_analysis.get("commerce_risks", [])

    if intent:
        updated["last_intent"] = intent

    if category:
        updated["last_category"] = category

    if product_type:
        updated["last_product_type"] = product_type

    if budget:
        updated["last_budget"] = budget

    if payments:
        old_payments = updated.get("last_payments", []) or []
        merged = list(dict.fromkeys(old_payments + payments))
        updated["last_payments"] = merged

    if risks:
        updated["last_commerce_risks"] = risks

    if "LIMIT_YETERSIZ" in risks or "SEPET_TERK_RISKI" in risks:
        updated["cart_rescue_count"] = int(updated.get("cart_rescue_count", 0)) + 1

    for key, value in preferences.items():
        if value:
            updated[key] = True

    updated["last_follow_ups"] = follow_ups

    return updated


def enrich_analysis_with_profile(customer_analysis, profile):
    """
    Eksik müşteri analizini profil geçmişiyle tamamlar.
    Örnek:
    - Müşteri önce 'telefon öner' dedi.
    - Sonra 'daha ucuzu var mı?' dedi.
    - Bu fonksiyon ikinci mesajın kategorisini Telefon yapar.
    """

    if profile is None:
        return customer_analysis

    enriched = customer_analysis.copy()

    follow_ups = detect_follow_up_type(enriched.get("original_query", ""))

    enriched["follow_up_types"] = follow_ups
    enriched["is_follow_up"] = len(follow_ups) > 0

    if enriched.get("is_follow_up"):
        if not enriched.get("category") and profile.get("last_category"):
            enriched["category"] = profile.get("last_category")

        if not enriched.get("product_type") and profile.get("last_product_type"):
            enriched["product_type"] = profile.get("last_product_type")

        if not enriched.get("budget") and profile.get("last_budget"):
            enriched["budget"] = profile.get("last_budget")

        if not enriched.get("payments") and profile.get("last_payments"):
            enriched["payments"] = profile.get("last_payments")

        if "CHEAPER_FOLLOW_UP" in follow_ups:
            enriched["intent"] = "CHEAPER_ALTERNATIVE"
            enriched["is_cheaper_alternative"] = True

        if "PAYMENT_FOLLOW_UP" in follow_ups:
            enriched["intent"] = "PAYMENT_ALTERNATIVE"
            enriched["is_payment_help"] = True

        if "COMPARE_FOLLOW_UP" in follow_ups:
            enriched["intent"] = "PRODUCT_COMPARISON"

        if "PACKAGE_FOLLOW_UP" in follow_ups:
            enriched["intent"] = "PACKAGE_BUILDING"
            enriched["is_package"] = True

    enriched["profile_flags"] = {
        "price_sensitive": profile.get("price_sensitive", False),
        "payment_sensitive": profile.get("payment_sensitive", False),
        "easy_use_preference": profile.get("easy_use_preference", False),
        "premium_preference": profile.get("premium_preference", False),
        "cart_rescue_count": profile.get("cart_rescue_count", 0),
    }

    return enriched


def create_profile_summary(profile):
    if profile is None:
        return "Müşteri profili yok."

    parts = []

    if profile.get("last_category"):
        parts.append(f"Son kategori: {profile.get('last_category')}")

    if profile.get("last_product_type"):
        parts.append(f"Son ürün tipi: {profile.get('last_product_type')}")

    if profile.get("last_budget"):
        parts.append(f"Son bütçe: {money(profile.get('last_budget'))}")

    if profile.get("last_payments"):
        parts.append(f"Ödeme tercihi: {', '.join(profile.get('last_payments'))}")

    flags = []

    if profile.get("price_sensitive"):
        flags.append("fiyat hassasiyeti")

    if profile.get("payment_sensitive"):
        flags.append("ödeme hassasiyeti")

    if profile.get("easy_use_preference"):
        flags.append("kolay kullanım tercihi")

    if profile.get("premium_preference"):
        flags.append("premium tercih")

    if flags:
        parts.append("Profil sinyalleri: " + ", ".join(flags))

    if profile.get("cart_rescue_count", 0) > 0:
        parts.append(f"Sepet kurtarma sayısı: {profile.get('cart_rescue_count')}")

    if not parts:
        return "Henüz belirgin müşteri tercihi yok."

    return " | ".join(parts)