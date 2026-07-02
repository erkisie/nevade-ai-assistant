import re
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


# =====================================================
# CUSTOMER INTELLIGENCE ENGINE
# Advanced NLP + Semantic Intent Detection
# =====================================================

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_model = None


def get_model():
    global _model

    if SentenceTransformer is None:
        return None

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    tr_map = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    text = text.translate(tr_map)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def safe_number(value):
    try:
        if value is None or pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).lower()
        text = text.replace("tl", "")
        text = text.replace("₺", "")
        text = text.replace(".", "")
        text = text.replace(",", ".")
        text = re.sub(r"[^0-9.]", "", text)

        if text == "":
            return 0.0

        return float(text)

    except Exception:
        return 0.0


def money(value):
    value = safe_number(value)

    if value <= 0:
        return "-"

    return f"{value:,.0f} TL".replace(",", ".")


# =====================================================
# INTENT DEFINITIONS
# =====================================================

INTENT_PROTOTYPES = {
    "PRODUCT_RECOMMENDATION": [
        "ürün öner",
        "bana uygun ürün bul",
        "hangi ürünü almalıyım",
        "telefon öner",
        "laptop öner",
        "buzdolabı öner",
        "ihtiyacıma uygun ürün arıyorum",
    ],
    "PACKAGE_BUILDING": [
        "çeyiz paketi yap",
        "yeni ev için paket hazırla",
        "ev kuruyorum temel eşyalar lazım",
        "beyaz eşya paketi oluştur",
        "yeni eve taşınıyorum ürün paketi öner",
    ],
    "CART_RESCUE": [
        "kart limitim yetmedi",
        "limitim yetersiz",
        "ödeme yapamadım",
        "sepeti alamıyorum",
        "ürün pahalı geldi",
        "almaktan vazgeçiyorum",
        "bütçemi aştı",
    ],
    "PAYMENT_ALTERNATIVE": [
        "senetle alabilir miyim",
        "taksit olur mu",
        "havale fiyatı nedir",
        "ödeme seçenekleri neler",
        "kartla alamıyorum başka ödeme var mı",
    ],
    "CHEAPER_ALTERNATIVE": [
        "daha ucuz alternatif var mı",
        "uygun fiyatlı ürün göster",
        "bütçeme uygun ürün bul",
        "daha ekonomik model öner",
        "pahalı geldi daha ucuzu var mı",
    ],
    "PRODUCT_COMPARISON": [
        "iki ürünü karşılaştır",
        "hangisi daha iyi",
        "bu ürün mü daha mantıklı diğeri mi",
        "aralarındaki fark ne",
    ],
    "ORDER_SUPPORT": [
        "siparişim nerede",
        "kargo ne zaman gelir",
        "sipariş durumumu öğrenmek istiyorum",
        "faturam nerede",
        "iade etmek istiyorum",
    ],
    "STORE_STAFF_SUPPORT": [
        "müşteri bunu soruyor ne cevap vereyim",
        "mağaza için hızlı bilgi ver",
        "personel notu oluştur",
        "müşteriye nasıl anlatmalıyım",
    ],
    "GENERAL_HELP": [
        "yardım eder misin",
        "ne yapmalıyım",
        "bilgi almak istiyorum",
        "bana yardımcı ol",
    ],
}


COMMERCE_RISK_PATTERNS = {
    "LIMIT_YETERSIZ": [
        "limit yetmedi",
        "limitim yetmedi",
        "limit yetersiz",
        "kart limitim yetmedi",
        "kart limitim yetersiz",
        "karttan gecmedi",
        "karttan geçmedi",
        "odeme yapamiyorum",
        "ödeme yapamıyorum",
        "kart reddedildi",
        "kart kabul etmedi",
    ],
    "SEPET_TERK_RISKI": [
        "vazgectim",
        "vazgeçtim",
        "almayacagim",
        "almayacağım",
        "cok pahali",
        "çok pahalı",
        "pahali geldi",
        "pahalı geldi",
        "butcemi asti",
        "bütçemi aştı",
        "alamiyorum",
        "alamıyorum",
    ],
    "BUDGET_PRESSURE": [
        "butcem dusuk",
        "bütçem düşük",
        "butceme uymadi",
        "bütçeme uymadı",
        "daha uygunu",
        "daha ucuz",
        "ekonomik",
        "uygun fiyatli",
        "uygun fiyatlı",
    ],
    "PAYMENT_NEED": [
        "taksit",
        "senet",
        "senetli",
        "havale",
        "pesin",
        "peşin",
        "kart",
        "odeme",
        "ödeme",
    ],
}


