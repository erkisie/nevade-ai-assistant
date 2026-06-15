import os
import re
import json
import pickle
import difflib

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


MODEL_DIR = "models"
TFIDF_MODEL_PATH = os.path.join(MODEL_DIR, "nevade_tfidf_vectorizer.pkl")
TFIDF_MATRIX_PATH = os.path.join(MODEL_DIR, "nevade_product_matrix.pkl")


CATEGORY_KEYWORDS = {
    "Bilgisayar": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "dizüstü",
        "dizustu",
        "öğrenci bilgisayarı",
        "oyun bilgisayarı",
        "iş bilgisayarı"
    ],
    "Telefon": [
        "telefon",
        "iphone",
        "samsung",
        "xiaomi",
        "oppo",
        "akıllı telefon",
        "cep telefonu",
        "galaxy",
        "redmi"
    ],
    "Ev Elektroniği": [
        "süpürge",
        "robot süpürge",
        "airfryer",
        "kahve makinesi",
        "dyson",
        "philips",
        "ev aleti",
        "temizlik"
    ],
    "Beyaz Eşya": [
        "buzdolabı",
        "çamaşır makinesi",
        "beyaz eşya",
        "dolap",
        "makine"
    ],
    "Televizyon": [
        "televizyon",
        "tv",
        "oled",
        "4k",
        "akıllı tv"
    ]
}


BRAND_ALIASES = {
    "macbook": "apple",
    "iphone": "apple",
    "ios": "apple",
    "galaxy": "samsung",
    "redmi": "xiaomi",
    "mi": "xiaomi",
    "idea pad": "lenovo",
    "ideapad": "lenovo",
    "vivobook": "asus",
    "aspire": "acer",
    "inspiron": "dell"
}


KNOWN_BRANDS = [
    "lenovo",
    "hp",
    "apple",
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
    "arcelik",
    "siemens",
    "bosch",
    "lg",
    "tcl"
]


