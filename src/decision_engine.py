import pandas as pd

from src.nlp_engine import normalize_text, PRODUCT_TYPE_LABELS


# =====================================================
# PRODUCT MATCHING RULES
# =====================================================

PRODUCT_TYPE_MATCH_WORDS = {
    "laptop": [
        "laptop",
        "bilgisayar",
        "notebook",
        "macbook",
        "dizustu",
    ],

    "telefon": [
        "telefon",
        "iphone",
        "galaxy",
        "redmi",
        "xiaomi",
        "cep telefonu",
    ],

    "buzdolabi": [
        "buzdolabi",
        "buz dolabi",
        "no frost",
        "sogutucu",
    ],

    "camasir_makinesi": [
        "camasir",
        "camasir makinesi",
        "yikama",
    ],

    "bulasik_makinesi": [
        "bulasik",
        "bulasik makinesi",
    ],

    "firin": [
        "firin",
        "ankastre",
        "ankastre firin",
        "mini firin",
        "elektrikli firin",
    ],

    "televizyon": [
        "televizyon",
        "tv",
        "smart tv",
        "oled",
        "4k",
    ],

    "supurge": [
        "supurge",
        "robot supurge",
        "dyson",
        "philips supurge",
    ],

    "blender": [
        "blender",
        "blender seti",
    ],

    "cay_makinesi": [
        "cay makinesi",
        "cayci",
    ],

    "tost_makinesi": [
        "tost makinesi",
        "tost",
    ],

    "utu": [
        "utu",
        "buharli utu",
    ],
}


# =====================================================
# BASIC HELPERS
# =====================================================

def safe_number(value):
    try:
        if value is None or pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        text = text.replace("TL", "").replace("tl", "").replace("₺", "").strip()

        if text == "":
            return 0.0

        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        else:
            if text.count(".") == 1:
                left, right = text.split(".")
                if len(right) == 3:
                    text = text.replace(".", "")

        return float(text)

    except Exception:
        return 0.0


def money(value):
    value = safe_number(value)

    if value <= 0:
        return "-"

    return f"{value:,.0f} TL".replace(",", ".")


def get_product_text(row):
    fields = [
        "product_name",
        "category",
        "brand",
        "description",
        "features",
        "use_case",
        "payment_options",
        "processor",
        "ram",
        "storage",
        "capacity",
        "energy_class",
    ]

    parts = []

    for field in fields:
        if field in row:
            parts.append(str(row.get(field, "")))

    return normalize_text(" ".join(parts))


def matches_product_type(row, product_type):
    if not product_type:
        return True

    text = get_product_text(row)
    match_words = PRODUCT_TYPE_MATCH_WORDS.get(product_type, [])

    if not match_words:
        return True

    return any(normalize_text(word) in text for word in match_words)


# =====================================================
# FILTERING
# =====================================================

def filter_by_category(products_df, category):
    if products_df.empty or not category:
        return products_df.copy()

    if "category" not in products_df.columns:
        return products_df.copy()

    filtered = products_df[
        products_df["category"].astype(str).apply(normalize_text) == normalize_text(category)
    ].copy()

    return filtered


def filter_by_product_type(products_df, product_type):
    if products_df.empty or not product_type:
        return products_df.copy()

    filtered = products_df[
        products_df.apply(lambda row: matches_product_type(row, product_type), axis=1)
    ].copy()

    return filtered


def filter_by_brand(products_df, brand):
    if products_df.empty or not brand:
        return products_df.copy()

    if "brand" not in products_df.columns:
        return products_df.copy()

    filtered = products_df[
        products_df["brand"].astype(str).apply(normalize_text) == normalize_text(brand)
    ].copy()

    return filtered


def filter_by_budget(products_df, budget):
    if products_df.empty or not budget:
        return products_df.copy()

    if "price" not in products_df.columns:
        return products_df.copy()

    filtered = products_df[
        products_df["price"].apply(safe_number) <= safe_number(budget)
    ].copy()

    return filtered


