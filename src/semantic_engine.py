from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class SemanticProductSearch:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

    def prepare_product_text(self, df):
        df = df.copy()

        for col in [
            "product_name",
            "category",
            "brand",
            "description",
            "stock_status",
            "installment_available",
            "price"
        ]:
            if col not in df.columns:
                df[col] = ""

        df["semantic_text"] = (
            "Ürün adı: " + df["product_name"].astype(str) + ". " +
            "Kategori: " + df["category"].astype(str) + ". " +
            "Marka: " + df["brand"].astype(str) + ". " +
            "Fiyat: " + df["price"].astype(str) + " TL. " +
            "Açıklama: " + df["description"].astype(str) + ". " +
            "Stok durumu: " + df["stock_status"].astype(str) + ". " +
            "Taksit uygunluğu: " + df["installment_available"].astype(str) + "."
        )

        return df

    def calculate_business_scores(self, df):
        df = df.copy()

        df["price"] = df["price"].astype(float)

        max_price = df["price"].max()
        min_price = df["price"].min()

        if max_price == min_price:
            df["price_score"] = 1
        else:
            df["price_score"] = 1 - (
                (df["price"] - min_price) / (max_price - min_price)
            )

        df["stock_score"] = df["stock_status"].astype(str).str.lower().apply(
            lambda value: 1 if value == "stokta" else 0
        )

        df["installment_score"] = df["installment_available"].astype(str).str.lower().apply(
            lambda value: 1 if value == "evet" else 0
        )

        return df

    def recommend(self, user_query, df, top_n=5):
        df = self.prepare_product_text(df)
        df = self.calculate_business_scores(df)

        product_texts = df["semantic_text"].tolist()

        product_embeddings = self.model.encode(
            product_texts,
            convert_to_tensor=True,
            normalize_embeddings=True
        )

        query_embedding = self.model.encode(
            user_query,
            convert_to_tensor=True,
            normalize_embeddings=True
        )

        similarity_scores = util.cos_sim(
            query_embedding,
            product_embeddings
        )[0]

        df_result = df.copy()
        df_result["semantic_score"] = similarity_scores.cpu().numpy()

        df_result["final_score"] = (
            df_result["semantic_score"] * 0.70 +
            df_result["price_score"] * 0.15 +
            df_result["stock_score"] * 0.10 +
            df_result["installment_score"] * 0.05
        )

        df_result = df_result.sort_values(
            by="final_score",
            ascending=False
        ).head(top_n)

        return df_result