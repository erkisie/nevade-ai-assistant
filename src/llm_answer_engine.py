import pandas as pd


# =====================================================
# OPTIONAL LLM IMPORT
# =====================================================

try:
    from llm_service import call_gemini
except Exception:
    call_gemini = None


# =====================================================
# BASIC HELPERS
# =====================================================

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


def money(value):
    value = safe_number(value)

    if value <= 0:
        return "-"

    return f"{value:,.0f} TL".replace(",", ".")


def row_to_llm_product(row):
    return {
        "product_id": safe_text(row.get("product_id", "")),
        "product_name": safe_text(row.get("product_name", "")),
        "category": safe_text(row.get("category", "")),
        "brand": safe_text(row.get("brand", "")),
        "price": money(row.get("price", 0)),
        "cash_price": money(row.get("cash_price", 0)),
        "bank_transfer_price": money(row.get("bank_transfer_price", 0)),
        "card_price": money(row.get("card_price", 0)),
        "installment_6_total": money(row.get("installment_6_total", 0)),
        "senet_total_price": money(row.get("senet_total_price", 0)),
        "senet_monthly_9": money(row.get("senet_monthly_9", 0)),
        "stock_status": safe_text(row.get("stock_status", "")),
        "processor": safe_text(row.get("processor", "")),
        "ram": safe_text(row.get("ram", "")),
        "storage": safe_text(row.get("storage", "")),
        "capacity": safe_text(row.get("capacity", "")),
        "energy_class": safe_text(row.get("energy_class", "")),
        "screen_size": safe_text(row.get("screen_size", "")),
        "warranty": safe_text(row.get("warranty", "")),
        "description": safe_text(row.get("description", "")),
        "features": safe_text(row.get("features", "")),
        "use_case": safe_text(row.get("use_case", "")),
        "package_group": safe_text(row.get("package_group", "")),
    }


def dataframe_to_products(result_df, limit=6):
    if result_df is None:
        return []

    if not isinstance(result_df, pd.DataFrame):
        return []

    if result_df.empty:
        return []

    products = []

    for _, row in result_df.head(limit).iterrows():
        products.append(row_to_llm_product(row))

    return products


# =====================================================
# ANSWER QUALITY CONTROL
# =====================================================

def is_incomplete_answer(answer):
    """
    LLM bazen cevabı yarım bırakabiliyor.
    Bu fonksiyon ekrana yarım cevap basılmasını engeller.
    """

    if answer is None:
        return True

    text = str(answer).strip()

    if text == "":
        return True

    # Çok kısa cevaplar genelde eksik kalıyor
    if len(text) < 45:
        return True

    # Cümle bitişi yoksa yarım olma ihtimali yüksek
    if not text.endswith((".", "!", "?", ":", "…")):
        return True

    # Şu kelimelerle bitiyorsa cümle büyük ihtimalle yarımdır
    bad_endings = [
        "aradığınız",
        "istediğiniz",
        "uygun",
        "ancak",
        "ama",
        "ve",
        "veya",
        "için",
        "şu anda",
        "maalesef",
        "ürün listemizde",
        "öneriyorum",
        "olarak",
        "ile",
        "bu yüzden",
    ]

    lowered = text.lower()

    for ending in bad_endings:
        if lowered.endswith(ending):
            return True

    return False


