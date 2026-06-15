import re
import difflib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =====================================================
# TEXT HELPERS
# =====================================================

def normalize_text(text):
    text = str(text).lower().strip()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def safe_number(value):
    try:
        if value is None:
            return 0

        text = str(value)
        text = text.replace("TL", "")
        text = text.replace("₺", "")
        text = text.replace(".", "")
        text = text.replace(",", ".")
        text = text.strip()

        if text == "":
            return 0

        return float(text)

    except Exception:
        return 0


def money(value):
    return f"{safe_number(value):,.0f} TL".replace(",", ".")


def extract_first_number(value):
    text = str(value).lower().replace(",", ".")
    found = re.findall(r"\d+\.?\d*", text)

    if len(found) == 0:
        return 0

    return float(found[0])


# =====================================================
# NLP DICTIONARIES
# =====================================================

CATEGORY_KEYWORDS = {
    "Bilgisayar": [
        "laptop", "bilgisayar", "notebook", "macbook", "dizustu",
        "ogrenci", "okul", "ders", "odev", "ofis", "is",
        "oyun", "gaming", "hafif", "tasinabilir", "islemci",
        "ram", "ssd", "depolama"
    ],
    "Telefon": [
        "telefon", "iphone", "samsung", "xiaomi", "oppo",
        "akilli telefon", "cep telefonu", "galaxy", "redmi",
        "kamera", "batarya", "hafiza"
    ],
    "Ev Elektroniği": [
        "supurge", "robot supurge", "airfryer", "kahve makinesi",
        "dyson", "philips", "temizlik", "ev aleti", "fritoz"
    ],
    "Beyaz Eşya": [
        "buzdolabi", "camasir", "camasir makinesi", "beyaz esya",
        "dolap", "makine", "enerji", "a kalite", "a+",
        "a++", "a+++", "kapasite", "hacim", "litre", "kg"
    ],
    "Televizyon": [
        "televizyon", "tv", "oled", "4k", "akilli tv", "ekran",
        "inc", "inch", "sinema"
    ]
}


BRAND_ALIASES = {
    "macbook": "apple",
    "iphone": "apple",
    "ios": "apple",
    "galaxy": "samsung",
    "redmi": "xiaomi",
    "mi telefon": "xiaomi",
    "ideapad": "lenovo",
    "idea pad": "lenovo",
    "vivobook": "asus",
    "aspire": "acer",
    "inspiron": "dell"
}


KNOWN_BRANDS = [
    "lenovo", "hp", "apple", "asus", "acer", "dell",
    "samsung", "xiaomi", "oppo", "philips", "dyson",
    "tefal", "karaca", "beko", "arcelik", "arçelik",
    "siemens", "bosch", "lg", "tcl"
]


INTENT_KEYWORDS = {
    "student_laptop": [
        "ogrenci laptop", "ogrenci bilgisayar", "okul icin laptop",
        "ders icin laptop", "uygun laptop", "fiyat performans laptop",
        "ogrenci dostu"
    ],
    "bundle_recommendation": [
        "ceyiz", "ev kuruyorum", "evlenecegim", "evlilik",
        "ev alisverisi", "ceyiz alisverisi"
    ],
    "comparison": [
        "karsilastir", "kiyasla", "hangisi", " vs ",
        " mi ", " mu ", " mu?", " mi?", "mı", "mü",
        "daha iyi", "daha avantajli", "daha mantikli"
    ],
    "similar": [
        "benzer", "alternatif", "buna benzer", "daha uygun alternatif"
    ],
    "payment_advice": [
        "senet", "senetle", "taksit", "kredi karti", "pesin",
        "nakit", "odeme", "aylik", "havale"
    ],
    "recommendation": [
        "oner", "listele", "istiyorum", "ariyorum", "alacagim",
        "tavsiye", "secenek"
    ]
}


PRIORITY_KEYWORDS = {
    "price": [
        "fiyat", "ucuz", "uygun", "ekonomik", "butce", "butce dostu"
    ],
    "capacity": [
        "kapasite", "capacity", "hacim", "litre", "lt", "l ", "kg"
    ],
    "energy": [
        "enerji", "a+", "a++", "a+++", "tasarruf"
    ],
    "performance": [
        "performans", "islemci", "processor", "ram", "ssd",
        "depolama", "storage", "hizli", "oyun", "gaming"
    ],
    "usage": [
        "kullanim kolayligi", "kullanim", "kolay", "pratik",
        "gunluk", "ogrenci", "aile", "ceyiz", "ofis", "is"
    ],
    "payment": [
        "odeme", "taksit", "senet", "havale", "pesin", "kart",
        "kredi karti", "nakit"
    ]
}


