import re
from difflib import SequenceMatcher


# =====================================================
# TEXT NORMALIZATION
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


def similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0

    return SequenceMatcher(None, a, b).ratio()


def contains_any(text, keywords):
    text = normalize_text(text)

    for keyword in keywords:
        if normalize_text(keyword) in text:
            return True

    return False


# =====================================================
# DICTIONARIES
# =====================================================

BRAND_ALIASES = {
    "apple": ["apple", "iphone", "macbook", "ipad", "airpods"],
    "samsung": ["samsung", "samsun", "samung", "galaxy"],
    "lenovo": ["lenovo", "lenova", "thinkpad", "ideapad"],
    "hp": ["hp", "hewlett", "pavilion", "victus"],
    "asus": ["asus", "asuz", "rog", "vivobook", "zenbook"],
    "xiaomi": ["xiaomi", "redmi", "mi"],
    "beko": ["beko"],
    "arcelik": ["arcelik", "arçelik"],
    "vestel": ["vestel"],
    "bosch": ["bosch"],
    "lg": ["lg"],
    "philips": ["philips", "filips"],
    "dyson": ["dyson"],
}

PRODUCT_TYPE_ALIASES = {
    "telefon": [
        "telefon", "cep telefonu", "iphone", "samsung telefon", "android",
        "akilli telefon", "galaxy", "redmi"
    ],
    "laptop": [
        "laptop", "bilgisayar", "notebook", "macbook", "oyuncu bilgisayari",
        "is bilgisayari", "ogrenci bilgisayari", "gaming laptop"
    ],
    "tablet": [
        "tablet", "ipad"
    ],
    "televizyon": [
        "televizyon", "tv", "smart tv", "led tv", "oled", "qled"
    ],
    "buzdolabi": [
        "buzdolabi", "buz dolabi", "no frost", "dolap"
    ],
    "camasir_makinesi": [
        "camasir makinesi", "çamaşır makinesi", "camasir", "makine"
    ],
    "bulasik_makinesi": [
        "bulasik makinesi", "bulaşık makinesi", "bulasik"
    ],
    "klima": [
        "klima", "inverter klima"
    ],
    "supurge": [
        "supurge", "süpürge", "robot supurge", "dikey supurge", "dyson"
    ],
    "kulaklik": [
        "kulaklik", "airpods", "bluetooth kulaklik"
    ],
    "cay_makinesi": [
        "cay makinesi", "çay makinesi", "cayci"
    ],
}

CATEGORY_ALIASES = {
    "Elektronik": [
        "telefon", "laptop", "bilgisayar", "tablet", "televizyon",
        "kulaklik", "akilli saat", "elektronik"
    ],
    "Beyaz Eşya": [
        "buzdolabi", "camasir", "bulasik", "kurutma", "firin",
        "ocak", "beyaz esya"
    ],
    "Ev Elektroniği": [
        "supurge", "robot supurge", "klima", "cay makinesi",
        "kahve makinesi", "ev elektronigi"
    ],
    "Mobilya": [
        "koltuk", "masa", "sandalye", "yatak", "dolap", "mobilya"
    ],
}

INTENT_KEYWORDS = {
    "product_search": [
        "oner", "oneri", "tavsiye", "ne alayim", "hangisi iyi",
        "hangi urun", "urun bakiyorum", "lazim", "ariyorum"
    ],
    "price": [
        "fiyat", "ne kadar", "kac tl", "ucret", "pahali", "ucuz",
        "indirim", "kampanya"
    ],
    "installment": [
        "taksit", "kredi karti", "kartla", "6 taksit", "9 taksit",
        "aylik odeme"
    ],
    "senet": [
        "senet", "senetli", "elden taksit", "magaza taksidi",
        "aylik dusuk", "pesinatsiz"
    ],
    "cash_transfer": [
        "havale", "eft", "pesin", "nakit", "toplam uygun",
        "en uygun fiyat"
    ],
    "stock": [
        "stok", "stokta", "var mi", "mevcut mu", "hemen alabilir miyim"
    ],
    "shipping": [
        "kargo", "teslimat", "ne zaman gelir", "kac gunde gelir",
        "teslim edilir"
    ],
    "return_cancel": [
        "iade", "iptal", "vazgectim", "geri vermek", "degisim"
    ],
    "invoice": [
        "fatura", "e fatura", "efatura", "faturam"
    ],
    "order_tracking": [
        "siparis", "siparisim", "nerede", "takip", "kargom nerede",
        "siparis durumu"
    ],
    "comparison": [
        "karsilastir", "farki ne", "hangisi daha iyi", "mi daha iyi",
        "versus", "vs"
    ],
    "warranty": [
        "garanti", "servis", "yetkili servis"
    ],
    "customer_support": [
        "yardim", "destek", "musteri hizmetleri", "canli destek"
    ],
}