CATEGORY_PATTERNS = {
    "Bilgisayar": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "oyun bilgisayari",
        "öğrenci bilgisayarı",
    ],
    "Telefon": [
        "telefon",
        "iphone",
        "samsung",
        "xiaomi",
        "android",
        "cep telefonu",
    ],
    "Beyaz Eşya": [
        "beyaz esya",
        "beyaz eşya",
        "buzdolabi",
        "buzdolabı",
        "camasir makinesi",
        "çamaşır makinesi",
        "bulasik makinesi",
        "bulaşık makinesi",
        "firin",
        "fırın",
    ],
    "Televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "oled",
        "qled",
        "4k",
    ],
    "Küçük Ev Aleti": [
        "supurge",
        "süpürge",
        "blender",
        "cay makinesi",
        "çay makinesi",
        "tost makinesi",
        "airfryer",
        "mutfak ürünü",
    ],
}


PRODUCT_TYPE_PATTERNS = {
    "laptop": ["laptop", "bilgisayar", "notebook", "macbook"],
    "telefon": ["telefon", "iphone", "android", "cep telefonu"],
    "buzdolabi": ["buzdolabi", "buzdolabı", "buz dolabi", "buz dolabı"],
    "camasir_makinesi": ["camasir makinesi", "çamaşır makinesi", "camasir", "çamaşır"],
    "bulasik_makinesi": ["bulasik makinesi", "bulaşık makinesi"],
    "firin": ["firin", "fırın", "ankastre", "mini fırın"],
    "televizyon": ["televizyon", "tv", "smart tv"],
    "supurge": ["supurge", "süpürge", "robot süpürge"],
    "blender": ["blender", "rondo", "doğrayıcı"],
    "cay_makinesi": ["cay makinesi", "çay makinesi"],
    "tost_makinesi": ["tost makinesi", "tost"],
}


PAYMENT_PATTERNS = {
    "senet": ["senet", "senetli", "elden ödeme"],
    "taksit": ["taksit", "aylık ödeme", "kaç taksit"],
    "havale": ["havale", "eft", "banka transferi"],
    "kart": ["kart", "kredi kartı", "kartla"],
    "pesin": ["peşin", "pesin", "nakit"],
}


# =====================================================
# ENTITY EXTRACTION
# =====================================================

