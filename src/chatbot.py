def generate_chatbot_response(user_message, recommended_products):
    if recommended_products is None or len(recommended_products) == 0:
        return "Aradığınız ihtiyaca uygun ürün bulamadım. Farklı bir ifade deneyebilirsiniz."

    response = "İhtiyacınıza göre şu ürünleri öneriyorum:\n\n"

    for index, row in recommended_products.iterrows():
        response += (
            f"- {row['product_name']} | "
            f"Kategori: {row['category']} | "
            f"Marka: {row['brand']} | "
            f"Fiyat: {row['price']} TL\n"
        )

    response += "\nBu ürünler, yazdığınız ihtiyaca benzer özellikler taşıdığı için önerildi."

    return response