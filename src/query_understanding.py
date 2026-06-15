import re


CATEGORY_KEYWORDS = {
    "Bilgisayar": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "oyun bilgisayarı",
        "öğrenci bilgisayarı",
        "iş bilgisayarı"
    ],
    "Telefon": [
        "telefon",
        "iphone",
        "samsung",
        "xiaomi",
        "oppo",
        "akıllı telefon"
    ],
    "Beyaz Eşya": [
        "buzdolabı",
        "çamaşır makinesi",
        "beyaz eşya",
        "dolap",
        "makine"
    ],
    "Ev Elektroniği": [
        "süpürge",
        "robot süpürge",
        "airfryer",
        "kahve makinesi",
        "ev elektroniği",
        "dyson",
        "philips"
    ],
    "Televizyon": [
        "televizyon",
        "tv",
        "oled",
        "4k",
        "akıllı tv"
    ]
}


BRAND_KEYWORDS = [
    "lenovo",
    "hp",
    "apple",
    "macbook",
    "asus",
    "acer",
    "dell",
    "samsung",
    "xiaomi",
    "oppo",
    "philips",
    "dyson",
    "tefal",
    "karaca",
    "beko",
    "arçelik",
    "siemens",
    "bosch",
    "lg",
    "tcl"
]


def normalize_text(text):
    return str(text).lower().strip()


def extract_budget(user_query):
    query = normalize_text(user_query)

    patterns = [
        r"(\d+)\s*bin",
        r"(\d+)\s*000",
        r"(\d+)\s*tl",
        r"(\d+)\s*lira"
    ]

    for pattern in patterns:
        match = re.search(pattern, query)

        if match:
            value = int(match.group(1))

            if "bin" in pattern:
                return value * 1000

            if value < 1000 and "000" in pattern:
                return value * 1000

            return value

    return None


def extract_category(user_query):
    query = normalize_text(user_query)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                return category

    return None


def extract_brands(user_query):
    query = normalize_text(user_query)

    matched_brands = []

    for brand in BRAND_KEYWORDS:
        if brand in query:
            normalized_brand = brand

            if brand == "macbook":
                normalized_brand = "apple"

            if normalized_brand not in matched_brands:
                matched_brands.append(normalized_brand)

    return matched_brands


def is_comparison_query(user_query):
    query = normalize_text(user_query)

    comparison_words = [
        "mı",
        "mi",
        "mu",
        "mü",
        "hangisi",
        "karşılaştır",
        "kıyasla",
        "farkı",
        "daha iyi",
        "sence",
        "vs"
    ]

    brand_count = len(extract_brands(user_query))

    return any(word in query for word in comparison_words) and brand_count >= 1


def wants_installment(user_query):
    query = normalize_text(user_query)

    return any(
        word in query
        for word in [
            "taksit",
            "taksitli",
            "6 taksit",
            "peşin fiyatına",
            "aylık ödeme"
        ]
    )


def wants_in_stock(user_query):
    query = normalize_text(user_query)

    return any(
        word in query
        for word in [
            "stokta",
            "hemen",
            "teslim",
            "var mı"
        ]
    )


def detect_assistant_intent(user_query):
    query = normalize_text(user_query)

    if any(
        word in query
        for word in [
            "siparişim nerede",
            "siparisim nerede",
            "kargom nerede",
            "sipariş durum",
            "siparis durum",
            "sipariş takip",
            "siparis takip"
        ]
    ):
        return "order_tracking"

    if any(
        word in query
        for word in [
            "sepetim",
            "sepeti göster",
            "sepette ne var",
            "sepetimi göster"
        ]
    ):
        return "show_cart"

    if any(
        word in query
        for word in [
            "favorilerim",
            "favorileri göster",
            "favorilerimi göster",
            "favorimde ne var"
        ]
    ):
        return "show_favorites"

    if is_comparison_query(user_query):
        return "comparison"

    if any(
        word in query
        for word in [
            "benzer",
            "alternatif",
            "buna benzer"
        ]
    ):
        return "similar_products"

    return "product_recommendation"


def understand_query(user_query):
    return {
        "original_query": user_query,
        "intent": detect_assistant_intent(user_query),
        "budget": extract_budget(user_query),
        "category": extract_category(user_query),
        "brands": extract_brands(user_query),
        "is_comparison": is_comparison_query(user_query),
        "wants_installment": wants_installment(user_query),
        "wants_in_stock": wants_in_stock(user_query)
    }