def create_strong_fallback_answer(decision_result):
    decision = decision_result.get("decision", "")
    query_info = decision_result.get("query_info", {})
    result_df = decision_result.get("result_df", pd.DataFrame())
    fallback_answer = decision_result.get(
        "fallback_answer",
        "Size yardımcı olabilmem için aradığınız ürünü biraz daha detaylandırabilir misiniz?"
    )

    category = query_info.get("category")
    product_type_label = query_info.get("product_type_label") or query_info.get("product_type")
    budget = query_info.get("budget")
    payments = query_info.get("payments", [])

    # 1. Ürün tipi sistemde yoksa
    if decision == "NO_PRODUCT_TYPE_MATCH":
        return (
            f"{fallback_answer} "
            "Size alakasız bir ürün önermek istemem. "
            "İsterseniz mevcut ürünler arasından farklı bir kategori veya benzer bir ürün tipi için yeniden yardımcı olabilirim."
        )

    # 2. Sadece kategori yazıldıysa
    if decision == "CATEGORY_CLARIFICATION":
        return (
            f"{fallback_answer} "
            "Bütçenizi ve ödeme tercihinizi de yazarsanız size daha net seçenekler sunabilirim."
        )

    # 3. Sadece bütçe yazıldıysa
    if decision == "BUDGET_CLARIFICATION":
        return (
            f"{fallback_answer} "
            "Örneğin laptop, telefon, beyaz eşya, televizyon veya küçük ev aleti şeklinde kategori belirtebilirsiniz."
        )

    # 4. Bütçeye uygun ürün yoksa
    if decision == "NO_BUDGET_MATCH":
        return (
            f"{fallback_answer} "
            "Dilerseniz bütçeyi biraz artırarak veya farklı bir kategori seçerek tekrar kontrol edebilirim."
        )

    # 5. Paket / çeyiz cevabı
    if decision in ["PACKAGE_RECOMMENDATION", "NO_PACKAGE_MATCH"]:
        return fallback_answer

    # 6. Ürün önerisi varsa
    if decision == "PRODUCT_RECOMMENDATION" and isinstance(result_df, pd.DataFrame) and not result_df.empty:
        top = result_df.iloc[0]

        name = safe_text(top.get("product_name", "Ürün"))
        price = money(top.get("price", 0))
        stock = safe_text(top.get("stock_status", ""))
        brand = safe_text(top.get("brand", ""))

        answer = (
            f"Talebinize en uygun seçenek olarak {brand + ' ' if brand else ''}{name} ürününü önerebilirim. "
            f"Liste fiyatı yaklaşık {price}."
        )

        if stock:
            answer += f" Stok durumu {stock} olarak görünüyor."

        if "senet" in payments and safe_number(top.get("senet_total_price", 0)) > 0:
            answer += f" Senetli toplam ödeme yaklaşık {money(top.get('senet_total_price', 0))}."

        if "havale" in payments and safe_number(top.get("bank_transfer_price", 0)) > 0:
            answer += f" Havale fiyatı yaklaşık {money(top.get('bank_transfer_price', 0))}."

        if budget:
            answer += f" Belirttiğiniz {money(budget)} bütçe dikkate alınarak değerlendirme yapılmıştır."

        alternatives = []

        if "product_name" in result_df.columns:
            alternatives = result_df.iloc[1:4]["product_name"].astype(str).tolist()

        if alternatives:
            answer += " Alternatif olarak " + ", ".join(alternatives) + " ürünlerini de inceleyebilirsiniz."

        return answer

    # 7. Genel güvenli cevap
    return fallback_answer


# =====================================================
# MAIN LLM ANSWER ENGINE
# =====================================================

def generate_customer_answer_with_llm(decision_result):
    """
    Input:
    decision_result = {
        "decision": str,
        "query_info": dict,
        "result_df": DataFrame,
        "fallback_answer": str
    }

    Output:
    Tamamlanmış müşteri cevabı
    """

    strong_fallback = create_strong_fallback_answer(decision_result)

    if call_gemini is None:
        return strong_fallback

    decision = decision_result.get("decision", "")
    query_info = decision_result.get("query_info", {})
    result_df = decision_result.get("result_df", pd.DataFrame())
    products = dataframe_to_products(result_df)

    user_query = query_info.get("original_query", "")

    prompt = f"""
Sen Nevade.com için çalışan müşteri odaklı bir AI alışveriş asistanısın.

Sistem müşterinin mesajını analiz etti ve ürün listesine göre güvenli bir karar verdi.
Senin görevin bu kararı müşteriye eksiksiz, doğal ve profesyonel Türkçe ile yazmak.

MUTLAK KURALLAR:
- Cevabın yarım kalmasın.
- Cevabın mutlaka tamamlanmış cümlelerden oluşsun.
- Cevabı 3 ila 6 cümle arasında tut.
- Ürün listesinde olmayan ürünü asla önerme.
- Ürün listesi boşsa ürün adı verme.
- Karar NO_PRODUCT_TYPE_MATCH ise aranan ürünün bulunmadığını söyle.
- Karar BUDGET_CLARIFICATION ise kategori sormadan ürün önerme.
- Karar CATEGORY_CLARIFICATION ise ürün grubunu netleştirmesini iste.
- Karar NO_BUDGET_MATCH ise bütçenin altında uygun ürün olmadığını söyle.
- Karar PRODUCT_RECOMMENDATION ise sadece verilen ürünlerden bahset.
- Karar PACKAGE_RECOMMENDATION ise verilen paket ürünlerini özetle.
- Teknik kelimeler kullanma: NLP, algoritma, filtre, dataframe, fallback deme.
- Müşteriye güven veren, net ve yardımcı bir ton kullan.
- Cevabın sonunda uygun bir sonraki adımı söyle.

Müşteri mesajı:
{user_query}

Algılanan bilgiler:
{query_info}

Sistemin kararı:
{decision}

Sistemin güvenli cevabı:
{strong_fallback}

Sadece bahsedilebilecek ürünler:
{products}

Şimdi müşteriye eksiksiz son cevabı yaz.
"""

    try:
        answer = call_gemini(prompt)

        if answer and not is_incomplete_answer(answer):
            return str(answer).strip()

    except Exception as e:
        print("LLM answer engine error:", e)

    return strong_fallback