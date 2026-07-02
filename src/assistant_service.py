import pandas as pd

from src.personal_shopping_orchestrator import run_personal_shopping_assistant
from src.llm_response_orchestrator import generate_response
from src.customer_intelligence_engine import safe_number, money


# =====================================================
# ASSISTANT SERVICE
# Premium arayüzün çağıracağı tek ana servis katmanı
# =====================================================


def load_products(path="data/products.csv"):
    """
    Ürün verisini yükler.
    App.py tarafında doğrudan csv okuma yerine bu fonksiyon kullanılacak.
    """

    try:
        df = pd.read_csv(path)

        if "product_id" not in df.columns:
            df["product_id"] = range(1, len(df) + 1)

        return df

    except Exception as e:
        print("Ürün verisi yüklenemedi:", e)
        return pd.DataFrame()


def get_products_by_ids(products_df, product_ids):
    """
    Sepet/favori gibi alanlarda product_id listesinden ürünleri getirir.
    """

    if products_df is None or products_df.empty:
        return pd.DataFrame()

    if not product_ids:
        return pd.DataFrame()

    if "product_id" not in products_df.columns:
        return pd.DataFrame()

    return products_df[products_df["product_id"].isin(product_ids)].copy()


def get_decision_label(decision):
    labels = {
        "PRODUCT_RECOMMENDATION": "Ürün Önerisi",
        "CART_RESCUE": "Sepet Kurtarma",
        "CHEAPER_ALTERNATIVE": "Daha Uygun Alternatif",
        "PAYMENT_HELP": "Ödeme Alternatifi",
        "PAYMENT_ALTERNATIVE": "Ödeme Alternatifi",
        "PACKAGE_RECOMMENDATION": "Çeyiz / Yeni Ev Paketi",
        "BUDGET_OPTIMIZED": "Bütçe Optimizasyonu",
        "BUDGET_PARTIALLY_OPTIMIZED": "Kısmi Bütçe Optimizasyonu",
        "RANKING_REORDER": "Akıllı Yeniden Sıralama",
        "ORDER_SUPPORT": "Sipariş Desteği",
        "GENERAL_HELP": "Genel Asistan",
        "NO_PRODUCTS": "Ürün Bulunamadı",
        "NO_PRODUCT_TYPE_MATCH": "Ürün Tipi Bulunamadı",
        "NO_BUDGET_MATCH": "Bütçe Uygun Değil",
    }

    return labels.get(decision, decision or "AI Asistan")


def get_decision_badge_type(decision):
    """
    UI tarafında renk/etiket mantığı için kullanılabilir.
    """

    if decision in ["CART_RESCUE", "CHEAPER_ALTERNATIVE"]:
        return "warning"

    if decision in ["BUDGET_OPTIMIZED", "BUDGET_PARTIALLY_OPTIMIZED"]:
        return "budget"

    if decision in ["PAYMENT_HELP", "PAYMENT_ALTERNATIVE"]:
        return "payment"

    if decision in ["PACKAGE_RECOMMENDATION"]:
        return "package"

    if decision in ["PRODUCT_RECOMMENDATION", "RANKING_REORDER"]:
        return "success"

    return "default"


def calculate_cart_summary(cart_df):
    """
    Sepet toplamı, havale toplamı, taksit/senet sayısı gibi özet metrikler.
    """

    if cart_df is None or cart_df.empty:
        return {
            "item_count": 0,
            "total_price": 0,
            "bank_transfer_total": 0,
            "senet_available_count": 0,
            "installment_available_count": 0,
            "summary_text": "Sepet boş.",
        }

    total_price = 0
    bank_transfer_total = 0
    senet_count = 0
    installment_count = 0

    for _, row in cart_df.iterrows():
        price = safe_number(row.get("price", 0))
        bank = safe_number(row.get("bank_transfer_price", 0))
        senet = safe_number(row.get("senet_total_price", 0))
        installment = safe_number(row.get("installment_6_total", 0))

        total_price += price

        if bank > 0:
            bank_transfer_total += bank
        else:
            bank_transfer_total += price

        if senet > 0:
            senet_count += 1

        if installment > 0:
            installment_count += 1

    summary_text = (
        f"Sepette {len(cart_df)} ürün var. "
        f"Liste toplamı {money(total_price)}, "
        f"havale toplamı yaklaşık {money(bank_transfer_total)}."
    )

    return {
        "item_count": len(cart_df),
        "total_price": total_price,
        "bank_transfer_total": bank_transfer_total,
        "senet_available_count": senet_count,
        "installment_available_count": installment_count,
        "summary_text": summary_text,
    }