# =====================================================
# DECISION ANSWERS
# =====================================================

def create_category_clarification(query_info):
    category = query_info.get("category")

    if category == "Beyaz Eşya":
        return (
            "Beyaz eşya için yardımcı olabilirim. Daha doğru öneri yapabilmem için hangi ürün grubunu istediğinizi "
            "bilmem gerekiyor: buzdolabı, çamaşır makinesi, bulaşık makinesi, fırın ya da çeyiz paketi mi düşünüyorsunuz?"
        )

    if category == "Bilgisayar":
        return (
            "Bilgisayar kategorisinde yardımcı olabilirim. Öğrenci kullanımı, oyun, ofis veya yazılım için mi arıyorsunuz? "
            "Bütçenizi de yazarsanız daha doğru laptop öneririm."
        )

    if category == "Telefon":
        return (
            "Telefon kategorisinde yardımcı olabilirim. Bütçenizi, marka tercihinizi veya ödeme şeklinizi belirtirseniz "
            "size daha uygun modelleri önerebilirim."
        )

    if category == "Televizyon":
        return (
            "Televizyon için yardımcı olabilirim. Kaç inç düşündüğünüzü, bütçenizi veya kullanım amacınızı yazarsanız "
            "daha doğru öneri sunabilirim."
        )

    if category == "Küçük Ev Aleti":
        return (
            "Küçük ev aleti kategorisinde yardımcı olabilirim. Süpürge, blender, çay makinesi, tost makinesi veya ütü gibi "
            "hangi ürünü düşündüğünüzü yazarsanız daha doğru öneri yapabilirim."
        )

    return (
        "Hangi ürün grubunu aradığınızı biraz daha net yazarsanız size daha doğru yardımcı olabilirim."
    )


def create_budget_clarification(query_info):
    budget = query_info.get("budget")

    return (
        f"{money(budget)} altı ürün aradığınızı anladım; ancak kategori belirtmediğiniz için rastgele ürün önermek doğru olmaz. "
        "Laptop, telefon, beyaz eşya, televizyon veya küçük ev aleti gibi bir kategori yazarsanız size daha doğru seçenekler sunabilirim."
    )


def create_no_product_type_match(query_info):
    product_type = query_info.get("product_type")
    category = query_info.get("category")
    label = PRODUCT_TYPE_LABELS.get(product_type, product_type or "bu ürün tipi")

    if category:
        return (
            f"{label} aradığınızı anladım; ancak ürün listesinde {category} kategorisi altında "
            f"{label} için uygun ürün bulunamadı. Bu yüzden alakasız bir ürün önermek yerine ürün bulunamadı bilgisini gösteriyorum."
        )

    return (
        f"{label} aradığınızı anladım; ancak mevcut ürün listesinde bu ürün tipine uygun ürün bulunamadı. "
        "Bu yüzden alakasız bir ürün önermek yerine ürün bulunamadı bilgisini gösteriyorum."
    )


def create_no_budget_match(query_info):
    budget = query_info.get("budget")
    product_type = query_info.get("product_type")
    category = query_info.get("category")
    label = PRODUCT_TYPE_LABELS.get(product_type, product_type)

    if product_type:
        return (
            f"{money(budget)} altında {label} için uygun seçenek bulamadım. "
            "Bütçeyi biraz artırırsanız tekrar kontrol edebilirim."
        )

    if category:
        return (
            f"{category} kategorisinde {money(budget)} altında uygun ürün bulamadım. "
            "Bütçeyi artırabilir veya farklı bir kategori seçebilirsiniz."
        )

    return (
        f"{money(budget)} altında uygun ürün bulamadım. Kategori belirtirseniz daha net kontrol edebilirim."
    )


