import pandas as pd

from src.customer_intelligence_engine import normalize_text, safe_number, money


# =====================================================
# CART RESCUE ENGINE
# Sepet terk riskini azaltan karar motoru
# =====================================================


def get_best_available_price(row):
    """
    Ürün için en avantajlı görünen fiyatı seçer.
    Öncelik: havale > peşin > kart > liste fiyatı
    """

    price_options = []

    bank_price = safe_number(row.get("bank_transfer_price", 0))
    cash_price = safe_number(row.get("cash_price", 0))
    card_price = safe_number(row.get("card_price", 0))
    list_price = safe_number(row.get("price", 0))

    if bank_price > 0:
        price_options.append(("Havale", bank_price))

    if cash_price > 0:
        price_options.append(("Peşin", cash_price))

    if card_price > 0:
        price_options.append(("Kart", card_price))

    if list_price > 0:
        price_options.append(("Liste", list_price))

    if not price_options:
        return {
            "payment_name": "Belirtilmedi",
            "price": 0,
        }

    best_payment, best_price = min(price_options, key=lambda x: x[1])

    return {
        "payment_name": best_payment,
        "price": best_price,
    }


def enrich_products_for_rescue(products_df):
    """
    Ürünlere kurtarma akışı için yardımcı kolonlar ekler.
    """

    if products_df is None or products_df.empty:
        return pd.DataFrame()

    df = products_df.copy()

    best_payment_names = []
    best_prices = []

    for _, row in df.iterrows():
        best = get_best_available_price(row)
        best_payment_names.append(best["payment_name"])
        best_prices.append(best["price"])

    df["rescue_best_payment"] = best_payment_names
    df["rescue_best_price"] = best_prices

    df["rescue_stock_score"] = df["stock_status"].apply(
        lambda x: 1 if normalize_text(x) == "stokta" else 0
    )

    df["rescue_senet_score"] = df["senet_total_price"].apply(
        lambda x: 1 if safe_number(x) > 0 else 0
    )

    df["rescue_taksit_score"] = df["installment_6_total"].apply(
        lambda x: 1 if safe_number(x) > 0 else 0
    )

    df["rescue_havale_score"] = df["bank_transfer_price"].apply(
        lambda x: 1 if safe_number(x) > 0 else 0
    )

    return df


