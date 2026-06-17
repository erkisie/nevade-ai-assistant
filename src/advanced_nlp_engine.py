import difflib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils import normalize_text, safe_number, money
from src.nlp_engine import NLPQueryEngine, PRODUCT_TYPE_KEYWORDS
from src.decision_engine import DecisionEngine


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


class AdvancedNevadeNLPEngine:
    def __init__(self, products_df):
        self.nlp = NLPQueryEngine()
        self.decision = DecisionEngine()

        self.products_df = self.prepare_products(products_df)

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=15000
        )

        self.product_matrix = self.vectorizer.fit_transform(
            self.products_df["model_text"].tolist()
        )

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

    def understand_query(self, user_query):
        return self.nlp.understand(user_query)

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

    def filter_candidates(self, query_info):
        df = self.products_df.copy()

        if query_info.get("category"):
            category_df = df[df["category"] == query_info["category"]]
            if not category_df.empty:
                df = category_df

        product_type = query_info.get("product_type")

        if product_type:
            keywords = PRODUCT_TYPE_KEYWORDS.get(product_type, [])
            mask = None

            for keyword in keywords:
                keyword_norm = normalize_text(keyword)
                current_mask = (
                    df["normalized_name"].str.contains(keyword_norm, na=False) |
                    df["model_text"].str.contains(keyword_norm, na=False)
                )

                if mask is None:
                    mask = current_mask
                else:
                    mask = mask | current_mask

            if mask is not None:
                type_df = df[mask]
                if not type_df.empty:
                    df = type_df

        if query_info.get("brands"):
            brand_df = df[df["normalized_brand"].isin(query_info["brands"])]
            if not brand_df.empty:
                df = brand_df

        if query_info.get("budget"):
            budget = float(query_info["budget"])
            under_budget = df[df["price"] <= budget]

            if not under_budget.empty:
                df = under_budget
            else:
                df = df.copy()
                df["budget_distance"] = abs(df["price"] - budget)
                df = df.sort_values("budget_distance").head(8)

        if df.empty:
            df = self.products_df.copy()

        return df

    def payment_specific_score(self, row, query_info):
        preference = query_info.get("payment_preference")

        if preference == "senet":
            value = safe_number(row.get("senet_total_price", 0))
            if value <= 0:
                return 0.0
            return value

        if preference == "bank_transfer":
            value = safe_number(row.get("bank_transfer_price", 0))
            if value <= 0:
                return safe_number(row.get("price", 0))
            return value

        if preference == "cash":
            value = safe_number(row.get("cash_price", 0))
            if value <= 0:
                return safe_number(row.get("price", 0))
            return value

        return safe_number(row.get("price", 0))

    def score_candidates(self, user_query, candidate_df):
        if candidate_df.empty:
            return candidate_df

        query_info = self.understand_query(user_query)
        priority = query_info.get("priority")
        payment_preference = query_info.get("payment_preference")

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

        result["payment_score"] = result.apply(
            lambda row: self.decision.payment_score(row, query_info),
            axis=1
        )

        result["feature_score"] = result.apply(
            lambda row: self.decision.feature_score(row, priority),
            axis=1
        )

        if payment_preference:
            result["selected_payment_price"] = result.apply(
                lambda row: self.payment_specific_score(row, query_info),
                axis=1
            )

            min_payment = result["selected_payment_price"].min()
            max_payment = result["selected_payment_price"].max()

            if min_payment == max_payment:
                result["selected_payment_score"] = 1
            else:
                result["selected_payment_score"] = 1 - (
                    (result["selected_payment_price"] - min_payment) / (max_payment - min_payment)
                )

            result["final_score"] = (
                result["selected_payment_score"] * 0.45 +
                result["payment_score"] * 0.25 +
                result["price_score"] * 0.15 +
                result["nlp_score"] * 0.10 +
                result["stock_score"] * 0.05
            )

            return result.sort_values("final_score", ascending=False)

        if priority in ["capacity", "energy", "performance", "usage"]:
            result["final_score"] = (
                result["feature_score"] * 0.40 +
                result["nlp_score"] * 0.25 +
                result["price_score"] * 0.20 +
                result["payment_score"] * 0.10 +
                result["stock_score"] * 0.05
            )

        elif priority == "price":
            result["final_score"] = (
                result["price_score"] * 0.45 +
                result["nlp_score"] * 0.25 +
                result["payment_score"] * 0.15 +
                result["stock_score"] * 0.10 +
                result["feature_score"] * 0.05
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

    def product_to_json(self, row, reason, score=0.70):
        price = safe_number(row.get("price", 0))
        payment_analysis = self.decision.payment_analysis(row)

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
            "payment_analysis": payment_analysis,
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

    def create_reason(self, row, query_info):
        price = safe_number(row.get("price", 0))
        payment = self.decision.payment_analysis(row)

        parts = []

        parts.append(
            "Bu ürün, yazdığınız ihtiyaca göre ürün tipi, kategori, açıklama, fiyat, ödeme seçeneği ve stok durumu birlikte değerlendirilerek önerildi."
        )

        if query_info.get("product_type"):
            parts.append("Aradığınız ürün tipiyle eşleştiği için listeye alındı.")

        if query_info.get("budget"):
            budget = float(query_info["budget"])
            if price <= budget:
                parts.append(f"{money(budget)} bütçenizin altında kalıyor.")
            else:
                parts.append(f"{money(budget)} bütçenize en yakın alternatiflerden biri.")

        if query_info.get("payment_preference") == "senet":
            parts.append(
                f"Senetli ödeme açısından değerlendirildi. Senetli toplam fiyatı {money(row.get('senet_total_price', 0))}."
            )

        if query_info.get("payment_preference") == "bank_transfer":
            parts.append(
                f"Havale fiyatı {money(row.get('bank_transfer_price', 0))} olarak dikkate alındı."
            )

        parts.append(
            f"Liste fiyatı {money(price)}."
        )

        if row.get("capacity", ""):
            parts.append(f"Kapasite: {row.get('capacity')}.")

        if row.get("energy_class", ""):
            parts.append(f"Enerji sınıfı: {row.get('energy_class')}.")

        if row.get("ram", ""):
            parts.append(f"RAM: {row.get('ram')}.")

        if row.get("storage", ""):
            parts.append(f"Depolama: {row.get('storage')}.")

        parts.append(payment["advice"])

        return " ".join(parts)

    def recommend(self, user_query, top_n=6):
        query_info = self.understand_query(user_query)
        candidates = self.filter_candidates(query_info)
        scored = self.score_candidates(user_query, candidates).head(top_n)

        products = []

        for _, row in scored.iterrows():
            score = float(row.get("final_score", 0.70))
            reason = self.create_reason(row, query_info)

            products.append(
                self.product_to_json(row, reason, score)
            )

        return products, query_info

    def recommend_student_laptops(self, user_query):
        query_info = self.understand_query(user_query)
        query_info["category"] = "Bilgisayar"
        query_info["product_type"] = "laptop"

        candidates = self.filter_candidates(query_info)

        scored = self.score_candidates(
            "ogrenci icin uygun fiyatli laptop okul ders hafif tasinabilir",
            candidates
        ).head(4)

        products = []

        for _, row in scored.iterrows():
            reason = self.create_reason(row, query_info)
            products.append(
                self.product_to_json(row, reason, float(row.get("final_score", 0.80)))
            )

        message = (
            "Öğrenci kullanımı için uygun laptopları fiyat, taksit, taşınabilirlik, RAM, depolama ve kullanım amacı açısından listeledim."
        )

        return products, message

    def recommend_ceyiz_bundle(self, user_query):
        query_info = self.understand_query(user_query)
        budget = query_info.get("budget") or 50000

        df = self.products_df[
            self.products_df["category"].isin(["Beyaz Eşya", "Ev Elektroniği", "Televizyon"])
        ].copy()

        df = df.sort_values("price")

        selected = []
        used_types = set()
        total = 0

        target_types = [
            ("buzdolabi", ["buzdolabi"]),
            ("camasir_makinesi", ["camasir"]),
            ("supurge", ["supurge"]),
            ("televizyon", ["televizyon", "tv"])
        ]

        for type_name, keywords in target_types:
            type_rows = df[
                df["model_text"].apply(lambda text: any(keyword in text for keyword in keywords))
            ].sort_values("price")

            for _, row in type_rows.iterrows():
                price = safe_number(row.get("price", 0))

                if total + price <= budget and type_name not in used_types:
                    selected.append(row)
                    total += price
                    used_types.add(type_name)
                    break

        products = []

        for row in selected:
            reason = self.create_reason(row, query_info)
            products.append(self.product_to_json(row, reason, 0.82))

        message = (
            f"{money(budget)} bütçeye göre çeyiz alışverişi için temel ürünleri listeledim. "
            f"Seçilen ürünlerin toplamı yaklaşık {money(total)}."
        )

        return products, message

    def similarity_ratio(self, a, b):
        return difflib.SequenceMatcher(
            None,
            normalize_text(a),
            normalize_text(b)
        ).ratio()

    def find_products_in_text(self, user_query):
        query = normalize_text(user_query)
        found = []

        for _, row in self.products_df.iterrows():
            name = normalize_text(row.get("product_name", ""))
            brand = normalize_text(row.get("brand", ""))

            if name in query or self.similarity_ratio(query, name) > 0.55:
                found.append(row)

            elif brand in query and len(brand) > 2:
                found.append(row)

        unique = []
        used_ids = set()

        for row in found:
            product_id = str(row.get("product_id", ""))

            if product_id not in used_ids:
                unique.append(row)
                used_ids.add(product_id)

        return unique

    def compare(self, user_query):
        found = self.find_products_in_text(user_query)
        query_info = self.understand_query(user_query)

        if len(found) < 2:
            products, _ = self.recommend(user_query, top_n=4)

            return (
                products,
                "Karşılaştırmak istediğiniz iki ürünü tam net yakalayamadım. Yine de sorgunuza en yakın ürünleri listeledim."
            )

        return self.compare_rows(found[0], found[1], query_info)

    def compare_rows(self, row1, row2, query_info):
        winner, decision_reason = self.decision.compare_rows(row1, row2, query_info)

        price1 = safe_number(row1.get("price", 0))
        price2 = safe_number(row2.get("price", 0))

        monthly1 = self.calculate_installment(price1, 6)
        monthly2 = self.calculate_installment(price2, 6)

        message = (
            f"{row1['product_name']} ve {row2['product_name']} karşılaştırıldı. "
            f"{decision_reason} "
            f"Standart 6 taksit hesabında {row1['product_name']} aylık yaklaşık {monthly1:.0f} TL, "
            f"{row2['product_name']} aylık yaklaşık {monthly2:.0f} TL olur."
        )

        products = []

        for row in [row1, row2]:
            is_winner = str(row.get("product_id", "")) == str(winner.get("product_id", ""))
            score = 0.92 if is_winner else 0.58

            if is_winner:
                label_reason = "Bu ürün seçtiğiniz kritere göre daha avantajlı olduğu için öne çıkarıldı."
            else:
                label_reason = "Bu ürün alternatif olarak değerlendirildi; seçtiğiniz kritere göre diğer ürün daha avantajlı görünüyor."

            reason = f"{label_reason} {self.create_reason(row, query_info)}"
            product = self.product_to_json(row, reason, score)
            product["match_label"] = "Daha avantajlı" if is_winner else "Alternatif"

            products.append(product)

        return products, message