USE_CASE_KEYWORDS = {
    "ogrenci": [
        "ogrenci", "okul", "ders", "odev", "universite"
    ],
    "oyun": [
        "oyun", "gaming", "fps", "gta", "valorant", "pubg"
    ],
    "is": [
        "is", "ofis", "excel", "rapor", "toplanti", "home office"
    ],
    "ceyiz": [
        "ceyiz", "evleniyorum", "ev kuruyorum", "yeni ev"
    ],
    "aile": [
        "aile", "kalabalik", "genis aile", "cocuklu"
    ],
    "butce_dostu": [
        "uygun", "ucuz", "butce", "fiyat performans", "ekonomik"
    ],
    "premium": [
        "premium", "en iyi", "kaliteli", "ust segment", "performansli"
    ],
}


PAYMENT_PRIORITY_KEYWORDS = {
    "lowest_total": [
        "en uygun", "en ucuz", "toplam az", "pesin", "havale",
        "nakit", "fazla odemeyeyim"
    ],
    "lowest_monthly": [
        "aylik dusuk", "aylik az", "senet", "taksit", "pesinatsiz",
        "kolay odeme", "ay ay"
    ],
    "card_installment": [
        "kredi karti", "kartla", "6 taksit", "kart taksiti"
    ],
}


# =====================================================
# ENTITY EXTRACTION
# =====================================================

def extract_budget(text):
    normalized = normalize_text(text)

    patterns = [
        r"(\d{1,3}(?:[.\s]\d{3})+|\d{4,7})\s*(tl|lira)?",
        r"(\d{1,3})\s*bin",
    ]

    budgets = []

    for pattern in patterns:
        matches = re.findall(pattern, normalized)

        for match in matches:
            if isinstance(match, tuple):
                number = match[0]
            else:
                number = match

            if "bin" in pattern:
                try:
                    budgets.append(int(number) * 1000)
                except Exception:
                    pass
            else:
                clean_number = re.sub(r"[^\d]", "", str(number))
                try:
                    value = int(clean_number)
                    if value >= 500:
                        budgets.append(value)
                except Exception:
                    pass

    if not budgets:
        return None

    return max(budgets)


def extract_brands(text):
    normalized = normalize_text(text)
    found = []

    for brand, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_text(alias)

            if alias_norm in normalized:
                found.append(brand)
                break

            for word in normalized.split():
                if similarity(word, alias_norm) >= 0.86:
                    found.append(brand)
                    break

    return list(dict.fromkeys(found))


def extract_product_types(text):
    normalized = normalize_text(text)
    found = []

    for product_type, aliases in PRODUCT_TYPE_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_text(alias)

            if alias_norm in normalized:
                found.append(product_type)
                break

            for word in normalized.split():
                if similarity(word, alias_norm) >= 0.88:
                    found.append(product_type)
                    break

    return list(dict.fromkeys(found))


def extract_categories(text):
    normalized = normalize_text(text)
    found = []

    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if normalize_text(alias) in normalized:
                found.append(category)
                break

    return list(dict.fromkeys(found))


def extract_use_cases(text):
    normalized = normalize_text(text)
    found = []

    for use_case, keywords in USE_CASE_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in normalized:
                found.append(use_case)
                break

    return list(dict.fromkeys(found))


def extract_payment_priority(text):
    normalized = normalize_text(text)
    scores = {
        "lowest_total": 0,
        "lowest_monthly": 0,
        "card_installment": 0,
    }

    for priority, keywords in PAYMENT_PRIORITY_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in normalized:
                scores[priority] += 1

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return None

    return best


def extract_order_number(text):
    normalized = str(text).upper()

    patterns = [
        r"NVD[-\s]?\d{3,8}",
        r"SIP[-\s]?\d{3,8}",
        r"ORDER[-\s]?\d{3,8}",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)

        if match:
            return match.group(0).replace(" ", "-")

    return None


# =====================================================
# INTENT DETECTION
# =====================================================