def infer_target_categories(customer_analysis, current_results=None, cart_df=None):
    """
    Limit sorunu olduğunda hangi kategori içinde alternatif aranacağını belirler.
    Öncelik:
    1. Müşteri mesajında kategori varsa
    2. Son önerilen ürünlerin kategorisi
    3. Sepetteki ürünlerin kategorisi
    """

    categories = []

    category = customer_analysis.get("category")

    if category:
        categories.append(category)

    if current_results is not None and not current_results.empty and "category" in current_results.columns:
        categories.extend(
            current_results["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    if cart_df is not None and not cart_df.empty and "category" in cart_df.columns:
        categories.extend(
            cart_df["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    cleaned = []

    for item in categories:
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned


def infer_reference_price(current_results=None, cart_df=None):
    """
    Müşterinin pahalı bulduğu ürün/sepet için yaklaşık referans fiyat.
    """

    values = []

    if current_results is not None and not current_results.empty:
        if "price" in current_results.columns:
            values.extend(current_results["price"].apply(safe_number).tolist())

    if cart_df is not None and not cart_df.empty:
        if "price" in cart_df.columns:
            values.extend(cart_df["price"].apply(safe_number).tolist())

    values = [v for v in values if v > 0]

    if not values:
        return None

    return max(values)


def find_rescue_alternatives(
    products_df,
    customer_analysis,
    current_results=None,
    cart_df=None,
    top_n=5,
):
    """
    Limit yetersizliği / pahalı geldi / sepet terk riski için alternatif ürün bulur.
    """

    if products_df is None or products_df.empty:
        return pd.DataFrame()

    df = enrich_products_for_rescue(products_df)

    if df.empty:
        return df

    target_categories = infer_target_categories(
        customer_analysis=customer_analysis,
        current_results=current_results,
        cart_df=cart_df,
    )

    if target_categories:
        df = df[df["category"].astype(str).isin(target_categories)]

    current_ids = []

    if current_results is not None and not current_results.empty and "product_id" in current_results.columns:
        current_ids.extend(current_results["product_id"].astype(str).tolist())

    if cart_df is not None and not cart_df.empty and "product_id" in cart_df.columns:
        current_ids.extend(cart_df["product_id"].astype(str).tolist())

    if current_ids:
        df = df[~df["product_id"].astype(str).isin(current_ids)]

    budget = customer_analysis.get("budget")
    reference_price = infer_reference_price(
        current_results=current_results,
        cart_df=cart_df,
    )

    if budget:
        budget_value = safe_number(budget)
        df = df[df["rescue_best_price"] <= budget_value]

    elif reference_price:
        df = df[df["rescue_best_price"] < reference_price]

    df = df[df["rescue_best_price"] > 0]

    if df.empty:
        return df

    df["rescue_score"] = (
        df["rescue_stock_score"] * 25
        + df["rescue_havale_score"] * 20
        + df["rescue_taksit_score"] * 15
        + df["rescue_senet_score"] * 15
    )

    df = df.sort_values(
        ["rescue_score", "rescue_best_price"],
        ascending=[False, True],
    )

    return df.head(top_n)


def analyze_payment_alternatives(row):
    """
    Ürün için müşteriye sunulabilecek ödeme alternatiflerini üretir.
    """

    alternatives = []

    list_price = safe_number(row.get("price", 0))
    bank_price = safe_number(row.get("bank_transfer_price", 0))
    cash_price = safe_number(row.get("cash_price", 0))
    installment_6_total = safe_number(row.get("installment_6_total", 0))
    senet_total = safe_number(row.get("senet_total_price", 0))
    senet_monthly = safe_number(row.get("senet_monthly_9", 0))

    if bank_price > 0:
        text = f"Havale ile yaklaşık {money(bank_price)}"

        if list_price > bank_price:
            text += f" ödeme avantajı sağlar. Tasarruf: {money(list_price - bank_price)}"

        alternatives.append(text)

    if cash_price > 0:
        alternatives.append(f"Peşin ödemede yaklaşık {money(cash_price)}")

    if installment_6_total > 0:
        alternatives.append(
            f"6 taksitte aylık yaklaşık {money(installment_6_total / 6)}"
        )

    if senet_total > 0:
        if senet_monthly > 0:
            alternatives.append(
                f"Senetli ödeme ile aylık yaklaşık {money(senet_monthly)}"
            )
        else:
            alternatives.append(
                f"Senetli toplam ödeme yaklaşık {money(senet_total)}"
            )

    return alternatives


def create_rescue_answer(customer_analysis, alternatives_df):
    """
    Müşteriye satış danışmanı gibi, sepet terk ettirmeyen cevap üretir.
    """

    risks = customer_analysis.get("commerce_risks", [])
    budget = customer_analysis.get("budget")

    opening = "Anladım, ödeme veya bütçe tarafında zorlandığınızı görüyorum."

    if "LIMIT_YETERSIZ" in risks:
        opening = "Anladım, kart limiti yeterli gelmemiş olabilir."

    elif "SEPET_TERK_RISKI" in risks:
        opening = "Anladım, ürün veya sepet size pahalı gelmiş olabilir."

    elif "BUDGET_PRESSURE" in risks:
        opening = "Anladım, bütçenize daha uygun seçeneklere bakmak istiyorsunuz."

    if alternatives_df is None or alternatives_df.empty:
        return (
            f"{opening} Sepeti terk etmeden önce birkaç çözüm deneyebiliriz: "
            "daha uygun fiyatlı benzer ürünleri listeleyebiliriz, havale avantajı olan ürünlere bakabiliriz, "
            "taksitli veya senetli ödeme seçeneği olan modelleri önceliklendirebiliriz."
        )

    lines = []

    for _, row in alternatives_df.iterrows():
        product_name = row.get("product_name", "")
        category = row.get("category", "")
        stock = row.get("stock_status", "")
        best_payment = row.get("rescue_best_payment", "")
        best_price = money(row.get("rescue_best_price", 0))

        payment_options = analyze_payment_alternatives(row)

        payment_text = ""

        if payment_options:
            payment_text = " Ödeme alternatifi: " + payment_options[0]

        lines.append(
            f"- {product_name} ({category}) — {best_payment} ile yaklaşık {best_price} ({stock}).{payment_text}"
        )

    budget_text = ""

    if budget:
        budget_text = f" Belirttiğiniz {money(budget)} bütçeyi dikkate aldım."

    return (
        f"{opening} Sepeti terk etmeden önce size daha uygun alternatifler hazırladım."
        + budget_text
        + "\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "İsterseniz bu listeyi en düşük fiyat, en düşük aylık ödeme, havale avantajı veya senetli ödeme seçeneğine göre yeniden sıralayabilirim."
    )


def run_cart_rescue_flow(
    products_df,
    customer_analysis,
    current_results=None,
    cart_df=None,
):
    """
    Dışarıdan çağrılacak ana cart rescue fonksiyonu.
    """

    alternatives_df = find_rescue_alternatives(
        products_df=products_df,
        customer_analysis=customer_analysis,
        current_results=current_results,
        cart_df=cart_df,
        top_n=5,
    )

    answer = create_rescue_answer(
        customer_analysis=customer_analysis,
        alternatives_df=alternatives_df,
    )

    return {
        "decision": "CART_RESCUE",
        "analysis": customer_analysis,
        "result_df": alternatives_df,
        "answer": answer,
    }