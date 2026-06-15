import os
from dotenv import load_dotenv

load_dotenv()


def generate_fallback_reason(row, user_query):
    reasons = []

    if str(row.get("stock_status", "")).lower() == "stokta":
        reasons.append("stokta olması")

    if str(row.get("installment_available", "")).lower() == "evet":
        reasons.append("taksitli alışverişe uygun olması")

    if float(row.get("semantic_score", 0)) > 0:
        reasons.append("kullanıcının ihtiyacıyla anlamsal olarak benzer özellikler taşıması")

    if len(reasons) == 0:
        reasons.append("ürün bilgilerinin arama ifadesiyle ilişkili olması")

    return (
        f"Bu ürün, {', '.join(reasons)} nedeniyle önerildi. "
        f"{row.get('category', '')} kategorisinde yer alır, "
        f"{row.get('brand', '')} markasına aittir ve "
        f"'{user_query}' ihtiyacına uygun bir seçenek olarak değerlendirilebilir."
    )


def generate_llm_reason(row, user_query):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return generate_fallback_reason(row, user_query)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Sen Nevade.com için çalışan profesyonel bir e-ticaret ürün öneri asistanısın.

        Kullanıcının ihtiyacı:
        {user_query}

        Önerilen ürün bilgileri:
        Ürün adı: {row.get("product_name", "")}
        Kategori: {row.get("category", "")}
        Marka: {row.get("brand", "")}
        Fiyat: {row.get("price", "")} TL
        Açıklama: {row.get("description", "")}
        Stok durumu: {row.get("stock_status", "")}
        Taksit uygunluğu: {row.get("installment_available", "")}
        Benzerlik skoru: {row.get("semantic_score", "")}

        Görev:
        Bu ürünün kullanıcıya neden önerildiğini 2 kısa cümleyle açıkla.
        Satış dili kullan ama abartma.
        Türkçe yaz.
        """

        response = model.generate_content(prompt)

        if response and response.text:
            return response.text.strip()

        return generate_fallback_reason(row, user_query)

    except Exception:
        return generate_fallback_reason(row, user_query)


def is_comparison_question(user_query):
    query = user_query.lower()

    comparison_keywords = [
        " mı ",
        " mi ",
        " mu ",
        " mü ",
        "hangisi",
        "karşılaştır",
        "kıyasla",
        "farkı ne",
        "daha iyi",
        "sence"
    ]

    return any(keyword in query for keyword in comparison_keywords)


def find_products_in_query(user_query, full_df):
    query = user_query.lower()
    matched_products = []

    for _, row in full_df.iterrows():
        product_name = str(row.get("product_name", "")).lower()
        brand = str(row.get("brand", "")).lower()

        if brand and brand in query:
            matched_products.append(row)

        elif product_name and product_name in query:
            matched_products.append(row)

    return matched_products


def generate_comparison_response(user_query, full_df):
    matched_products = find_products_in_query(user_query, full_df)

    if len(matched_products) == 0:
        return (
            "Bu soru bir karşılaştırma sorusu gibi görünüyor ancak ürün kataloğunda "
            "karşılaştırılacak ürünleri net bulamadım. Ürün adını veya markayı daha açık yazarsanız "
            "daha doğru karşılaştırma yapabilirim."
        )

    if len(matched_products) == 1:
        product = matched_products[0]

        return (
            f"Sorduğunuz ürünlerden katalogda net olarak {product.get('product_name', '')} bulunuyor. "
            f"Bu ürün {product.get('brand', '')} markasına ait, fiyatı {product.get('price', '')} TL "
            f"ve {product.get('category', '')} kategorisinde yer alıyor. "
            f"Diğer ürün katalogda olmadığı için doğrudan fiyat, stok ve taksit karşılaştırması yapamıyorum. "
            f"Eğer MacBook gibi bir ürünü de ürün listesine eklerseniz sistem Lenovo ve MacBook arasında daha doğru karşılaştırma yapabilir."
        )

    product_1 = matched_products[0]
    product_2 = matched_products[1]

    price_1 = float(product_1.get("price", 0))
    price_2 = float(product_2.get("price", 0))

    cheaper_product = product_1 if price_1 <= price_2 else product_2
    expensive_product = product_2 if price_1 <= price_2 else product_1

    return (
        f"{product_1.get('product_name', '')} ve {product_2.get('product_name', '')} karşılaştırıldığında, "
        f"{cheaper_product.get('product_name', '')} fiyat açısından daha avantajlı görünüyor "
        f"({cheaper_product.get('price', '')} TL). "
        f"{expensive_product.get('product_name', '')} ise daha yüksek fiyat segmentinde yer alıyor "
        f"({expensive_product.get('price', '')} TL). "
        f"Bütçe ve fiyat/performans önceliğiniz varsa {cheaper_product.get('product_name', '')}; "
        f"premium segment veya marka tercihi önceliğiniz varsa {expensive_product.get('product_name', '')} değerlendirilebilir."
    )


def generate_chat_response(user_query, recommendation_df, full_df=None):
    if full_df is not None and is_comparison_question(user_query):
        return generate_comparison_response(user_query, full_df)

    if recommendation_df is None or len(recommendation_df) == 0:
        return "Bu ihtiyaca uygun ürün bulunamadı. Farklı bir arama ifadesi deneyebilirsiniz."

    top_product = recommendation_df.iloc[0]

    return (
        f"İhtiyacınıza en yakın ürün: {top_product.get('product_name', '')}. "
        f"Bu ürün {top_product.get('category', '')} kategorisinde yer alıyor, "
        f"{top_product.get('brand', '')} markasına ait ve "
        f"fiyatı {top_product.get('price', '')} TL olarak görünüyor. "
        f"Bu öneri, yazdığınız ihtiyacın ürün açıklamalarıyla anlamsal benzerliğine göre oluşturuldu."
    )