OPTIONAL_COLUMNS = [
    "cash_price",
    "bank_transfer_price",
    "card_price",
    "installment_3_total",
    "installment_6_total",
    "installment_9_total",
    "senet_total_price",
    "senet_monthly_9",
    "color",
    "processor",
    "ram",
    "storage",
    "screen_size",
    "energy_class",
    "capacity",
    "warranty",
    "rating",
    "payment_options",
    "use_case",
    "features"
]


# =====================================================
# MAIN ENGINE
# =====================================================

class AdvancedNevadeNLPEngine:
    def __init__(self, products_df):
        self.products_df = self.prepare_products(products_df)

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=15000
        )

        self.product_matrix = self.vectorizer.fit_transform(
            self.products_df["model_text"].tolist()
        )

    # -------------------------------------------------
    # DATA PREPARATION
    # -------------------------------------------------

    def prepare_products(self, df):
        df = df.copy().fillna("")

        required_columns = [
            "product_id",
            "product_name",
            "category",
            "brand",
            "price",
            "description",
            "stock_status",
            "installment_available",
            "product_link",
            "image_link"
        ]

        for column in required_columns:
            if column not in df.columns:
                df[column] = ""

        for column in OPTIONAL_COLUMNS:
            if column not in df.columns:
                df[column] = ""

        if df["product_id"].astype(str).str.strip().eq("").all():
            df["product_id"] = range(1, len(df) + 1)

        df["product_id"] = df["product_id"].astype(str)

        numeric_columns = [
            "price",
            "cash_price",
            "bank_transfer_price",
            "card_price",
            "installment_3_total",
            "installment_6_total",
            "installment_9_total",
            "senet_total_price",
            "senet_monthly_9"
        ]

        for column in numeric_columns:
            df[column] = df[column].apply(safe_number)

        df["stock_status"] = df["stock_status"].replace("", "Stokta")
        df["installment_available"] = df["installment_available"].replace("", "Evet")

        df["normalized_name"] = df["product_name"].apply(normalize_text)
        df["normalized_brand"] = df["brand"].apply(normalize_text)
        df["normalized_category"] = df["category"].apply(normalize_text)
        df["normalized_description"] = df["description"].apply(normalize_text)

        df["model_text"] = (
            df["product_name"].astype(str) + " " +
            df["category"].astype(str) + " " +
            df["brand"].astype(str) + " " +
            df["description"].astype(str) + " " +
            df["stock_status"].astype(str) + " " +
            df["installment_available"].astype(str) + " " +
            df["color"].astype(str) + " " +
            df["processor"].astype(str) + " " +
            df["ram"].astype(str) + " " +
            df["storage"].astype(str) + " " +
            df["screen_size"].astype(str) + " " +
            df["energy_class"].astype(str) + " " +
            df["capacity"].astype(str) + " " +
            df["warranty"].astype(str) + " " +
            df["payment_options"].astype(str) + " " +
            df["use_case"].astype(str) + " " +
            df["features"].astype(str)
        )

        df["model_text"] = df["model_text"].apply(normalize_text)

        return df

    # -------------------------------------------------
    # QUERY UNDERSTANDING
    # -------------------------------------------------

    def extract_budget(self, user_query):
        query = normalize_text(user_query)

        match = re.search(r"(\d+)\s*bin", query)
        if match:
            return int(match.group(1)) * 1000

        match = re.search(r"(\d+)\s*000", query)
        if match:
            value = int(match.group(1))
            if value < 1000:
                return value * 1000
            return value

        match = re.search(r"(\d+)\s*(tl|lira)", query)
        if match:
            return int(match.group(1))

        numbers = re.findall(r"\d+", query)

        if numbers:
            value = int(numbers[0])

            if value < 1000 and ("bin" in query or "000" in query):
                return value * 1000

            if value >= 1000:
                return value

        return None

    def detect_category(self, user_query):
        query = normalize_text(user_query)
        scores = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                if normalize_text(keyword) in query:
                    score += 1

            scores[category] = score

        best_category = max(scores, key=scores.get)

        if scores[best_category] == 0:
            return None

        return best_category

    def detect_brands(self, user_query):
        query = normalize_text(user_query)
        brands = []

        for alias, brand in BRAND_ALIASES.items():
            if normalize_text(alias) in query:
                normalized_brand = normalize_text(brand)

                if normalized_brand not in brands:
                    brands.append(normalized_brand)

        for brand in KNOWN_BRANDS:
            normalized_brand = normalize_text(brand)

            if normalized_brand in query:
                if normalized_brand not in brands:
                    brands.append(normalized_brand)

        return brands

    def detect_intent(self, user_query):
        query = normalize_text(user_query)
        scores = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                if normalize_text(keyword) in query:
                    score += 1

            scores[intent] = score

        best_intent = max(scores, key=scores.get)

        if scores[best_intent] == 0:
            return "recommendation"

        return best_intent

    def detect_priority(self, user_query):
        query = normalize_text(user_query)
        scores = {}

        for priority, keywords in PRIORITY_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                if normalize_text(keyword) in query:
                    score += 1

            scores[priority] = score

        best_priority = max(scores, key=scores.get)

        if scores[best_priority] == 0:
            return "balanced"

        return best_priority

    def detect_payment_preference(self, user_query):
        query = normalize_text(user_query)

        if "senet" in query or "senetle" in query:
            return "senet"

        if "havale" in query:
            return "bank_transfer"

        if "pesin" in query or "nakit" in query:
            return "cash"

        if "kredi karti" in query or "kart" in query:
            return "card"

        if "9 taksit" in query:
            return "installment_9"

        if "6 taksit" in query:
            return "installment_6"

        if "3 taksit" in query:
            return "installment_3"

        if "taksit" in query:
            return "installment"

        return None

    def understand_query(self, user_query):
        return {
            "original_query": user_query,
            "intent": self.detect_intent(user_query),
            "budget": self.extract_budget(user_query),
            "category": self.detect_category(user_query),
            "brands": self.detect_brands(user_query),
            "priority": self.detect_priority(user_query),
            "payment_preference": self.detect_payment_preference(user_query)
        }

    # -------------------------------------------------
    # FEATURE HELPERS
    # -------------------------------------------------

    def calculate_installment(self, price, months=6):
        return round(safe_number(price) / months, 2)

    def score_label(self, score):
        score = float(score)

        if score >= 0.85:
            return "En uygun seçenek"

        if score >= 0.70:
            return "Çok uygun"

        if score >= 0.50:
            return "Alternatif"

        return "Zayıf eşleşme"

    def get_energy_rank(self, value):
        value = str(value).upper().replace(" ", "")

        ranks = {
            "A+++": 5,
            "A++": 4,
            "A+": 3,
            "A": 2,
            "B": 1
        }

        return ranks.get(value, 0)

    def get_capacity_value(self, value):
        return extract_first_number(value)

    def get_ram_value(self, value):
        return extract_first_number(value)

    def get_storage_value(self, value):
        value_text = normalize_text(value)
        number = extract_first_number(value)

        if "tb" in value_text:
            return number * 1024

        return number

    # -------------------------------------------------
    # PAYMENT ENGINE
    # -------------------------------------------------

    def analyze_payment_options(self, row):
        price = safe_number(row.get("price", 0))
        cash = safe_number(row.get("cash_price", price))
        havale = safe_number(row.get("bank_transfer_price", price))
        card = safe_number(row.get("card_price", price))
        ins3 = safe_number(row.get("installment_3_total", 0))
        ins6 = safe_number(row.get("installment_6_total", 0))
        ins9 = safe_number(row.get("installment_9_total", 0))
        senet = safe_number(row.get("senet_total_price", 0))
        senet_monthly = safe_number(row.get("senet_monthly_9", 0))

        candidates = []

        if cash > 0:
            candidates.append(("Peşin", cash))

        if havale > 0:
            candidates.append(("Havale", havale))

        if card > 0:
            candidates.append(("Kart", card))

        if ins3 > 0:
            candidates.append(("3 Taksit", ins3))

        if ins6 > 0:
            candidates.append(("6 Taksit", ins6))

        if ins9 > 0:
            candidates.append(("9 Taksit", ins9))

        if senet > 0:
            candidates.append(("Senet", senet))

        if len(candidates) == 0:
            return {
                "best_method": "Liste fiyatı",
                "best_total": price,
                "senet_difference": 0,
                "senet_monthly_9": senet_monthly,
                "advice": "Bu ürün için ödeme alternatifi bilgisi sınırlı."
            }

        best_method, best_total = min(candidates, key=lambda x: x[1])

        senet_difference = 0

        if senet > 0:
            senet_difference = senet - best_total

        if senet > 0 and senet_difference > price * 0.12:
            advice = (
                f"Senetli toplam fiyat {money(senet)} olduğu için "
                f"{best_method} seçeneği daha avantajlı görünüyor. "
                f"Senet ile en avantajlı ödeme arasında yaklaşık {money(senet_difference)} fark var."
            )
        elif best_method == "Havale":
            advice = (
                f"Havale fiyatı {money(best_total)} ile en avantajlı ödeme seçeneği görünüyor."
            )
        elif "Taksit" in best_method:
            advice = (
                f"{best_method} toplamı {money(best_total)} ile ödeme kolaylığı açısından değerlendirilebilir."
            )
        else:
            advice = (
                f"Bu ürün için en avantajlı ödeme seçeneği {best_method}: {money(best_total)}."
            )

        return {
            "best_method": best_method,
            "best_total": best_total,
            "senet_difference": senet_difference,
            "senet_monthly_9": senet_monthly,
            "advice": advice
        }

    def payment_score(self, row, query_info):
        payment_preference = query_info.get("payment_preference")
        price = safe_number(row.get("price", 0))

        if payment_preference == "senet":
            senet = safe_number(row.get("senet_total_price", 0))

            if senet == 0:
                return 0.40

            difference_ratio = (senet - price) / price if price > 0 else 1

            if difference_ratio <= 0.10:
                return 1.0

            if difference_ratio <= 0.20:
                return 0.75

            return 0.45

        if payment_preference == "bank_transfer":
            havale = safe_number(row.get("bank_transfer_price", 0))

            if havale > 0 and havale < price:
                return 1.0

            return 0.60

        if payment_preference == "cash":
            cash = safe_number(row.get("cash_price", 0))

            if cash > 0 and cash <= price:
                return 1.0

            return 0.60

        if payment_preference in [
            "installment",
            "installment_3",
            "installment_6",
            "installment_9"
        ]:
            if str(row.get("installment_available", "")).lower() == "evet":
                return 1.0

            return 0.40

        return 0.75

    # -------------------------------------------------
    # FILTERING AND SCORING
    # -------------------------------------------------

    def filter_candidates(self, query_info):
        df = self.products_df.copy()

        if query_info.get("category"):
            df = df[df["category"] == query_info["category"]]

        if query_info.get("budget"):
            budget = float(query_info["budget"])
            under_budget = df[df["price"] <= budget]

            if not under_budget.empty:
                df = under_budget
            else:
                df["budget_distance"] = abs(df["price"] - budget)
                df = df.sort_values("budget_distance").head(10)

        if len(query_info.get("brands", [])) > 0:
            brand_df = df[df["normalized_brand"].isin(query_info["brands"])]

            if not brand_df.empty:
                df = brand_df

        if df.empty:
            df = self.products_df.copy()

        return df

    def feature_score_for_priority(self, row, priority):
        if priority == "capacity":
            capacity = self.get_capacity_value(row.get("capacity", ""))
            return min(capacity / 600, 1.0) if capacity > 0 else 0.50

        if priority == "energy":
            rank = self.get_energy_rank(row.get("energy_class", ""))
            return min(rank / 5, 1.0) if rank > 0 else 0.50

        if priority == "performance":
            ram = self.get_ram_value(row.get("ram", ""))
            storage = self.get_storage_value(row.get("storage", ""))

            score = 0.40

            if ram >= 16:
                score += 0.30
            elif ram >= 8:
                score += 0.20

            if storage >= 512:
                score += 0.30
            elif storage >= 256:
                score += 0.20

            return min(score, 1.0)

        if priority == "usage":
            use_case = normalize_text(row.get("use_case", ""))
            features = normalize_text(row.get("features", ""))

            score = 0.50

            if "gunluk" in use_case or "pratik" in features:
                score += 0.20

            if "ogrenci" in use_case:
                score += 0.20

            if "aile" in use_case or "ceyiz" in use_case:
                score += 0.20

            if "hafif" in features or "sessiz" in features:
                score += 0.10

            return min(score, 1.0)

        return 0.70

    def score_candidates(self, user_query, candidate_df):
        if candidate_df.empty:
            return candidate_df

        query_info = self.understand_query(user_query)
        priority = query_info.get("priority", "balanced")

        candidate_indexes = candidate_df.index.tolist()
        query_vector = self.vectorizer.transform([normalize_text(user_query)])

        similarities = cosine_similarity(
            query_vector,
            self.product_matrix[candidate_indexes]
        )[0]

        result = candidate_df.copy()
        result["nlp_score"] = similarities

        min_price = result["price"].min()
        max_price = result["price"].max()

        if min_price == max_price:
            result["price_score"] = 1
        else:
            result["price_score"] = 1 - (
                (result["price"] - min_price) / (max_price - min_price)
            )

        result["stock_score"] = result["stock_status"].astype(str).str.lower().apply(
            lambda value: 1 if value == "stokta" else 0
        )

        result["installment_score"] = result["installment_available"].astype(str).str.lower().apply(
            lambda value: 1 if value == "evet" else 0.4
        )

        result["payment_score"] = result.apply(
            lambda row: self.payment_score(row, query_info),
            axis=1
        )

        result["feature_score"] = result.apply(
            lambda row: self.feature_score_for_priority(row, priority),
            axis=1
        )

        if priority == "price":
            result["final_score"] = (
                result["price_score"] * 0.45 +
                result["nlp_score"] * 0.20 +
                result["payment_score"] * 0.20 +
                result["stock_score"] * 0.10 +
                result["feature_score"] * 0.05
            )

        elif priority in ["capacity", "energy", "performance", "usage"]:
            result["final_score"] = (
                result["feature_score"] * 0.35 +
                result["nlp_score"] * 0.25 +
                result["price_score"] * 0.20 +
                result["payment_score"] * 0.10 +
                result["stock_score"] * 0.10
            )

        elif priority == "payment":
            result["final_score"] = (
                result["payment_score"] * 0.40 +
                result["price_score"] * 0.25 +
                result["nlp_score"] * 0.20 +
                result["feature_score"] * 0.10 +
                result["stock_score"] * 0.05
            )

        else:
            result["final_score"] = (
                result["nlp_score"] * 0.35 +
                result["price_score"] * 0.25 +
                result["payment_score"] * 0.15 +
                result["feature_score"] * 0.15 +
                result["stock_score"] * 0.10
            )

        return result.sort_values("final_score", ascending=False)

    # -------------------------------------------------
    # OUTPUT
    # -------------------------------------------------

    def product_to_json(self, row, reason, score=0.70):
        price = safe_number(row.get("price", 0))

        return {
            "product_id": str(row.get("product_id", "")),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "price": price,
            "cash_price": safe_number(row.get("cash_price", "")),
            "bank_transfer_price": safe_number(row.get("bank_transfer_price", "")),
            "card_price": safe_number(row.get("card_price", "")),
            "installment_3_total": safe_number(row.get("installment_3_total", "")),
            "installment_6_total": safe_number(row.get("installment_6_total", "")),
            "installment_9_total": safe_number(row.get("installment_9_total", "")),
            "senet_total_price": safe_number(row.get("senet_total_price", "")),
            "senet_monthly_9": safe_number(row.get("senet_monthly_9", "")),
            "stock_status": row.get("stock_status", ""),
            "installment_available": row.get("installment_available", ""),
            "monthly_installment_6": self.calculate_installment(price, 6),
            "final_score": round(float(score), 4),
            "match_label": self.score_label(score),
            "reason": reason,
            "product_link": row.get("product_link", ""),
            "image_link": row.get("image_link", ""),
            "payment_analysis": self.analyze_payment_options(row),
            "specs": {
                "Renk": row.get("color", ""),
                "İşlemci": row.get("processor", ""),
                "RAM": row.get("ram", ""),
                "Depolama": row.get("storage", ""),
                "Ekran": row.get("screen_size", ""),
                "Enerji Sınıfı": row.get("energy_class", ""),
                "Kapasite": row.get("capacity", ""),
                "Garanti": row.get("warranty", ""),
                "Ödeme Seçenekleri": row.get("payment_options", ""),
                "Kullanım Amacı": row.get("use_case", ""),
                "Özellikler": row.get("features", "")
            }
        }

    # -------------------------------------------------
    # EXPLANATION ENGINE
    # -------------------------------------------------

    def explain_feature_advantage(self, row, query_info):
        priority = query_info.get("priority", "balanced")
        category = row.get("category", "")

        if priority == "capacity":
            return f"Kapasite bilgisi {row.get('capacity', '-')} olduğu için kapasite kriterinde değerlendirildi."

        if priority == "energy":
            return f"Enerji sınıfı {row.get('energy_class', '-')} olduğu için uzun vadeli tüketim açısından değerlendirildi."

        if priority == "performance":
            return (
                f"Performans tarafında işlemci {row.get('processor', '-')}, "
                f"RAM {row.get('ram', '-')}, depolama {row.get('storage', '-')} olarak dikkate alındı."
            )

        if priority == "usage":
            return (
                f"Kullanım amacı '{row.get('use_case', '-')}' ve özellikleri "
                f"'{row.get('features', '-')}' olduğu için kullanım kolaylığı açısından değerlendirildi."
            )

        if category == "Beyaz Eşya":
            return (
                f"Kapasite {row.get('capacity', '-')}, enerji sınıfı {row.get('energy_class', '-')} "
                f"ve garanti {row.get('warranty', '-')} bilgileri dikkate alındı."
            )

        if category == "Bilgisayar":
            return (
                f"İşlemci {row.get('processor', '-')}, RAM {row.get('ram', '-')}, "
                f"depolama {row.get('storage', '-')} ve kullanım amacı dikkate alındı."
            )

        return "Ürünün fiyatı, stok durumu, ödeme seçenekleri ve açıklama bilgisi birlikte değerlendirildi."

    def create_recommendation_reason(self, row, user_query, query_info):
        price = safe_number(row.get("price", 0))
        monthly = self.calculate_installment(price, 6)

        payment_analysis = self.analyze_payment_options(row)
        feature_sentence = self.explain_feature_advantage(row, query_info)

        parts = []

        parts.append(
            "Bu ürün, yazdığınız ihtiyaca kategori, marka, açıklama, ödeme seçeneği ve ürün özellikleri açısından uygun olduğu için önerildi."
        )

        parts.append(
            f"{row.get('brand', '')} markasına ait, {row.get('category', '')} kategorisindedir."
        )

        if query_info.get("budget"):
            budget = float(query_info["budget"])

            if price <= budget:
                parts.append(f"{money(budget)} bütçenizin altında kalıyor.")
            else:
                parts.append(f"{money(budget)} bütçenize en yakın alternatiflerden biridir.")

        parts.append(
            f"Liste fiyatı {money(price)}, 6 taksit tutarı yaklaşık {monthly:.0f} TL x 6."
        )

        parts.append(feature_sentence)
        parts.append(payment_analysis["advice"])

        return " ".join(parts)

    # -------------------------------------------------
    # RECOMMENDATION
    # -------------------------------------------------

    def recommend(self, user_query, top_n=6):
        query_info = self.understand_query(user_query)
        candidates = self.filter_candidates(query_info)
        scored = self.score_candidates(user_query, candidates).head(top_n)

        products = []

        for _, row in scored.iterrows():
            score = float(row.get("final_score", 0.70))
            reason = self.create_recommendation_reason(row, user_query, query_info)

            products.append(
                self.product_to_json(row, reason, score)
            )

        return products, query_info

    # -------------------------------------------------
    # SPECIAL CASES
    # -------------------------------------------------

    def recommend_student_laptops(self, user_query):
        df = self.products_df[
            self.products_df["category"] == "Bilgisayar"
        ].copy()

        if df.empty:
            return [], "Laptop kategorisinde ürün bulunamadı."

        scored = self.score_candidates(
            "ogrenci dostu uygun fiyatli laptop hafif tasinabilir taksit okul ders",
            df
        ).head(4)

        products = []

        for _, row in scored.iterrows():
            score = float(row.get("final_score", 0.80))
            payment_analysis = self.analyze_payment_options(row)

            reason = (
                f"Bu laptop öğrenci kullanımı için fiyat/performans, taksit, taşınabilirlik ve günlük kullanım açısından değerlendirildi. "
                f"İşlemci: {row.get('processor', '-')}, RAM: {row.get('ram', '-')}, depolama: {row.get('storage', '-')}. "
                f"{payment_analysis['advice']}"
            )

            products.append(
                self.product_to_json(row, reason, score)
            )

        best = products[0]

        message = (
            f"Öğrenci dostu laptoplar içinde en uygun seçenek {best['product_name']} görünüyor. "
            f"Aşağıda fiyat, ödeme seçeneği ve teknik özellik açısından alternatifleriyle birlikte listeledim."
        )

        return products, message

    def recommend_ceyiz_bundle(self, user_query):
        query_info = self.understand_query(user_query)
        budget = query_info.get("budget") or 50000

        df = self.products_df[
            self.products_df["category"].isin(
                ["Beyaz Eşya", "Ev Elektroniği", "Televizyon"]
            )
        ].copy()

        df = df.sort_values("price")

        priority_words = [
            "buzdolabi",
            "camasir",
            "supurge",
            "airfryer",
            "kahve",
            "televizyon",
            "tv"
        ]

        selected = []
        used_ids = set()
        total = 0

        for keyword in priority_words:
            candidates = df[
                df["normalized_name"].str.contains(keyword, na=False)
            ].sort_values("price")

            for _, row in candidates.iterrows():
                product_id = str(row["product_id"])
                price = safe_number(row["price"])

                if product_id not in used_ids and total + price <= budget:
                    selected.append(row)
                    used_ids.add(product_id)
                    total += price
                    break

        for _, row in df.iterrows():
            product_id = str(row["product_id"])
            price = safe_number(row["price"])

            if len(selected) >= 6:
                break

            if product_id not in used_ids and total + price <= budget:
                selected.append(row)
                used_ids.add(product_id)
                total += price

        products = []

        for row in selected:
            payment_analysis = self.analyze_payment_options(row)

            reason = (
                f"Bu ürün çeyiz alışverişinde temel ihtiyaçlardan biri olduğu ve bütçeye uyduğu için seçildi. "
                f"{self.explain_feature_advantage(row, query_info)} "
                f"{payment_analysis['advice']}"
            )

            products.append(
                self.product_to_json(row, reason, 0.82)
            )

        message = (
            f"{money(budget)} bütçeye göre çeyiz alışverişi için uygun ürünleri listeledim. "
            f"Seçilen ürünlerin toplamı yaklaşık {money(total)}. "
            f"Kalan bütçe yaklaşık {money(budget - total)}."
        )

        return products, message

    # -------------------------------------------------
    # PRODUCT MATCHING
    # -------------------------------------------------

    def similarity_ratio(self, a, b):
        return difflib.SequenceMatcher(
            None,
            normalize_text(a),
            normalize_text(b)
        ).ratio()

    def split_comparison_terms(self, user_query):
        query = normalize_text(user_query)

        remove_words = [
            "bana", "sence", "hangisi", "daha iyi", "karsilastir",
            "kiyasla", "oner", "fiyat", "kullanim", "kolayligi",
            "kapasite", "enerji", "performans", "taksit", "senet",
            "havale", "pesin", "odeme", "acisindan", "gore"
        ]

        for word in remove_words:
            query = query.replace(normalize_text(word), " ")

        separators = [
            " mi ", " mu ", " veya ", " ya da ", " ile ", " vs ", ",", "/"
        ]

        cleaned = query

        for separator in separators:
            cleaned = cleaned.replace(separator, "|")

        terms = [
            term.strip()
            for term in cleaned.split("|")
            if term.strip() != ""
        ]

        return terms

    def find_best_product_for_term(self, term):
        term = normalize_text(term)

        alias_brand = None

        for alias, brand in BRAND_ALIASES.items():
            if normalize_text(alias) in term:
                alias_brand = normalize_text(brand)

        best_score = 0
        best_row = None

        for _, row in self.products_df.iterrows():
            product_name = normalize_text(row.get("product_name", ""))
            brand = normalize_text(row.get("brand", ""))
            category = normalize_text(row.get("category", ""))
            description = normalize_text(row.get("description", ""))
            model_text = normalize_text(row.get("model_text", ""))

            score = 0

            if term == product_name:
                score += 150

            if term in product_name:
                score += 120

            if product_name in term:
                score += 90

            if term == brand:
                score += 95

            if term in brand:
                score += 80

            if alias_brand and alias_brand == brand:
                score += 100

            if term in category:
                score += 35

            if term in description:
                score += 30

            if term in model_text:
                score += 25

            score += self.similarity_ratio(term, product_name) * 55
            score += self.similarity_ratio(term, brand) * 40

            if alias_brand:
                score += self.similarity_ratio(alias_brand, brand) * 50

            if score > best_score:
                best_score = score
                best_row = row

        if best_score < 40:
            return None

        return best_row

    def find_products_in_text(self, user_query):
        terms = self.split_comparison_terms(user_query)
        found = []

        for term in terms:
            product = self.find_best_product_for_term(term)

            if product is not None:
                product_id = str(product.get("product_id", ""))

                exists = any(
                    str(item.get("product_id", "")) == product_id
                    for item in found
                )

                if not exists:
                    found.append(product)

        if len(found) < 2:
            brands = self.detect_brands(user_query)

            for brand in brands:
                rows = self.products_df[
                    self.products_df["normalized_brand"] == normalize_text(brand)
                ].copy()

                if not rows.empty:
                    selected = rows.sort_values("price").iloc[0]
                    product_id = str(selected.get("product_id", ""))

                    exists = any(
                        str(item.get("product_id", "")) == product_id
                        for item in found
                    )

                    if not exists:
                        found.append(selected)

        return found

    # -------------------------------------------------
    # COMPARISON
    # -------------------------------------------------

    def compare(self, user_query):
        found = self.find_products_in_text(user_query)
        query_info = self.understand_query(user_query)

        if len(found) < 2:
            products, _ = self.recommend(user_query, top_n=4)

            return (
                products,
                "Karşılaştırmak istediğiniz iki ürünü tam net yakalayamadım. "
                "Yine de sorgunuza en yakın ürünleri listeledim. "
                "Daha kontrollü karşılaştırma için kategori seçip envanterden iki ürün seçebilirsiniz."
            )

        p1 = found[0]
        p2 = found[1]

        return self.compare_rows(p1, p2, query_info)

    def compare_rows(self, row1, row2, query_info):
        priority = query_info.get("priority", "balanced")

        price1 = safe_number(row1["price"])
        price2 = safe_number(row2["price"])

        winner = None
        decision_reason = ""

        if priority == "price":
            winner = row1 if price1 <= price2 else row2

            decision_reason = (
                f"Fiyat kriterinde {winner['product_name']} daha avantajlıdır. "
                f"Çünkü liste fiyatı {money(winner['price'])}."
            )

        elif priority == "capacity":
            cap1 = self.get_capacity_value(row1.get("capacity", ""))
            cap2 = self.get_capacity_value(row2.get("capacity", ""))

            winner = row1 if cap1 >= cap2 else row2

            decision_reason = (
                f"Kapasite kriterinde {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} kapasitesi {row1.get('capacity', '-')}, "
                f"{row2['product_name']} kapasitesi {row2.get('capacity', '-')}."
            )

        elif priority == "energy":
            rank1 = self.get_energy_rank(row1.get("energy_class", ""))
            rank2 = self.get_energy_rank(row2.get("energy_class", ""))

            winner = row1 if rank1 >= rank2 else row2

            decision_reason = (
                f"Enerji sınıfında {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} enerji sınıfı {row1.get('energy_class', '-')}, "
                f"{row2['product_name']} enerji sınıfı {row2.get('energy_class', '-')}."
            )

        elif priority == "performance":
            perf1 = self.feature_score_for_priority(row1, "performance")
            perf2 = self.feature_score_for_priority(row2, "performance")

            winner = row1 if perf1 >= perf2 else row2

            decision_reason = (
                f"Performans kriterinde {winner['product_name']} daha avantajlıdır. "
                f"{row1['product_name']} işlemci/RAM/depolama: "
                f"{row1.get('processor', '-')}, {row1.get('ram', '-')}, {row1.get('storage', '-')}; "
                f"{row2['product_name']} işlemci/RAM/depolama: "
                f"{row2.get('processor', '-')}, {row2.get('ram', '-')}, {row2.get('storage', '-')}."
            )

        elif priority == "payment":
            pay1 = self.payment_score(row1, query_info)
            pay2 = self.payment_score(row2, query_info)

            winner = row1 if pay1 >= pay2 else row2

            decision_reason = (
                f"Ödeme kriterinde {winner['product_name']} daha avantajlıdır. "
                f"{self.analyze_payment_options(winner)['advice']}"
            )

        elif priority == "usage":
            usage1 = self.feature_score_for_priority(row1, "usage")
            usage2 = self.feature_score_for_priority(row2, "usage")

            winner = row1 if usage1 >= usage2 else row2

            decision_reason = (
                f"Kullanım kolaylığı kriterinde {winner['product_name']} daha avantajlı görünüyor. "
                f"{row1['product_name']} kullanım amacı: {row1.get('use_case', '-')}; "
                f"{row2['product_name']} kullanım amacı: {row2.get('use_case', '-')}. "
                f"Kapasite, enerji sınıfı, özellikler ve günlük kullanım amacı birlikte değerlendirildi."
            )

        else:
            score1 = (
                self.feature_score_for_priority(row1, "usage") * 0.35 +
                self.payment_score(row1, query_info) * 0.25 +
                self.feature_score_for_priority(row1, "capacity") * 0.20 +
                self.feature_score_for_priority(row1, "energy") * 0.20
            )

            score2 = (
                self.feature_score_for_priority(row2, "usage") * 0.35 +
                self.payment_score(row2, query_info) * 0.25 +
                self.feature_score_for_priority(row2, "capacity") * 0.20 +
                self.feature_score_for_priority(row2, "energy") * 0.20
            )

            winner = row1 if score1 >= score2 else row2

            decision_reason = (
                f"Genel değerlendirmede {winner['product_name']} daha dengeli seçenek görünüyor. "
                f"Fiyat, ödeme seçenekleri, stok, kullanım amacı ve ürün özellikleri birlikte dikkate alındı."
            )

        monthly1 = self.calculate_installment(price1, 6)
        monthly2 = self.calculate_installment(price2, 6)

        message = (
            f"{row1['product_name']} ve {row2['product_name']} karşılaştırıldı. "
            f"{decision_reason} "
            f"6 taksit hesabında {row1['product_name']} aylık yaklaşık {monthly1:.0f} TL, "
            f"{row2['product_name']} aylık yaklaşık {monthly2:.0f} TL olur."
        )

        products = []

        for row in [row1, row2]:
            is_winner = str(row["product_id"]) == str(winner["product_id"])
            score = 0.92 if is_winner else 0.58

            label_reason = (
                "Bu ürün seçtiğiniz kritere göre daha avantajlı olduğu için öne çıkarıldı."
                if is_winner
                else "Bu ürün alternatif olarak değerlendirildi; seçtiğiniz kritere göre diğer ürün daha avantajlı görünüyor."
            )

            reason = (
                f"{label_reason} "
                f"{self.explain_feature_advantage(row, query_info)} "
                f"{self.analyze_payment_options(row)['advice']}"
            )

            product = self.product_to_json(row, reason, score)

            product["match_label"] = "Daha avantajlı" if is_winner else "Alternatif"

            products.append(product)

        return products, message