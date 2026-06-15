import json


def create_api_output(recommendation_df, reason_function):
    api_results = []

    for _, row in recommendation_df.iterrows():
        score = row.get(
            "final_score",
            row.get("semantic_score", row.get("similarity_score", 0))
        )

        api_results.append({
            "product_id": int(row.get("product_id", 0)),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "price": float(row.get("price", 0)),
            "score": round(float(score), 4),
            "semantic_score": round(float(row.get("semantic_score", 0)), 4),
            "price_score": round(float(row.get("price_score", 0)), 4),
            "stock_score": round(float(row.get("stock_score", 0)), 4),
            "installment_score": round(float(row.get("installment_score", 0)), 4),
            "recommendation_type": "nlp_llm_ai_recommendation",
            "reason": reason_function(row)
        })

    return api_results


def convert_to_json(api_results):
    return json.dumps(
        api_results,
        ensure_ascii=False,
        indent=4
    )