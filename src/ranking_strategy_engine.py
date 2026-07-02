import pandas as pd

from src.customer_intelligence_engine import normalize_text, safe_number, money


# =====================================================
# RANKING STRATEGY ENGINE
# Ürünleri müşteri önceliğine göre yeniden sıralar
# =====================================================


RANKING_PATTERNS = {
    "LOWEST_PRICE": [
        "en düşük fiyat",
        "en dusuk fiyat",
        "en ucuz",
        "ucuzdan pahalıya",
        "uygun fiyat",
        "fiyata göre",
    ],
    "LOWEST_MONTHLY_PAYMENT": [
        "en düşük aylık",
        "en dusuk aylik",
        "aylık düşük",
        "aylik dusuk",
        "taksit düşük",
        "taksit dusuk",
        "aylık ödemeye göre",
        "aylik odemeye gore",
    ],
    "SENET_PRIORITY": [
        "senetli",
        "senede göre",
        "senet seçeneği",
        "senet secenegi",
        "elden ödeme",
    ],
    "BANK_TRANSFER_PRIORITY": [
        "havale",
        "havale avantajı",
        "eft",
        "banka transferi",
    ],
    "STOCK_PRIORITY": [
        "stokta olan",
        "hemen alınabilir",
        "hemen alinabilir",
        "hazır ürün",
        "hazir urun",
    ],
    "AI_MATCH_PRIORITY": [
        "en uygun",
        "bana en uygun",
        "ai uygunluk",
        "ihtiyacıma göre",
        "ihtiyacima gore",
    ],
}


def detect_ranking_strategy(user_query):
    q = normalize_text(user_query)

    for strategy, patterns in RANKING_PATTERNS.items():
        for pattern in patterns:
            if normalize_text(pattern) in q:
                return strategy

    return None


def get_lowest_price(row):
    prices = []

    for col in ["bank_transfer_price", "cash_price", "card_price", "price"]:
        value = safe_number(row.get(col, 0))

        if value > 0:
            prices.append(value)

    if not prices:
        return 0

    return min(prices)


def get_monthly_payment(row):
    monthly_options = []

    installment_6 = safe_number(row.get("installment_6_total", 0))
    installment_9 = safe_number(row.get("installment_9_total", 0))
    senet_monthly = safe_number(row.get("senet_monthly_9", 0))

    if installment_6 > 0:
        monthly_options.append(installment_6 / 6)

    if installment_9 > 0:
        monthly_options.append(installment_9 / 9)

    if senet_monthly > 0:
        monthly_options.append(senet_monthly)

    if not monthly_options:
        return 0

    return min(monthly_options)


def apply_ranking_strategy(result_df, strategy):
    if result_df is None or not isinstance(result_df, pd.DataFrame) or result_df.empty:
        return result_df

    df = result_df.copy()

    if strategy == "LOWEST_PRICE":
        df["ranking_value"] = df.apply(get_lowest_price, axis=1)
        df = df[df["ranking_value"] > 0]
        df = df.sort_values("ranking_value", ascending=True)

    elif strategy == "LOWEST_MONTHLY_PAYMENT":
        df["ranking_value"] = df.apply(get_monthly_payment, axis=1)
        df = df[df["ranking_value"] > 0]
        df = df.sort_values("ranking_value", ascending=True)

    elif strategy == "SENET_PRIORITY":
        df["ranking_value"] = df["senet_total_price"].apply(
            lambda x: 1 if safe_number(x) > 0 else 0
        )
        df["monthly_value"] = df["senet_monthly_9"].apply(safe_number)
        df = df.sort_values(
            ["ranking_value", "monthly_value"],
            ascending=[False, True],
        )

    elif strategy == "BANK_TRANSFER_PRIORITY":
        df["ranking_value"] = df["bank_transfer_price"].apply(safe_number)
        df = df[df["ranking_value"] > 0]
        df = df.sort_values("ranking_value", ascending=True)

    elif strategy == "STOCK_PRIORITY":
        df["ranking_value"] = df["stock_status"].apply(
            lambda x: 1 if normalize_text(x) == "stokta" else 0
        )
        df = df.sort_values("ranking_value", ascending=False)

    elif strategy == "AI_MATCH_PRIORITY":
        if "final_ai_score" in df.columns:
            df["ranking_value"] = df["final_ai_score"].apply(safe_number)
        elif "semantic_score" in df.columns:
            df["ranking_value"] = df["semantic_score"].apply(safe_number)
        elif "score" in df.columns:
            df["ranking_value"] = df["score"].apply(safe_number)
        else:
            df["ranking_value"] = 0

        df = df.sort_values("ranking_value", ascending=False)

    return df


def create_ranking_answer(strategy, ranked_df):
    if ranked_df is None or ranked_df.empty:
        return (
            "Bu sıralama için uygun ürün bulamadım. "
            "İsterseniz farklı bir fiyat, ödeme veya kategori tercihiyle tekrar arayabilirim."
        )

    strategy_text = {
        "LOWEST_PRICE": "en düşük fiyata göre",
        "LOWEST_MONTHLY_PAYMENT": "en düşük aylık ödeme seçeneğine göre",
        "SENET_PRIORITY": "senetli ödeme seçeneğine göre",
        "BANK_TRANSFER_PRIORITY": "havale avantajına göre",
        "STOCK_PRIORITY": "stokta olan ürünlere göre",
        "AI_MATCH_PRIORITY": "ihtiyacınıza en uygun olma durumuna göre",
    }.get(strategy, "belirttiğiniz önceliğe göre")

    lines = []

    for _, row in ranked_df.head(5).iterrows():
        name = row.get("product_name", "")
        price = money(row.get("price", 0))
        bank = money(row.get("bank_transfer_price", 0))
        senet_monthly = money(row.get("senet_monthly_9", 0))
        stock = row.get("stock_status", "")

        lines.append(
            f"- {name} — Liste fiyatı: {price}, Havale: {bank}, Senetli aylık: {senet_monthly}, Stok: {stock}"
        )

    return (
        f"Ürünleri {strategy_text} yeniden sıraladım:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "İsterseniz bu listeyi karşılaştırma tablosu şeklinde de gösterebilirim."
    )


def run_ranking_flow(user_query, current_results):
    strategy = detect_ranking_strategy(user_query)

    if strategy is None:
        return None

    ranked_df = apply_ranking_strategy(
        result_df=current_results,
        strategy=strategy,
    )

    answer = create_ranking_answer(
        strategy=strategy,
        ranked_df=ranked_df,
    )

    return {
        "decision": "RANKING_REORDER",
        "ranking_strategy": strategy,
        "result_df": ranked_df,
        "answer": answer,
    }