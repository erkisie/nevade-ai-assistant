from src.query_understanding import understand_query


def apply_query_filters(df, query_info):
    filtered_df = df.copy()

    category = query_info.get("category")
    budget = query_info.get("budget")
    brands = query_info.get("brands", [])
    wants_installment = query_info.get("wants_installment")
    wants_in_stock = query_info.get("wants_in_stock")

    if category:
        filtered_df = filtered_df[
            filtered_df["category"].astype(str).str.lower()
            == category.lower()
        ]

    if budget:
        filtered_df = filtered_df[
            filtered_df["price"].astype(float) <= float(budget)
        ]

    if wants_installment:
        filtered_df = filtered_df[
            filtered_df["installment_available"].astype(str).str.lower()
            == "evet"
        ]

    if wants_in_stock:
        filtered_df = filtered_df[
            filtered_df["stock_status"].astype(str).str.lower()
            == "stokta"
        ]

    if len(brands) > 0:
        brand_filtered = filtered_df[
            filtered_df["brand"].astype(str).str.lower().isin(brands)
        ]

        if not brand_filtered.empty:
            filtered_df = brand_filtered

    return filtered_df


def safe_generate_reason(row, user_query):
    try:
        from src.llm_assistant import generate_llm_reason

        return generate_llm_reason(row, user_query)

    except Exception:
        return (
            f"Bu ürün, arama ihtiyacınızla ilişkili olduğu için önerildi. "
            f"{row.get('category', '')} kategorisinde yer alır, "
            f"{row.get('brand', '')} markasına aittir ve "
            f"{row.get('price', '')} TL fiyatıyla değerlendirilebilir."
        )


def compare_products(user_query, df, query_info):
    brands = query_info.get("brands", [])

    if len(brands) == 0:
        return {
            "response_type": "comparison",
            "query_understanding": query_info,
            "assistant_message": (
                "Karşılaştırma yapmak istediğinizi anladım ancak katalogda "
                "karşılaştırılacak marka veya ürünleri net bulamadım."
            ),
            "products": []
        }

    comparison_products = df[
        df["brand"].astype(str).str.lower().isin(brands)
    ].copy()

    if comparison_products.empty:
        return {
            "response_type": "comparison",
            "query_understanding": query_info,
            "assistant_message": (
                "Karşılaştırmak istediğiniz ürünler mevcut ürün kataloğunda bulunamadı."
            ),
            "products": []
        }

    comparison_products["price"] = comparison_products["price"].astype(float)
    comparison_products = comparison_products.sort_values(
        by="price",
        ascending=True
    )

    products_json = []

    for _, row in comparison_products.iterrows():
        products_json.append({
            "product_id": str(row.get("product_id", "")),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "price": float(row.get("price", 0)),
            "stock_status": row.get("stock_status", ""),
            "installment_available": row.get("installment_available", ""),
            "product_link": row.get("product_link", ""),
            "image_link": row.get("image_link", ""),
            "reason": safe_generate_reason(row, user_query)
        })

    cheapest = comparison_products.iloc[0]
    most_expensive = comparison_products.iloc[-1]

    assistant_message = (
        f"Karşılaştırma sonucunda {cheapest.get('product_name', '')} fiyat açısından "
        f"daha avantajlı görünüyor ({float(cheapest.get('price', 0)):.0f} TL). "
        f"{most_expensive.get('product_name', '')} ise daha yüksek fiyat segmentinde yer alıyor. "
        f"Bütçe ve fiyat/performans önceliğiniz varsa daha uygun fiyatlı ürün; "
        f"premium marka veya üst segment önceliğiniz varsa daha yüksek fiyatlı ürün değerlendirilebilir."
    )

    return {
        "response_type": "comparison",
        "query_understanding": query_info,
        "assistant_message": assistant_message,
        "products": products_json
    }


def build_recommendation_json(results_df, user_query):
    products = []

    for _, row in results_df.iterrows():
        final_score = row.get(
            "final_score",
            row.get("semantic_score", row.get("similarity_score", 0))
        )

        products.append({
            "product_id": str(row.get("product_id", "")),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "price": float(row.get("price", 0)),
            "stock_status": row.get("stock_status", ""),
            "installment_available": row.get("installment_available", ""),
            "product_link": row.get("product_link", ""),
            "image_link": row.get("image_link", ""),
            "final_score": round(float(final_score), 4),
            "semantic_score": round(float(row.get("semantic_score", 0)), 4),
            "price_score": round(float(row.get("price_score", 0)), 4),
            "stock_score": round(float(row.get("stock_score", 0)), 4),
            "installment_score": round(float(row.get("installment_score", 0)), 4),
            "reason": safe_generate_reason(row, user_query)
        })

    return products


def get_ai_recommendation_response(user_query, df, semantic_engine, top_n=5):
    query_info = understand_query(user_query)

    if query_info.get("intent") == "comparison" or query_info.get("is_comparison"):
        return compare_products(user_query, df, query_info)

    filtered_df = apply_query_filters(df, query_info)

    if filtered_df.empty:
        filtered_df = df.copy()

    results_df = semantic_engine.recommend(
        user_query,
        filtered_df,
        top_n
    )

    products = build_recommendation_json(results_df, user_query)

    if len(products) == 0:
        assistant_message = (
            "Bu ihtiyaca uygun ürün bulunamadı. Farklı bir arama ifadesi deneyebilirsiniz."
        )
    else:
        top_product = products[0]

        assistant_message = (
            f"İhtiyacınıza en uygun ürün {top_product['product_name']} olarak görünüyor. "
            f"Bu ürün {top_product['category']} kategorisinde, {top_product['brand']} markasına ait "
            f"ve {top_product['price']:.0f} TL fiyatıyla listeleniyor. "
            f"Peşin fiyatına 6 taksit seçeneğiyle aylık yaklaşık "
            f"{top_product['price'] / 6:.0f} TL olarak değerlendirilebilir."
        )

    return {
        "response_type": "recommendation",
        "query_understanding": query_info,
        "assistant_message": assistant_message,
        "products": products
    }