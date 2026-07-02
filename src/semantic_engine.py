import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


# =====================================================
# SEMANTIC ENGINE
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


def safe_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def safe_number(value):
    try:
        if value is None or pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).replace("TL", "").replace("₺", "").replace("tl", "").strip()

        if text == "":
            return 0.0

        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        elif text.count(".") == 1:
            left, right = text.split(".")
            if len(right) == 3:
                text = text.replace(".", "")

        return float(text)

    except Exception:
        return 0.0


def build_product_semantic_text(row):
    """
    Ürün hakkında anlam çıkarılacak metni oluşturur.
    Kullanıcı mesajı bu metinlerle anlamsal olarak kıyaslanır.
    """

    fields = [
        "product_name",
        "category",
        "brand",
        "product_type",
        "description",
        "features",
        "use_case",
        "payment_options",
        "processor",
        "ram",
        "storage",
        "capacity",
        "energy_class",
        "screen_size",
        "warranty",
    ]

    parts = []

    for field in fields:
        if field in row:
            value = safe_text(row.get(field, ""))

            if value:
                parts.append(value)

    return " ".join(parts)


def add_semantic_scores(products_df, user_query):
    """
    Ürünlere semantic_score ekler.
    Model çalışmazsa sistem bozulmaz, skor 0 döner.
    """

    if products_df is None or products_df.empty:
        return products_df

    scored_df = products_df.copy()

    model = get_model()

    if model is None:
        scored_df["semantic_score"] = 0
        return scored_df

    product_texts = []

    for _, row in scored_df.iterrows():
        product_texts.append(build_product_semantic_text(row))

    try:
        product_embeddings = model.encode(product_texts, convert_to_numpy=True)
        query_embedding = model.encode([user_query], convert_to_numpy=True)

        similarities = cosine_similarity(product_embeddings, query_embedding).flatten()

        scored_df["semantic_score"] = [
            round(float(score) * 100, 2)
            for score in similarities
        ]

    except Exception as e:
        print("Semantic scoring error:", e)
        scored_df["semantic_score"] = 0

    return scored_df


def apply_semantic_reranking(result_df, user_query):
    """
    Decision Engine güvenli ürünleri seçtikten sonra,
    bu ürünleri semantic_score ile yeniden sıralar.
    """

    if result_df is None or result_df.empty:
        return result_df

    scored_df = add_semantic_scores(result_df, user_query)

    if "score" not in scored_df.columns:
        scored_df["score"] = 0

    scored_df["final_ai_score"] = (
        scored_df["score"].apply(safe_number) * 0.60
        + scored_df["semantic_score"].apply(safe_number) * 0.40
    )

    scored_df = scored_df.sort_values(
        ["final_ai_score", "price"],
        ascending=[False, True],
    )

    return scored_df