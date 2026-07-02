import re
import unicodedata


# =====================================================
# TEXT NORMALIZATION
# =====================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    replacements = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    text = text.translate(replacements)

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =====================================================
# DICTIONARIES
# =====================================================

CATEGORY_KEYWORDS = {
    "Bilgisayar": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "pc",
        "dizustu",
    ],

    "Telefon": [
        "telefon",
        "iphone",
        "samsung",
        "xiaomi",
        "redmi",
        "galaxy",
        "cep telefonu",
    ],

    "Beyaz Eşya": [
        "beyaz esya",
        "buzdolabi",
        "buz dolabi",
        "camasir",
        "camasir makinesi",
        "bulasik",
        "bulasik makinesi",
        "firin",
        "ankastre",
        "mini firin",
        "ceyiz",
    ],

    "Televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "oled",
        "4k",
        "ekran",
    ],

    "Küçük Ev Aleti": [
        "blender",
        "cay makinesi",
        "tost makinesi",
        "supurge",
        "robot supurge",
        "airfryer",
        "kahve makinesi",
        "utu",
        "mutfak",
    ],
}


PRODUCT_TYPE_KEYWORDS = {
    "laptop": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "dizustu",
    ],

    "telefon": [
        "telefon",
        "iphone",
        "galaxy",
        "redmi",
        "xiaomi",
        "cep telefonu",
    ],

    "buzdolabi": [
        "buzdolabi",
        "buz dolabi",
        "no frost",
        "sogutucu",
    ],

    "camasir_makinesi": [
        "camasir",
        "camasir makinesi",
        "yikama",
    ],

    "bulasik_makinesi": [
        "bulasik",
        "bulasik makinesi",
    ],

    "firin": [
        "firin",
        "ankastre",
        "ankastre firin",
        "mini firin",
        "elektrikli firin",
    ],

    "televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "oled",
        "4k",
    ],

    "supurge": [
        "supurge",
        "robot supurge",
        "dyson",
        "philips supurge",
    ],

    "blender": [
        "blender",
        "blender seti",
    ],

    "cay_makinesi": [
        "cay makinesi",
        "cayci",
    ],

    "tost_makinesi": [
        "tost makinesi",
        "tost",
    ],

    "utu": [
        "utu",
        "buharli utu",
    ],
}


PRODUCT_TYPE_LABELS = {
    "laptop": "laptop",
    "telefon": "telefon",
    "buzdolabi": "buzdolabı",
    "camasir_makinesi": "çamaşır makinesi",
    "bulasik_makinesi": "bulaşık makinesi",
    "firin": "fırın",
    "televizyon": "televizyon",
    "supurge": "süpürge",
    "blender": "blender",
    "cay_makinesi": "çay makinesi",
    "tost_makinesi": "tost makinesi",
    "utu": "ütü",
}


BRAND_ALIASES = {
    "apple": "Apple",
    "iphone": "Apple",
    "macbook": "Apple",

    "samsung": "Samsung",
    "galaxy": "Samsung",

    "xiaomi": "Xiaomi",
    "redmi": "Xiaomi",

    "lenovo": "Lenovo",
    "lenova": "Lenovo",
    "ideapad": "Lenovo",

    "beko": "Beko",
    "arcelik": "Arçelik",
    "arcelik": "Arçelik",
    "vestel": "Vestel",
    "bosch": "Bosch",
    "siemens": "Siemens",

    "philips": "Philips",
    "fakir": "Fakir",
    "arzum": "Arzum",
    "tefal": "Tefal",
}


PAYMENT_KEYWORDS = {
    "senet": [
        "senet",
        "senetli",
        "senetle",
        "elden odeme",
    ],

    "havale": [
        "havale",
        "eft",
    ],

    "taksit": [
        "taksit",
        "aylik",
        "aylik odeme",
    ],

    "pesin": [
        "pesin",
        "nakit",
    ],

    "kart": [
        "kart",
        "kredi karti",
    ],
}


PACKAGE_KEYWORDS = [
    "paket",
    "paketi",
    "set",
    "seti",
    "kombin",
    "kombin yap",
    "ceyiz paketi",
    "ceyiz seti",
    "alisveris listesi",
]


# =====================================================
# EXTRACTION FUNCTIONS
# =====================================================

def extract_budget(query):
    q = normalize_text(query)

    match = re.search(r"(\d+)\s*(bin|k)", q)
    if match:
        return int(match.group(1)) * 1000

    numbers = re.findall(r"\d[\d\.\,]*", q)

    if not numbers:
        return None

    raw = numbers[0].replace(".", "").replace(",", "")

    try:
        value = int(raw)
    except Exception:
        return None

    if value < 1000:
        return None

    return value


def extract_category(q):
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                return category

    return None


def extract_product_type(q):
    for product_type, keywords in PRODUCT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                return product_type

    return None


def extract_brand(q):
    for alias, brand in BRAND_ALIASES.items():
        if normalize_text(alias) in q:
            return brand

    return None


def extract_payments(q):
    payments = []

    for payment, keywords in PAYMENT_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in q:
                payments.append(payment)
                break

    return list(set(payments))


def is_package_query(q):
    return any(normalize_text(word) in q for word in PACKAGE_KEYWORDS)


# =====================================================
# MAIN ANALYSIS
# =====================================================

def analyze_query(query):
    q = normalize_text(query)

    product_type = extract_product_type(q)
    category = extract_category(q)

    if category is None:
        if product_type in ["buzdolabi", "camasir_makinesi", "bulasik_makinesi", "firin"]:
            category = "Beyaz Eşya"

        elif product_type in ["blender", "cay_makinesi", "tost_makinesi", "supurge", "utu"]:
            category = "Küçük Ev Aleti"

        elif product_type == "laptop":
            category = "Bilgisayar"

        elif product_type == "telefon":
            category = "Telefon"

        elif product_type == "televizyon":
            category = "Televizyon"

    budget = extract_budget(query)
    brand = extract_brand(q)
    payments = extract_payments(q)
    package = is_package_query(q)

    return {
        "original_query": query,
        "normalized_query": q,
        "intent": "product_search",
        "category": category,
        "product_type": product_type,
        "product_type_label": PRODUCT_TYPE_LABELS.get(product_type),
        "brand": brand,
        "budget": budget,
        "payments": payments,
        "is_package": package,
    }


# =====================================================
# QUERY CLASSIFICATION
# =====================================================

def is_category_only_query(query_info):
    q = query_info.get("normalized_query", "")
    words = q.split()

    has_category = query_info.get("category") is not None
    has_product_type = query_info.get("product_type") is not None
    has_budget = query_info.get("budget") is not None
    has_brand = query_info.get("brand") is not None
    has_payment = len(query_info.get("payments", [])) > 0
    is_package = query_info.get("is_package", False)

    if not has_category:
        return False

    if has_product_type or has_budget or has_brand or has_payment or is_package:
        return False

    if len(words) <= 3:
        return True

    return False


def is_budget_only_query(query_info):
    has_budget = query_info.get("budget") is not None
    has_category = query_info.get("category") is not None
    has_product_type = query_info.get("product_type") is not None
    has_brand = query_info.get("brand") is not None
    has_payment = len(query_info.get("payments", [])) > 0
    is_package = query_info.get("is_package", False)

    return (
        has_budget
        and not has_category
        and not has_product_type
        and not has_brand
        and not has_payment
        and not is_package
    )