import re

from src.utils import normalize_text


CATEGORY_KEYWORDS = {
    "Bilgisayar": [
        "laptop", "bilgisayar", "notebook", "macbook", "dizustu", "dizüstü",
        "ogrenci", "öğrenci", "okul", "ders", "ofis", "yazilim", "yazılım",
        "oyun", "gaming", "islemci", "işlemci", "ram", "ssd", "depolama"
    ],
    "Telefon": [
        "telefon", "iphone", "samsung", "xiaomi", "oppo", "akilli telefon",
        "akıllı telefon", "cep telefonu", "galaxy", "redmi", "kamera",
        "batarya", "hafiza", "hafıza"
    ],
    "Beyaz Eşya": [
        "buzdolabi", "buzdolabı", "dolap", "camasir", "çamaşır",
        "camasir makinesi", "çamaşır makinesi", "beyaz esya", "beyaz eşya",
        "enerji", "kapasite", "hacim", "litre", "lt", "kg",
        "ceyiz", "çeyiz", "evlilik", "ev kuruyorum"
    ],
    "Ev Elektroniği": [
        "supurge", "süpürge", "robot supurge", "robot süpürge", "airfryer",
        "fritoz", "fritöz", "kahve makinesi", "dyson", "philips",
        "temizlik", "ev aleti", "mutfak"
    ],
    "Televizyon": [
        "televizyon", "tv", "oled", "4k", "akilli tv", "akıllı tv",
        "ekran", "sinema", "salon", "film"
    ]
}