def extract_budget(user_query):
    text = normalize_text(user_query)

    patterns = [
        r"(\d+)\s*bin",
        r"(\d+)\s*k",
        r"(\d+)\s*tl",
        r"(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            value = safe_number(match.group(1))

            if "bin" in match.group(0) or "k" in match.group(0):
                value *= 1000

            if value >= 500:
                return value

    return None


def extract_category(user_query):
    q = normalize_text(user_query)

    for category, words in CATEGORY_PATTERNS.items():
        for word in words:
            if normalize_text(word) in q:
                return category

    return None


def extract_product_type(user_query):
    q = normalize_text(user_query)

    for product_type, words in PRODUCT_TYPE_PATTERNS.items():
        for word in words:
            if normalize_text(word) in q:
                return product_type

    return None


def extract_payment_preferences(user_query):
    q = normalize_text(user_query)
    payments = []

    for payment, words in PAYMENT_PATTERNS.items():
        for word in words:
            if normalize_text(word) in q:
                payments.append(payment)
                break

    return payments


def detect_commerce_risks(user_query):
    q = normalize_text(user_query)
    risks = []

    for risk, patterns in COMMERCE_RISK_PATTERNS.items():
        for pattern in patterns:
            if normalize_text(pattern) in q:
                risks.append(risk)
                break

    return risks


# =====================================================
# SEMANTIC INTENT DETECTION
# =====================================================

def build_intent_examples():
    labels = []
    texts = []

    for intent, examples in INTENT_PROTOTYPES.items():
        for example in examples:
            labels.append(intent)
            texts.append(example)

    return labels, texts


def semantic_intent_detect(user_query):
    model = get_model()

    if model is None:
        return {
            "intent": "GENERAL_HELP",
            "confidence": 0,
            "method": "fallback_no_model",
        }

    labels, examples = build_intent_examples()

    try:
        query_emb = model.encode([user_query], convert_to_numpy=True)
        example_embs = model.encode(examples, convert_to_numpy=True)

        similarities = cosine_similarity(query_emb, example_embs).flatten()

        best_index = int(similarities.argmax())
        best_score = float(similarities[best_index]) * 100
        best_intent = labels[best_index]

        return {
            "intent": best_intent,
            "confidence": round(best_score, 2),
            "method": "sentence_transformer_embedding",
        }

    except Exception as e:
        print("Semantic intent error:", e)

        return {
            "intent": "GENERAL_HELP",
            "confidence": 0,
            "method": "error_fallback",
        }


def strengthen_intent_with_business_rules(user_query, semantic_result, commerce_risks):
    """
    Kritik ticari intentlerde embedding tek başına bırakılmaz.
    Limit, sepet terk, ödeme problemi gibi durumlar yüksek önceliklidir.
    """

    q = normalize_text(user_query)
    intent = semantic_result.get("intent", "GENERAL_HELP")
    confidence = semantic_result.get("confidence", 0)

    if "LIMIT_YETERSIZ" in commerce_risks:
        return "CART_RESCUE", max(confidence, 95)

    if "SEPET_TERK_RISKI" in commerce_risks:
        return "CART_RESCUE", max(confidence, 92)

    if "BUDGET_PRESSURE" in commerce_risks:
        return "CHEAPER_ALTERNATIVE", max(confidence, 88)

    if "PAYMENT_NEED" in commerce_risks and intent == "GENERAL_HELP":
        return "PAYMENT_ALTERNATIVE", max(confidence, 85)

    package_words = ["ceyiz", "çeyiz", "paket", "yeni ev", "ev kuruyorum", "tasiniyorum", "taşınıyorum"]

    if any(normalize_text(word) in q for word in package_words):
        return "PACKAGE_BUILDING", max(confidence, 90)

    return intent, confidence


# =====================================================
# MAIN ANALYSIS
# =====================================================

def analyze_customer_message(user_query):
    semantic_result = semantic_intent_detect(user_query)

    commerce_risks = detect_commerce_risks(user_query)

    final_intent, final_confidence = strengthen_intent_with_business_rules(
        user_query=user_query,
        semantic_result=semantic_result,
        commerce_risks=commerce_risks,
    )

    budget = extract_budget(user_query)
    category = extract_category(user_query)
    product_type = extract_product_type(user_query)
    payments = extract_payment_preferences(user_query)

    return {
        "original_query": user_query,
        "normalized_query": normalize_text(user_query),
        "intent": final_intent,
        "intent_confidence": final_confidence,
        "semantic_raw_intent": semantic_result.get("intent"),
        "semantic_confidence": semantic_result.get("confidence"),
        "intent_method": semantic_result.get("method"),
        "commerce_risks": commerce_risks,
        "budget": budget,
        "category": category,
        "product_type": product_type,
        "payments": payments,
        "is_cart_rescue": final_intent == "CART_RESCUE",
        "is_package": final_intent == "PACKAGE_BUILDING",
        "is_payment_help": final_intent == "PAYMENT_ALTERNATIVE",
        "is_cheaper_alternative": final_intent == "CHEAPER_ALTERNATIVE",
    }


def explain_customer_analysis(analysis):
    """
    UI veya debug panelinde okunabilir açıklama vermek için.
    """

    return (
        f"Intent: {analysis.get('intent')} "
        f"(%{analysis.get('intent_confidence')}) | "
        f"Kategori: {analysis.get('category') or '-'} | "
        f"Ürün tipi: {analysis.get('product_type') or '-'} | "
        f"Bütçe: {money(analysis.get('budget')) if analysis.get('budget') else '-'} | "
        f"Risk: {', '.join(analysis.get('commerce_risks', [])) if analysis.get('commerce_risks') else '-'}"
    )