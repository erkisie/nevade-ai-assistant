import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_products(file_path="data/products.csv"):
    if isinstance(file_path, str):
        if file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    else:
        file_name = file_path.name

        if file_name.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

    df = df.fillna("")

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

    df["search_text"] = (
        df["product_name"].astype(str) + " " +
        df["category"].astype(str) + " " +
        df["brand"].astype(str) + " " +
        df["description"].astype(str)
    )

    return df

def recommend_products(user_query, df, top_n=5):
    vectorizer = TfidfVectorizer(lowercase=True)

    all_texts = df["search_text"].tolist() + [user_query]
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    product_vectors = tfidf_matrix[:-1]
    query_vector = tfidf_matrix[-1]

    similarities = cosine_similarity(query_vector, product_vectors).flatten()

    result_df = df.copy()
    result_df["similarity_score"] = similarities

    result_df = result_df.sort_values(
        by="similarity_score",
        ascending=False
    ).head(top_n)

    return result_df


def generate_reason(row):
    reasons = []

    if str(row["stock_status"]).lower() == "stokta":
        reasons.append("stokta olduğu")

    if str(row["installment_available"]).lower() == "evet":
        reasons.append("taksitli alışverişe uygun olduğu")

    if row["similarity_score"] > 0:
        reasons.append("arama ihtiyacınıza benzer olduğu")

    if str(row["price"]) != "":
        reasons.append(f"fiyatı {row['price']} TL olduğu")

    if len(reasons) == 0:
        return "Bu ürün arama kriterlerinize yakın olduğu için önerildi."

    return "Bu ürün " + ", ".join(reasons) + " için önerildi."

def recommend_similar_products(product_id, df, top_n=3):
    selected_product = df[df["product_id"].astype(str) == str(product_id)]

    if selected_product.empty:
        return None

    selected_row = selected_product.iloc[0]

    selected_category = selected_row["category"]
    selected_price = float(selected_row["price"])

    candidate_df = df[
        (df["category"] == selected_category) &
        (df["product_id"].astype(str) != str(product_id))
    ].copy()

    if candidate_df.empty:
        return None

    candidate_df["price"] = candidate_df["price"].astype(float)

    candidate_df["price_difference"] = abs(
        candidate_df["price"] - selected_price
    )

    max_price_difference = candidate_df["price_difference"].max()

    if max_price_difference == 0:
        candidate_df["price_score"] = 1
    else:
        candidate_df["price_score"] = 1 - (
            candidate_df["price_difference"] / max_price_difference
        )

    candidate_df["brand_score"] = candidate_df["brand"].apply(
        lambda brand: 1 if brand == selected_row["brand"] else 0
    )

    candidate_df["similarity_score"] = (
        candidate_df["price_score"] * 0.7 +
        candidate_df["brand_score"] * 0.3
    )

    candidate_df = candidate_df.sort_values(
        by="similarity_score",
        ascending=False
    ).head(top_n)

    return candidate_df