def calculate_product_metrics(products_df):
    """
    Premium dashboard için genel ürün metrikleri.
    """

    if products_df is None or products_df.empty:
        return {
            "total_products": 0,
            "stock_products": 0,
            "average_price": 0,
            "min_price": 0,
            "max_price": 0,
            "senet_products": 0,
            "bank_transfer_products": 0,
            "installment_products": 0,
            "category_count": 0,
            "brand_count": 0,
        }

    df = products_df.copy()

    prices = df["price"].apply(safe_number) if "price" in df.columns else pd.Series([])

    stock_products = 0
    if "stock_status" in df.columns:
        stock_products = len(df[df["stock_status"].astype(str).str.lower() == "stokta"])

    senet_products = 0
    if "senet_total_price" in df.columns:
        senet_products = len(df[df["senet_total_price"].apply(safe_number) > 0])

    bank_transfer_products = 0
    if "bank_transfer_price" in df.columns:
        bank_transfer_products = len(df[df["bank_transfer_price"].apply(safe_number) > 0])

    installment_products = 0
    if "installment_6_total" in df.columns:
        installment_products = len(df[df["installment_6_total"].apply(safe_number) > 0])

    category_count = df["category"].nunique() if "category" in df.columns else 0
    brand_count = df["brand"].nunique() if "brand" in df.columns else 0

    return {
        "total_products": len(df),
        "stock_products": stock_products,
        "average_price": float(prices.mean()) if len(prices) else 0,
        "min_price": float(prices.min()) if len(prices) else 0,
        "max_price": float(prices.max()) if len(prices) else 0,
        "senet_products": senet_products,
        "bank_transfer_products": bank_transfer_products,
        "installment_products": installment_products,
        "category_count": category_count,
        "brand_count": brand_count,
    }


def prepare_product_cards(result_df, max_items=6):
    """
    UI tarafına temiz ürün kartı verisi hazırlar.
    """

    if result_df is None or not isinstance(result_df, pd.DataFrame) or result_df.empty:
        return []

    cards = []

    for _, row in result_df.head(max_items).iterrows():
        price = safe_number(row.get("price", 0))
        bank = safe_number(row.get("bank_transfer_price", 0))
        cash = safe_number(row.get("cash_price", 0))
        card_price = safe_number(row.get("card_price", 0))
        installment_6 = safe_number(row.get("installment_6_total", 0))
        senet_monthly = safe_number(row.get("senet_monthly_9", 0))
        senet_total = safe_number(row.get("senet_total_price", 0))

        best_price = price
        best_price_label = "Liste fiyatı"

        price_options = []

        if bank > 0:
            price_options.append(("Havale fiyatı", bank))

        if cash > 0:
            price_options.append(("Peşin fiyat", cash))

        if card_price > 0:
            price_options.append(("Kart fiyatı", card_price))

        if price > 0:
            price_options.append(("Liste fiyatı", price))

        if price_options:
            best_price_label, best_price = min(price_options, key=lambda x: x[1])

        saving = 0
        if price > 0 and best_price > 0 and price > best_price:
            saving = price - best_price

        card = {
            "product_id": row.get("product_id"),
            "product_name": row.get("product_name", ""),
            "category": row.get("category", ""),
            "brand": row.get("brand", ""),
            "stock_status": row.get("stock_status", ""),
            "image_link": row.get("image_link", ""),
            "product_link": row.get("product_link", ""),
            "price": price,
            "price_text": money(price),
            "best_price": best_price,
            "best_price_text": money(best_price),
            "best_price_label": best_price_label,
            "saving": saving,
            "saving_text": money(saving) if saving > 0 else "",
            "bank_transfer_price": bank,
            "bank_transfer_text": money(bank) if bank > 0 else "",
            "installment_6_monthly": installment_6 / 6 if installment_6 > 0 else 0,
            "installment_6_monthly_text": money(installment_6 / 6) if installment_6 > 0 else "",
            "senet_monthly": senet_monthly,
            "senet_monthly_text": money(senet_monthly) if senet_monthly > 0 else "",
            "senet_total": senet_total,
            "senet_total_text": money(senet_total) if senet_total > 0 else "",
            "package_group": row.get("package_group", ""),
            "semantic_score": safe_number(row.get("semantic_score", 0)),
            "final_ai_score": safe_number(row.get("final_ai_score", 0)),
            "ranking_value": safe_number(row.get("ranking_value", 0)),
        }

        cards.append(card)

    return cards