def detect_intents(text):
    normalized = normalize_text(text)

    intent_scores = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            keyword_norm = normalize_text(keyword)

            if keyword_norm in normalized:
                score += 2

            for word in normalized.split():
                if similarity(word, keyword_norm) >= 0.90:
                    score += 1

        if score > 0:
            intent_scores[intent] = score

    if not intent_scores:
        return ["general_question"]

    sorted_intents = sorted(
        intent_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [intent for intent, score in sorted_intents]


# =====================================================
# SENTIMENT / URGENCY
# =====================================================

def detect_urgency(text):
    normalized = normalize_text(text)

    urgent_keywords = [
        "acil", "hemen", "bugun", "yarin", "simdi", "cok acil",
        "misafirim gelecek", "lazim", "bekliyorum"
    ]

    if contains_any(normalized, urgent_keywords):
        return "high"

    return "normal"


def detect_sentiment(text):
    normalized = normalize_text(text)

    negative_words = [
        "kotu", "berbat", "sinir", "iptal", "sikayet", "gecikti",
        "gelmedi", "memnun degilim", "problem", "sorun"
    ]

    positive_words = [
        "tesekkur", "super", "guzel", "memnunum", "iyi", "begendim"
    ]

    negative_hit = sum(1 for word in negative_words if normalize_text(word) in normalized)
    positive_hit = sum(1 for word in positive_words if normalize_text(word) in normalized)

    if negative_hit > positive_hit:
        return "negative"

    if positive_hit > negative_hit:
        return "positive"

    return "neutral"


# =====================================================
# MAIN NLP ANALYSIS
# =====================================================

def analyze_user_query(text):
    """
    Kullanıcı sorusunu detaylı analiz eder.
    App tarafında tek çağrılması gereken ana fonksiyon budur.
    """

    text = str(text or "").strip()

    intents = detect_intents(text)
    brands = extract_brands(text)
    product_types = extract_product_types(text)
    categories = extract_categories(text)
    use_cases = extract_use_cases(text)
    budget = extract_budget(text)
    payment_priority = extract_payment_priority(text)
    order_number = extract_order_number(text)
    urgency = detect_urgency(text)
    sentiment = detect_sentiment(text)

    analysis = {
        "original_query": text,
        "normalized_query": normalize_text(text),
        "intents": intents,
        "primary_intent": intents[0] if intents else "general_question",
        "brands": brands,
        "product_types": product_types,
        "categories": categories,
        "use_cases": use_cases,
        "budget": budget,
        "payment_priority": payment_priority,
        "order_number": order_number,
        "urgency": urgency,
        "sentiment": sentiment,
        "confidence": calculate_query_confidence(
            intents=intents,
            brands=brands,
            product_types=product_types,
            categories=categories,
            use_cases=use_cases,
            budget=budget,
            payment_priority=payment_priority,
            order_number=order_number,
        ),
    }

    return analysis


def calculate_query_confidence(
    intents,
    brands,
    product_types,
    categories,
    use_cases,
    budget,
    payment_priority,
    order_number,
):
    score = 0

    if intents and intents[0] != "general_question":
        score += 25

    if brands:
        score += 15

    if product_types:
        score += 20

    if categories:
        score += 10

    if use_cases:
        score += 10

    if budget:
        score += 10

    if payment_priority:
        score += 10

    if order_number:
        score += 20

    return min(score, 100)


# =====================================================
# CUSTOMER-FRIENDLY SUMMARY
# =====================================================

def analysis_to_short_summary(analysis):
    parts = []

    if analysis.get("primary_intent"):
        parts.append(f"Niyet: {analysis['primary_intent']}")

    if analysis.get("brands"):
        parts.append(f"Marka: {', '.join(analysis['brands'])}")

    if analysis.get("product_types"):
        parts.append(f"Ürün tipi: {', '.join(analysis['product_types'])}")

    if analysis.get("categories"):
        parts.append(f"Kategori: {', '.join(analysis['categories'])}")

    if analysis.get("budget"):
        parts.append(f"Bütçe: {analysis['budget']} TL")

    if analysis.get("payment_priority"):
        parts.append(f"Ödeme önceliği: {analysis['payment_priority']}")

    if analysis.get("order_number"):
        parts.append(f"Sipariş no: {analysis['order_number']}")

    parts.append(f"Güven: %{analysis.get('confidence', 0)}")

    return " | ".join(parts)


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    tests = [
        "Beko buzdolabı senetle olur mu, en avantajlı ödeme ne?",
        "50 bin TL bütçem var çeyiz için buzdolabı ve çamaşır makinesi öner",
        "Öğrenciyim 25 bin TL laptop lazım",
        "NVD-1001 siparişim nerede?",
        "Samsung televizyon stokta var mı havale fiyatı nedir?",
        "Lenova laptop istiyorum oyun için taksit olur mu?",
    ]

    for test in tests:
        result = analyze_user_query(test)
        print("\nSORU:", test)
        print(result)
        print(analysis_to_short_summary(result))