class NevadeAIEngine:
    def __init__(self, products_df):
        self.products_df = self.prepare_products(products_df)
        self.vectorizer = None
        self.product_matrix = None
        self.train_tfidf_model()

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

        if df["product_id"].astype(str).str.strip().eq("").all():
            df["product_id"] = range(1, len(df) + 1)

        df["product_id"] = df["product_id"].astype(str)

        df["price"] = (
            df["price"]
            .astype(str)
            .str.replace("TL", "", regex=False)
            .str.replace("₺", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

        df["stock_status"] = df["stock_status"].replace("", "Stokta")
        df["installment_available"] = df["installment_available"].replace("", "Evet")

        df["ai_text"] = (
            df["product_name"].astype(str) + " " +
            df["category"].astype(str) + " " +
            df["brand"].astype(str) + " " +
            df["description"].astype(str) + " " +
            df["stock_status"].astype(str) + " " +
            df["installment_available"].astype(str) + " " +
            df["price"].astype(str)
        )

        return df

    def train_tfidf_model(self):
        os.makedirs(MODEL_DIR, exist_ok=True)

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=7000
        )

        self.product_matrix = self.vectorizer.fit_transform(
            self.products_df["ai_text"].tolist()
        )

        with open(TFIDF_MODEL_PATH, "wb") as file:
            pickle.dump(self.vectorizer, file)

        with open(TFIDF_MATRIX_PATH, "wb") as file:
            pickle.dump(self.product_matrix, file)

    def normalize_text(self, text):
        text = str(text).lower().strip()
        text = text.replace("ı", "i")
        text = text.replace("ğ", "g")
        text = text.replace("ü", "u")
        text = text.replace("ş", "s")
        text = text.replace("ö", "o")
        text = text.replace("ç", "c")
        return text

    def extract_budget(self, text):
        query = self.normalize_text(text)

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

    def extract_category(self, text):
        query = self.normalize_text(text)

        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if self.normalize_text(keyword) in query:
                    return category

        return None

    def extract_brands(self, text):
        query = self.normalize_text(text)
        found = []

        for alias, brand in BRAND_ALIASES.items():
            if self.normalize_text(alias) in query:
                if brand not in found:
                    found.append(brand)

        for brand in KNOWN_BRANDS:
            normalized_brand = self.normalize_text(brand)

            if normalized_brand in query:
                real_brand = "arçelik" if normalized_brand == "arcelik" else brand

                if real_brand not in found:
                    found.append(real_brand)

        return found

    def detect_intent(self, text):
        query = self.normalize_text(text)

        if any(x in query for x in ["tum urunler", "urunleri goster", "katalog", "urun listesi", "urunleri listele"]):
            return "show_all_products"

        if any(x in query for x in ["siparisim nerede", "kargom nerede", "siparis takip", "kargo nerede", "teslimat nerede"]):
            return "order_tracking"

        if any(x in query for x in ["siparis ver", "satin al", "alisverisi tamamla", "siparisi olustur"]):
            return "create_order"

        if any(x in query for x in ["iptal", "siparisi iptal", "iptal talebi"]):
            return "cancel_order"

        if any(x in query for x in ["iade", "iade baslat", "iade et", "iade talebi"]):
            return "return_order"

        if any(x in query for x in ["sepetim", "sepeti goster", "sepetimi goster", "sepette ne var"]):
            return "show_cart"

        if any(x in query for x in ["favorilerim", "favorilerimi goster", "favorimde ne var", "favori urunler"]):
            return "show_favorites"

        if any(x in query for x in ["karsilastir", "kiyasla", "hangisi", " vs ", " mi ", " mi?", " mu ", " mu?", " mu", " mu?", "mı", "mu", "mü"]):
            return "compare"

        if any(x in query for x in ["benzer", "alternatif", "buna benzer", "daha uygun alternatif"]):
            return "similar"

        if any(x in query for x in ["taksit", "pesin fiyatina", "6 taksit", "aylik odeme"]):
            return "installment_recommendation"

        if any(x in query for x in ["uygun fiyat", "ucuz", "ekonomik", "butce dostu", "daha ucuz"]):
            return "cheap_recommendation"

        if any(x in query for x in ["kampanya", "kupon", "indirim"]):
            return "campaign"

        if any(x in query for x in ["uyelik", "sifre", "hesabim", "giris yapamiyorum"]):
            return "membership"

        if any(x in query for x in ["sikayet", "kargo firmasi", "teslimat sorunu", "gecikti", "destek"]):
            return "support_ticket"

        return "product_recommendation"

    def understand_query(self, text):
        return {
            "original_query": text,
            "intent": self.detect_intent(text),
            "budget": self.extract_budget(text),
            "category": self.extract_category(text),
            "brands": self.extract_brands(text)
        }

    def calculate_installment(self, price, months=6):
        return round(float(price) / months, 2)

    def get_match_label(self, score):
        score = float(score)

        if score >= 0.75:
            return "Çok uygun"
        if score >= 0.50:
            return "Uygun"
        return "Alternatif"

    def split_comparison_terms(self, user_query):
        query = self.normalize_text(user_query)

        separators = [
            " mi ",
            " mu ",
            " mu?",
            " mi?",
            " vs ",
            " veya ",
            " ile ",
            " karsilastir",
            " kiyasla",
            " hangisi"
        ]

        cleaned = query

        for sep in separators:
            cleaned = cleaned.replace(sep, "|")

        terms = [
            item.strip()
            for item in cleaned.split("|")
            if item.strip()
        ]

        return terms

    def text_similarity(self, a, b):
        return difflib.SequenceMatcher(
            None,
            self.normalize_text(a),
            self.normalize_text(b)
        ).ratio()

    def find_best_product_for_term(self, term):
        term_norm = self.normalize_text(term)
        alias_brand = BRAND_ALIASES.get(term_norm, term_norm)

        best_score = 0
        best_row = None

        for _, row in self.products_df.iterrows():
            product_name = self.normalize_text(row.get("product_name", ""))
            brand = self.normalize_text(row.get("brand", ""))
            category = self.normalize_text(row.get("category", ""))
            description = self.normalize_text(row.get("description", ""))

            score = 0

            if term_norm == product_name:
                score += 120

            if term_norm in product_name:
                score += 90

            if product_name in term_norm:
                score += 70

            if alias_brand == brand:
                score += 80

            if term_norm == brand:
                score += 80

            if term_norm in brand:
                score += 60

            if term_norm in category:
                score += 35

            if term_norm in description:
                score += 25

            score += self.text_similarity(term_norm, product_name) * 45
            score += self.text_similarity(alias_brand, brand) * 40

            if score > best_score:
                best_score = score
                best_row = row

        if best_score < 35:
            return None

        return best_row

    def find_products_mentioned(self, user_query):
        terms = self.split_comparison_terms(user_query)
        matches = []

        for term in terms:
            product = self.find_best_product_for_term(term)

            if product is not None:
                product_id = str(product.get("product_id", ""))

                exists = any(
                    str(item.get("product_id", "")) == product_id
                    for item in matches
                )

                if not exists:
                    matches.append(product)

        if len(matches) == 0:
            query = self.normalize_text(user_query)

            for _, row in self.products_df.iterrows():
                product_name = self.normalize_text(row.get("product_name", ""))
                brand = self.normalize_text(row.get("brand", ""))

                if product_name in query or brand in query:
                    matches.append(row)

        return matches

    def apply_business_filters(self, query_info):
        df = self.products_df.copy()

        if query_info.get("category"):
            df = df[df["category"] == query_info["category"]]

        if query_info.get("budget"):
            df = df[df["price"] <= query_info["budget"]]

        if len(query_info.get("brands", [])) > 0:
            normalized_brands = [
                self.normalize_text(brand)
                for brand in query_info["brands"]
            ]

            brand_df = df[
                df["brand"].astype(str).apply(self.normalize_text).isin(normalized_brands)
            ]

            if not brand_df.empty:
                df = brand_df

        return df

    def score_products(self, user_query, candidate_df):
        if candidate_df.empty:
            return candidate_df

        candidate_indexes = candidate_df.index.tolist()
        query_vector = self.vectorizer.transform([user_query])

        similarities = cosine_similarity(
            query_vector,
            self.product_matrix[candidate_indexes]
        )[0]

        result_df = candidate_df.copy()
        result_df["nlp_similarity_score"] = similarities

        max_price = result_df["price"].max()
        min_price = result_df["price"].min()

        if max_price == min_price:
            result_df["price_score"] = 1
        else:
            result_df["price_score"] = 1 - (
                (result_df["price"] - min_price) / (max_price - min_price)
            )

        result_df["stock_score"] = result_df["stock_status"].astype(str).str.lower().apply(
            lambda value: 1 if value == "stokta" else 0
        )

        result_df["installment_score"] = result_df["installment_available"].astype(str).str.lower().apply(
            lambda value: 1 if value == "evet" else 0
        )

        result_df["final_score"] = (
            result_df["nlp_similarity_score"] * 0.55 +
            result_df["price_score"] * 0.25 +
            result_df["stock_score"] * 0.10 +
            result_df["installment_score"] * 0.10
        )

        result_df = result_df.sort_values("final_score", ascending=False)

        return result_df

    def create_reason(self, row, user_query):
        price = float(row.get("price", 0))
        monthly = self.calculate_installment(price, 6)

        return (
            f"Bu ürün aradığınız ihtiyaca ürün adı, kategori, marka ve açıklama açısından yakın olduğu için önerildi. "
            f"{row.get('category', '')} kategorisinde, {row.get('brand', '')} markasına ait. "
            f"Fiyatı {price:.0f} TL ve peşin fiyatına 6 taksit ile aylık yaklaşık {monthly:.0f} TL olarak değerlendirilebilir."
        )

    def product_to_json(self, row, user_query="", custom_reason=None):
        price = float(row.get("price", 0))
        final_score = float(row.get("final_score", row.get("nlp_similarity_score", 0.70)))

        return {
            "product_id": str(row.get("product_id", "")),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "price": price,
            "stock_status": row.get("stock_status", ""),
            "installment_available": row.get("installment_available", ""),
            "monthly_installment_6": self.calculate_installment(price, 6),
            "product_link": row.get("product_link", ""),
            "image_link": row.get("image_link", ""),
            "nlp_similarity_score": round(float(row.get("nlp_similarity_score", 0)), 4),
            "price_score": round(float(row.get("price_score", 0)), 4),
            "stock_score": round(float(row.get("stock_score", 0)), 4),
            "installment_score": round(float(row.get("installment_score", 0)), 4),
            "final_score": round(final_score, 4),
            "match_label": self.get_match_label(final_score),
            "reason": custom_reason or self.create_reason(row, user_query)
        }

    def recommend_products(self, user_query, top_n=6):
        query_info = self.understand_query(user_query)
        candidate_df = self.apply_business_filters(query_info)

        if candidate_df.empty:
            candidate_df = self.products_df.copy()

        scored_df = self.score_products(user_query, candidate_df).head(top_n)

        products = [
            self.product_to_json(row, user_query)
            for _, row in scored_df.iterrows()
        ]

        return products, query_info

    def show_all_products(self, top_n=30):
        display_df = self.products_df.sort_values(["category", "price"]).head(top_n)

        products = [
            self.product_to_json(
                row,
                "Tüm ürünleri göster",
                "Katalogdaki ürünlerden biri olarak listeleniyor."
            )
            for _, row in display_df.iterrows()
        ]

        return products

    def compare_products_from_query(self, user_query):
        matched_products = self.find_products_mentioned(user_query)

        if len(matched_products) < 2:
            products, query_info = self.recommend_products(user_query, top_n=6)

            return (
                products,
                "Karşılaştırmak istediğiniz iki ürünü tam net yakalayamadım. "
                "Yine de sorgunuza en yakın ürünleri listeledim. "
                "Örneğin 'Lenovo mu MacBook mu?' veya 'Samsung telefon ile iPhone karşılaştır' yazabilirsiniz."
            )

        product_1 = matched_products[0]
        product_2 = matched_products[1]

        return self.compare_two_products(product_1, product_2)

    def compare_two_products_by_id(self, product_id_1, product_id_2):
        row_1 = self.products_df[self.products_df["product_id"] == str(product_id_1)]
        row_2 = self.products_df[self.products_df["product_id"] == str(product_id_2)]

        if row_1.empty or row_2.empty:
            return [], "Karşılaştırılacak ürünlerden biri bulunamadı."

        return self.compare_two_products(row_1.iloc[0], row_2.iloc[0])

    def compare_two_products(self, product_1, product_2):
        price_1 = float(product_1.get("price", 0))
        price_2 = float(product_2.get("price", 0))

        monthly_1 = self.calculate_installment(price_1, 6)
        monthly_2 = self.calculate_installment(price_2, 6)

        if price_1 <= price_2:
            cheaper = product_1
            expensive = product_2
        else:
            cheaper = product_2
            expensive = product_1

        same_category = product_1.get("category", "") == product_2.get("category", "")

        if same_category:
            category_text = f"İki ürün de {product_1.get('category', '')} kategorisinde olduğu için doğrudan karşılaştırılabilir."
        else:
            category_text = "Ürünler farklı kategorilerde olduğu için karşılaştırma kullanım amacına göre değerlendirilmelidir."

        message = (
            f"{product_1.get('product_name', '')} ve {product_2.get('product_name', '')} karşılaştırıldı. "
            f"{category_text} "
            f"Fiyat açısından {cheaper.get('product_name', '')} daha avantajlıdır "
            f"({float(cheaper.get('price', 0)):.0f} TL). "
            f"{expensive.get('product_name', '')} daha yüksek fiyat segmentindedir "
            f"({float(expensive.get('price', 0)):.0f} TL). "
            f"Peşin fiyatına 6 taksit olarak {product_1.get('product_name', '')} aylık yaklaşık {monthly_1:.0f} TL, "
            f"{product_2.get('product_name', '')} aylık yaklaşık {monthly_2:.0f} TL olur."
        )

        reason_1 = (
            f"{product_1.get('product_name', '')}, fiyatı {price_1:.0f} TL olan "
            f"{product_1.get('brand', '')} marka bir üründür. 6 taksit tutarı yaklaşık {monthly_1:.0f} TL'dir."
        )

        reason_2 = (
            f"{product_2.get('product_name', '')}, fiyatı {price_2:.0f} TL olan "
            f"{product_2.get('brand', '')} marka bir üründür. 6 taksit tutarı yaklaşık {monthly_2:.0f} TL'dir."
        )

        products = [
            self.product_to_json(product_1, "karşılaştırma", reason_1),
            self.product_to_json(product_2, "karşılaştırma", reason_2)
        ]

        return products, message

    def similar_products_from_query(self, user_query, top_n=5):
        matched_products = self.find_products_mentioned(user_query)

        if len(matched_products) == 0:
            return [], "Benzer ürün önermek için ürün adını veya markayı daha net yazabilirsiniz."

        return self.similar_products_by_id(matched_products[0].get("product_id", ""), top_n)

    def similar_products_by_id(self, product_id, top_n=5):
        selected_df = self.products_df[self.products_df["product_id"] == str(product_id)]

        if selected_df.empty:
            return [], "Benzer ürün bulunamadı."

        selected_product = selected_df.iloc[0]

        candidates = self.products_df[
            (self.products_df["category"] == selected_product["category"]) &
            (self.products_df["product_id"] != selected_product["product_id"])
        ].copy()

        if candidates.empty:
            return [], "Bu ürünle aynı kategoride alternatif ürün bulunamadı."

        candidates["price_diff"] = abs(candidates["price"] - float(selected_product["price"]))
        candidates = candidates.sort_values("price_diff").head(top_n)

        products = []

        for _, row in candidates.iterrows():
            reason = (
                f"Bu ürün, {selected_product.get('product_name', '')} ile aynı kategoride olduğu "
                f"ve fiyat olarak alternatif konumda bulunduğu için önerildi."
            )
            products.append(self.product_to_json(row, "benzer ürün", reason))

        message = f"{selected_product.get('product_name', '')} ürününe benzer alternatifleri listeledim."

        return products, message

    def llm_response(self, user_query, assistant_message, products, query_info):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return assistant_message

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""
            Sen Nevade.com için çalışan profesyonel bir e-ticaret alışveriş asistanısın.

            Kullanıcı mesajı:
            {user_query}

            Sistem intent analizi:
            {json.dumps(query_info, ensure_ascii=False)}

            Sistem cevabı:
            {assistant_message}

            Ürünler:
            {json.dumps(products[:4], ensure_ascii=False)}

            Görev:
            Kullanıcıya kısa, net, Türkçe ve müşteri hizmetleri diliyle cevap ver.
            Ürün önerisi varsa fiyat, taksit, stok ve neden önerildi bilgisini doğal anlat.
            Sipariş, kargo, iade veya iptal ise işlem durumunu net söyle.
            Abartılı satış dili kullanma.
            """

            response = model.generate_content(prompt)

            if response and response.text:
                return response.text.strip()

            return assistant_message

        except Exception:
            return assistant_message