def run_customer_assistant(
    products_df,
    user_query,
    customer_context=None,
    current_results=None,
    cart_df=None,
    mode="customer",
):
    """
    Premium arayüzün kullanacağı ana fonksiyon.

    Parametreler:
    - products_df: ürün listesi
    - user_query: müşteri mesajı
    - customer_context: müşteri profili / konuşma hafızası
    - current_results: önceki öneriler
    - cart_df: sepet ürünleri
    - mode: customer veya store
    """

    if customer_context is None:
        customer_context = {}

    result = run_personal_shopping_assistant(
        products_df=products_df,
        user_query=user_query,
        current_results=current_results,
        cart_df=cart_df,
        customer_context=customer_context,
    )

    answer = generate_response(result, mode=mode)

    result_df = result.get("result_df", pd.DataFrame())

    product_cards = prepare_product_cards(result_df)

    decision = result.get("decision", "GENERAL_HELP")

    response = {
        "decision": decision,
        "decision_label": get_decision_label(decision),
        "decision_badge_type": get_decision_badge_type(decision),
        "answer": answer,
        "result_df": result_df,
        "product_cards": product_cards,
        "customer_analysis": result.get("customer_analysis", {}),
        "analysis_summary": result.get("analysis_summary", ""),
        "customer_profile": result.get("customer_profile", {}),
        "profile_summary": result.get("profile_summary", ""),
        "context_summary": result.get("context_summary", ""),
        "cart_summary": result.get("cart_summary", ""),
        "cart_metrics": calculate_cart_summary(cart_df),
        "raw_result": result,
    }

    return response


def run_store_assistant(
    products_df,
    user_query,
    customer_context=None,
    current_results=None,
    cart_df=None,
):
    """
    Mağaza personeli modu.
    """

    return run_customer_assistant(
        products_df=products_df,
        user_query=user_query,
        customer_context=customer_context,
        current_results=current_results,
        cart_df=cart_df,
        mode="store",
    )


def get_quick_customer_prompts():
    return [
        "Annem için kullanımı kolay telefon öner",
        "Yeni ev kuruyorum 50000 TL çeyiz paketi yap",
        "Kart limitim yetmedi",
        "Çok pahalı, daha ucuzu var mı?",
        "Senetle buzdolabı alabilir miyim?",
        "En düşük aylık ödemeye göre sırala",
        "Havale avantajı olan telefon öner",
        "Siparişim nerede?",
    ]


def get_quick_store_prompts():
    return [
        "Müşteri kart limitim yetmedi diyor ne önerelim?",
        "Müşteri 30000 TL bütçeyle beyaz eşya istiyor",
        "Bu üründe senetli ödeme var mı?",
        "Müşteri pahalı buldu, nasıl alternatif sunalım?",
        "Havale avantajlı ürünleri göster",
        "Stokta olan telefonları listele",
    ]


def get_ai_capabilities():
    return [
        {
            "title": "Kişisel Ürün Önerisi",
            "description": "Müşteri ihtiyacına göre ürün önerir.",
        },
        {
            "title": "Sepet Terk Önleme",
            "description": "Kart limiti veya fiyat sorunu yaşayan müşteriye alternatif sunar.",
        },
        {
            "title": "Bütçe Optimizasyonu",
            "description": "Çeyiz ve paket alışverişlerinde bütçeye uygun kombinasyon üretir.",
        },
        {
            "title": "Ödeme Alternatifi",
            "description": "Havale, taksit ve senet seçeneklerini karşılaştırır.",
        },
        {
            "title": "Kişisel Müşteri Profili",
            "description": "Önceki mesajlardan kategori, bütçe ve ödeme tercihlerini hatırlar.",
        },
        {
            "title": "Akıllı Yeniden Sıralama",
            "description": "Ürünleri fiyat, aylık ödeme, stok veya ödeme avantajına göre sıralar.",
        },
        {
            "title": "Lokal LLM Desteği",
            "description": "Ollama ile yerel model kullanır, hata durumunda güvenli fallback çalışır.",
        },
    ]