def create_product_recommendation_answer(query_info, result_df):
    if result_df.empty:
        return "Bu kriterlere uygun ürün bulunamadı."

    top = result_df.iloc[0]

    name = str(top.get("product_name", "Ürün"))
    price = money(top.get("price", 0))
    stock = str(top.get("stock_status", ""))

    answer = (
        f"Talebinize en yakın ürün {name} olarak görünüyor. "
        f"Liste fiyatı yaklaşık {price}."
    )

    if stock:
        answer += f" Stok durumu: {stock}."

    alternatives = result_df.iloc[1:4]["product_name"].astype(str).tolist() if "product_name" in result_df.columns else []

    if alternatives:
        answer += " Alternatif olarak " + ", ".join(alternatives) + " ürünlerini de değerlendirebilirsiniz."

    return answer


# =====================================================
# MAIN DECISION ENGINE
# =====================================================

def make_decision(products_df, query_info):
    """
    Returns:
    {
        "decision": str,
        "query_info": dict,
        "result_df": DataFrame,
        "fallback_answer": str
    }
    """

    if products_df is None or products_df.empty:
        return {
            "decision": "NO_PRODUCTS",
            "query_info": query_info,
            "result_df": pd.DataFrame(),
            "fallback_answer": "Ürün listesi bulunamadı."
        }

    category = query_info.get("category")
    product_type = query_info.get("product_type")
    brand = query_info.get("brand")
    budget = query_info.get("budget")
    payments = query_info.get("payments", [])
    is_package = query_info.get("is_package", False)

    has_category = category is not None
    has_product_type = product_type is not None
    has_brand = brand is not None
    has_budget = budget is not None
    has_payment = len(payments) > 0

    # 1. Sadece kategori yazıldıysa ürün önerme, netleştirme sor
    if has_category and not has_product_type and not has_brand and not has_budget and not has_payment and not is_package:
        return {
            "decision": "CATEGORY_CLARIFICATION",
            "query_info": query_info,
            "result_df": pd.DataFrame(),
            "fallback_answer": create_category_clarification(query_info)
        }

    # 2. Sadece bütçe yazıldıysa kategori sor
    if has_budget and not has_category and not has_product_type and not has_brand and not has_payment and not is_package:
        return {
            "decision": "BUDGET_CLARIFICATION",
            "query_info": query_info,
            "result_df": pd.DataFrame(),
            "fallback_answer": create_budget_clarification(query_info)
        }

    filtered = products_df.copy()

    # 3. Kategori filtresi
    if has_category:
        category_df = filter_by_category(filtered, category)

        if not category_df.empty:
            filtered = category_df

    # 4. Ürün tipi varsa strict filtre
    if has_product_type:
        type_df = filter_by_product_type(filtered, product_type)

        if type_df.empty:
            return {
                "decision": "NO_PRODUCT_TYPE_MATCH",
                "query_info": query_info,
                "result_df": pd.DataFrame(),
                "fallback_answer": create_no_product_type_match(query_info)
            }

        filtered = type_df

    # 5. Marka varsa filtrele
    if has_brand:
        brand_df = filter_by_brand(filtered, brand)

        if not brand_df.empty:
            filtered = brand_df

    # 6. Bütçe varsa strict bütçe filtresi
    if has_budget:
        budget_df = filter_by_budget(filtered, budget)

        if budget_df.empty:
            return {
                "decision": "NO_BUDGET_MATCH",
                "query_info": query_info,
                "result_df": pd.DataFrame(),
                "fallback_answer": create_no_budget_match(query_info)
            }

        filtered = budget_df

    # 7. Basit sıralama
    if "price" in filtered.columns:
        filtered = filtered.copy()
        filtered["decision_price"] = filtered["price"].apply(safe_number)
        filtered = filtered.sort_values("decision_price", ascending=True)

    result_df = filtered.head(5).copy()

    return {
        "decision": "PRODUCT_RECOMMENDATION",
        "query_info": query_info,
        "result_df": result_df,
        "fallback_answer": create_product_recommendation_answer(query_info, result_df)
    }