from src.utils import safe_number, money, normalize_text


class BehaviorEngine:
    def __init__(self, products_df, recommender_engine):
        self.products_df = products_df.copy()
        self.engine = recommender_engine

    def get_product_row(self, product_id):
        product_id = str(product_id)

        df = self.products_df[
            self.products_df["product_id"].astype(str) == product_id
        ]

        if df.empty:
            return None

        return df.iloc[0]

    def product_type_keywords(self, row):
        text = normalize_text(
            f"{row.get('product_name', '')} "
            f"{row.get('description', '')} "
            f"{row.get('features', '')}"
        )

        if "buzdolabi" in text or "buzdolabı" in text:
            return ["buzdolabi", "buzdolabı", "dolap"]

        if "camasir" in text or "çamaşır" in text:
            return ["camasir", "çamaşır", "camasir makinesi", "çamaşır makinesi"]

        if "laptop" in text or "bilgisayar" in text or "notebook" in text:
            return ["laptop", "bilgisayar", "notebook", "macbook"]

        if "telefon" in text or "iphone" in text or "galaxy" in text:
            return ["telefon", "iphone", "galaxy", "redmi"]

        if "supurge" in text or "süpürge" in text:
            return ["supurge", "süpürge", "dyson"]

        if "televizyon" in text or "tv" in text:
            return ["televizyon", "tv", "oled", "4k"]

        if "airfryer" in text:
            return ["airfryer"]

        if "kahve" in text:
            return ["kahve"]

        return []

    def same_product_type_filter(self, df, selected_row):
        keywords = self.product_type_keywords(selected_row)

        if not keywords:
            return df

        mask = None

        for keyword in keywords:
            keyword_norm = normalize_text(keyword)

            current_mask = df["model_text"].astype(str).apply(
                lambda value: keyword_norm in normalize_text(value)
            )

            if mask is None:
                mask = current_mask
            else:
                mask = mask | current_mask

        filtered = df[mask]

        if filtered.empty:
            return df

        return filtered

    def cheaper_alternatives(self, product_id, limit=3):
        selected = self.get_product_row(product_id)

        if selected is None:
            return [], "Seçili ürünü ürün listesinde bulamadım."

        selected_price = safe_number(selected.get("price", 0))
        selected_category = selected.get("category", "")

        candidates = self.products_df[
            (self.products_df["category"] == selected_category) &
            (self.products_df["product_id"].astype(str) != str(product_id)) &
            (self.products_df["stock_status"].astype(str).str.lower() == "stokta")
        ].copy()

        candidates = self.same_product_type_filter(candidates, selected)

        candidates = candidates[
            candidates["price"].apply(safe_number) < selected_price
        ].copy()

        if candidates.empty:
            products, message = self.similar_alternatives(product_id, limit=limit)
            if products:
                return products, (
                    f"{selected['product_name']} ürününden daha ucuz aynı tip alternatif bulamadım. "
                    "Bunun yerine benzer alternatifleri listeledim."
                )
            return [], f"{selected['product_name']} için uygun alternatif bulunamadı."

        candidates["price_value"] = candidates["price"].apply(safe_number)
        candidates["price_difference"] = selected_price - candidates["price_value"]
        candidates = candidates.sort_values("price_value", ascending=True).head(limit)

        products = []

        for _, row in candidates.iterrows():
            diff = selected_price - safe_number(row.get("price", 0))

            reason = (
                f"{selected['product_name']} ürününe göre daha uygun fiyatlı bir alternatiftir. "
                f"Seçili ürün fiyatı {money(selected_price)}, bu ürünün fiyatı {money(row.get('price', 0))}. "
                f"Yaklaşık {money(diff)} daha ekonomiktir. Aynı kategori ve benzer ürün tipi içinde değerlendirilmiştir."
            )

            products.append(
                self.engine.product_to_json(row, reason, 0.82)
            )

        message = (
            f"{selected['product_name']} sepetinizde kaldığı için aynı ürün tipinde daha uygun fiyatlı alternatifleri listeledim."
        )

        return products, message

    def similar_alternatives(self, product_id, limit=3):
        selected = self.get_product_row(product_id)

        if selected is None:
            return [], "Seçili ürünü ürün listesinde bulamadım."

        query = (
            f"{selected.get('product_name', '')} "
            f"{selected.get('category', '')} "
            f"{selected.get('brand', '')} "
            f"{selected.get('description', '')} "
            f"{selected.get('features', '')} "
            f"{selected.get('use_case', '')}"
        )

        products, query_info = self.engine.recommend(query, top_n=limit + 4)

        clean_products = []

        for product in products:
            if str(product.get("product_id")) != str(product_id):
                product["reason"] = (
                    f"{selected['product_name']} ürününe benzer olduğu için önerildi. "
                    f"Kategori, kullanım amacı, açıklama, fiyat aralığı ve ödeme seçenekleri birlikte değerlendirildi. "
                    + product.get("reason", "")
                )
                clean_products.append(product)

            if len(clean_products) >= limit:
                break

        if not clean_products:
            return [], f"{selected['product_name']} için benzer ürün bulunamadı."

        message = (
            f"{selected['product_name']} ürününe benzer alternatifleri kategori, açıklama, fiyat, kullanım amacı ve ödeme seçeneklerine göre listeledim."
        )

        return clean_products, message

    def favorite_followup_suggestion(self, favorite_product_ids):
        if not favorite_product_ids:
            return [], "Favorileriniz boş olduğu için öneri oluşturamadım."

        # En son favoriye eklenen ürün üzerinden öneri yapıyoruz.
        product_id = favorite_product_ids[-1]

        products, message = self.similar_alternatives(product_id, limit=3)

        if products:
            message = (
                "Favoriye eklediğiniz ürüne göre benzer alternatifleri hazırladım. "
                + message
            )

        return products, message

    def cart_abandonment_suggestion(self, cart_product_ids):
        if not cart_product_ids:
            return [], "Sepetiniz boş olduğu için öneri oluşturamadım."

        # En son sepete eklenen ürün üzerinden daha uygun alternatif arıyoruz.
        product_id = cart_product_ids[-1]

        products, message = self.cheaper_alternatives(product_id, limit=3)

        if products:
            message = (
                "Sepette bırakılan ürüne göre daha uygun fiyatlı alternatifleri hazırladım. "
                + message
            )

        return products, message