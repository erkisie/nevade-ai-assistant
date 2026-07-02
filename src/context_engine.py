# =====================================================
# CONTEXT ENGINE
# =====================================================

def create_empty_customer_context():
    return {
        "category": None,
        "product_type": None,
        "brand": None,
        "last_user_query": None,
    }


def update_customer_context(context, query_info):
    if context is None:
        context = create_empty_customer_context()

    updated = context.copy()

    if query_info.get("category"):
        updated["category"] = query_info.get("category")

    if query_info.get("product_type"):
        updated["product_type"] = query_info.get("product_type")

    if query_info.get("brand"):
        updated["brand"] = query_info.get("brand")

    if query_info.get("original_query"):
        updated["last_user_query"] = query_info.get("original_query")

    return updated


def apply_customer_context(query_info, context):
    """
    Kullanıcı takip mesajı yazarsa önceki bağlamı uygular.

    Örnek:
    1. mesaj: "Beyaz eşya"
    2. mesaj: "3000 TL altı ürün öner"

    2. mesajda kategori yok ama önceki kategori Beyaz Eşya olduğu için query_info içine eklenir.
    """

    if context is None:
        context = create_empty_customer_context()

    enriched = query_info.copy()

    has_category = enriched.get("category") is not None
    has_product_type = enriched.get("product_type") is not None
    has_brand = enriched.get("brand") is not None
    has_budget = enriched.get("budget") is not None
    has_package = enriched.get("is_package") is True

    # Sadece bütçe yazıldıysa önceki kategori/ürün tipi/marka kullanılır
    budget_followup = (
        has_budget
        and not has_category
        and not has_product_type
        and not has_brand
        and not has_package
    )

    if budget_followup:
        if context.get("category"):
            enriched["category"] = context.get("category")

        if context.get("product_type"):
            enriched["product_type"] = context.get("product_type")

        if context.get("brand"):
            enriched["brand"] = context.get("brand")

        enriched["used_context"] = True

    else:
        enriched["used_context"] = False

    return enriched