PRODUCT_TYPE_KEYWORDS = {
    "buzdolabi": [
        "buzdolabi", "buzdolabı", "dolap", "fridge", "sogutucu", "soğutucu"
    ],
    "camasir_makinesi": [
        "camasir makinesi", "çamaşır makinesi", "camasir", "çamaşır",
        "yikama", "yıkama"
    ],
    "laptop": [
        "laptop", "bilgisayar", "notebook", "macbook", "dizustu", "dizüstü"
    ],
    "telefon": [
        "telefon", "iphone", "galaxy", "redmi", "cep telefonu", "akilli telefon", "akıllı telefon"
    ],
    "supurge": [
        "supurge", "süpürge", "robot supurge", "robot süpürge", "dyson"
    ],
    "televizyon": [
        "televizyon", "tv", "oled", "4k", "akilli tv", "akıllı tv"
    ],
    "airfryer": [
        "airfryer", "fritoz", "fritöz"
    ],
    "kahve_makinesi": [
        "kahve makinesi", "kahve"
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
    "victus": "hp",
    "pavilion": "hp"
}


KNOWN_BRANDS = [
    "lenovo", "hp", "apple", "asus", "acer", "dell",
    "samsung", "xiaomi", "oppo", "philips", "dyson",
    "tefal", "karaca", "beko", "arcelik", "arçelik",
    "siemens", "bosch", "lg", "tcl"
]


INTENT_KEYWORDS = {
    "student_laptop": [
        "ogrenci laptop", "öğrenci laptop", "ogrenci bilgisayar", "öğrenci bilgisayar",
        "okul icin laptop", "okul için laptop", "ders icin laptop", "ders için laptop",
        "ogrenci dostu", "öğrenci dostu"
    ],
    "bundle_recommendation": [
        "ceyiz", "çeyiz", "ev kuruyorum", "evlenecegim", "evleneceğim",
        "evlilik", "ev alisverisi", "ev alışverişi", "ceyiz alisverisi",
        "çeyiz alışverişi", "set oner", "set öner"
    ],
    "comparison": [
        "karsilastir", "karşılaştır", "kiyasla", "kıyasla", "hangisi",
        "daha iyi", "daha mantikli", "daha mantıklı", "daha avantajli",
        "daha avantajlı", "vs", "mi yoksa"
    ],
    "similar": [
        "benzer", "alternatif", "buna benzer", "daha uygun alternatif",
        "muadili", "yerine ne alabilirim"
    ],
    "recommendation": [
        "oner", "öner", "listele", "istiyorum", "ariyorum", "arıyorum",
        "alacagim", "alacağım", "tavsiye", "secenek", "seçenek", "bul"
    ]
}


PRIORITY_KEYWORDS = {
    "payment": [
        "senet", "senetle", "havale", "pesin", "peşin", "nakit",
        "kart", "kredi karti", "kredi kartı", "taksit", "odeme", "ödeme",
        "aylik", "aylık", "vade", "vadesiz", "toplam ödeme"
    ],
    "price": [
        "fiyat", "ucuz", "uygun", "uyguna", "ekonomik", "butce", "bütçe",
        "butce dostu", "bütçe dostu", "en hesapli", "en hesaplı", "indirimli"
    ],
    "capacity": [
        "kapasite", "capacity", "hacim", "litre", "lt", "kg", "genis", "geniş",
        "buyuk", "büyük", "aile icin", "aile için"
    ],
    "energy": [
        "enerji", "a+", "a++", "a+++", "tasarruf", "az yakar", "verimli",
        "enerji sinifi", "enerji sınıfı"
    ],
    "performance": [
        "performans", "islemci", "işlemci", "processor", "ram", "ssd",
        "depolama", "storage", "hizli", "hızlı", "oyun", "gaming",
        "yazilim", "yazılım", "tasarim", "tasarım"
    ],
    "usage": [
        "kullanim kolayligi", "kullanım kolaylığı", "kullanim", "kullanım",
        "kolay", "pratik", "gunluk", "günlük", "aile", "ceyiz", "çeyiz",
        "ofis", "ogrenci", "öğrenci", "hafif", "sessiz"
    ]
}


PAYMENT_KEYWORDS = {
    "senet": ["senet", "senetle", "senetli"],
    "bank_transfer": ["havale", "eft", "banka transferi"],
    "cash": ["pesin", "peşin", "nakit"],
    "card": ["kart", "kredi karti", "kredi kartı"],
    "installment_9": ["9 taksit", "dokuz taksit"],
    "installment_6": ["6 taksit", "alti taksit", "altı taksit"],
    "installment_3": ["3 taksit", "uc taksit", "üç taksit"],
    "installment": ["taksit", "aylik", "aylık", "vade"]
}


class NLPQueryEngine:
    def extract_budget(self, user_query):
        query = normalize_text(user_query)

        # 50 bin, 50k, 50.000, 50000 TL gibi ifadeleri yakalar
        match = re.search(r"(\d+)\s*(bin|k)", query)
        if match:
            return int(match.group(1)) * 1000

        numbers = re.findall(r"\d[\d\.\,]*", query)

        if not numbers:
            return None

        raw = numbers[0]
        cleaned = raw.replace(".", "").replace(",", "")

        try:
            value = int(cleaned)
        except Exception:
            return None

        if value < 1000 and ("bin" in query or "k" in query):
            return value * 1000

        return value

    def detect_category(self, user_query):
        query = normalize_text(user_query)
        scores = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                keyword_norm = normalize_text(keyword)

                if keyword_norm in query:
                    score += 2

            scores[category] = score

        best_category = max(scores, key=scores.get)

        if scores[best_category] == 0:
            return None

        return best_category

    def detect_product_type(self, user_query):
        query = normalize_text(user_query)

        type_scores = {}

        for product_type, keywords in PRODUCT_TYPE_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                keyword_norm = normalize_text(keyword)

                if keyword_norm in query:
                    score += 3

            type_scores[product_type] = score

        best_type = max(type_scores, key=type_scores.get)

        if type_scores[best_type] == 0:
            return None

        return best_type

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

    def detect_payment_preference(self, user_query):
        query = normalize_text(user_query)

        for payment_type, keywords in PAYMENT_KEYWORDS.items():
            for keyword in keywords:
                if normalize_text(keyword) in query:
                    return payment_type

        return None

    def detect_priority(self, user_query):
        query = normalize_text(user_query)

        payment_preference = self.detect_payment_preference(query)

        if payment_preference:
            return "payment"

        scores = {}

        for priority, keywords in PRIORITY_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                keyword_norm = normalize_text(keyword)

                if keyword_norm in query:
                    score += 2

            scores[priority] = score

        best_priority = max(scores, key=scores.get)

        if scores[best_priority] == 0:
            return "balanced"

        return best_priority

    def detect_intent(self, user_query):
        query = normalize_text(user_query)
        scores = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                if normalize_text(keyword) in query:
                    score += 2

            scores[intent] = score

        # Ürün önerme cümlelerinde intent recommendation olarak kalsın
        if any(word in query for word in ["oner", "öner", "tavsiye", "bul", "ariyorum", "arıyorum"]):
            scores["recommendation"] += 1

        best_intent = max(scores, key=scores.get)

        if scores[best_intent] == 0:
            return "recommendation"

        return best_intent

    def detect_user_profile(self, user_query):
        query = normalize_text(user_query)

        profiles = []

        if any(word in query for word in ["ogrenci", "öğrenci", "okul", "ders"]):
            profiles.append("öğrenci")

        if any(word in query for word in ["aile", "cocuklu", "çocuklu", "ev"]):
            profiles.append("aile")

        if any(word in query for word in ["ceyiz", "çeyiz", "evlilik", "evlenecegim", "evleneceğim"]):
            profiles.append("çeyiz")

        if any(word in query for word in ["oyun", "gaming"]):
            profiles.append("oyun")

        if any(word in query for word in ["ofis", "is", "iş", "calisma", "çalışma"]):
            profiles.append("ofis")

        return profiles

    def understand(self, user_query):
        product_type = self.detect_product_type(user_query)
        category = self.detect_category(user_query)

        # Product type kategoriye göre daha spesifik olduğu için kategori boşsa tamamla
        if category is None:
            if product_type in ["buzdolabi", "camasir_makinesi"]:
                category = "Beyaz Eşya"
            elif product_type == "laptop":
                category = "Bilgisayar"
            elif product_type == "telefon":
                category = "Telefon"
            elif product_type in ["supurge", "airfryer", "kahve_makinesi"]:
                category = "Ev Elektroniği"
            elif product_type == "televizyon":
                category = "Televizyon"

        return {
            "original_query": user_query,
            "intent": self.detect_intent(user_query),
            "category": category,
            "product_type": product_type,
            "budget": self.extract_budget(user_query),
            "brands": self.detect_brands(user_query),
            "payment_preference": self.detect_payment_preference(user_query),
            "priority": self.detect_priority(user_query),
            "user_profile": self.detect_user_profile(user_query)
        }