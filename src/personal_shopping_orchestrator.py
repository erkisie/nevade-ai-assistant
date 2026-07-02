import pandas as pd
from src.budget_optimization_engine import run_budget_optimization
from src.customer_intelligence_engine import (
    analyze_customer_message,
    explain_customer_analysis,
    safe_number,
    money,
)

from src.cart_rescue_engine import run_cart_rescue_flow
from src.ranking_strategy_engine import run_ranking_flow
from src.package_engine import make_package_decision
from src.decision_engine import make_decision
from src.customer_profile_engine import (
    create_empty_customer_profile,
    update_customer_profile,
    enrich_analysis_with_profile,
    create_profile_summary,
)
try:
    from src.semantic_engine import apply_semantic_reranking
except Exception:
    apply_semantic_reranking = None


# =====================================================
# PERSONAL SHOPPING ORCHESTRATOR
# Müşteri kişisel alışveriş asistanı ana beyni
# =====================================================


def convert_customer_analysis_to_query_info(customer_analysis):
    """
    Eski Decision Engine ve Package Engine ile uyumlu query_info üretir.
    """

    return {
        "original_query": customer_analysis.get("original_query", ""),
        "normalized_query": customer_analysis.get("normalized_query", ""),
        "intent": customer_analysis.get("intent", ""),
        "category": customer_analysis.get("category"),
        "product_type": customer_analysis.get("product_type"),
        "brand": customer_analysis.get("brand"),
        "budget": customer_analysis.get("budget"),
        "payments": customer_analysis.get("payments", []),
        "is_package": customer_analysis.get("is_package", False),
        "commerce_risks": customer_analysis.get("commerce_risks", []),
        "intent_confidence": customer_analysis.get("intent_confidence", 0),
    }


def get_products_by_ids(products_df, ids):
    if products_df is None or products_df.empty or not ids:
        return pd.DataFrame()

    if "product_id" not in products_df.columns:
        return pd.DataFrame()

    return products_df[
        products_df["product_id"].astype(str).isin([str(x) for x in ids])
    ].copy()


def build_context_summary(customer_context=None):
    if not customer_context:
        return "Kayıtlı bağlam yok."

    parts = []

    for key in ["category", "product_type", "brand", "last_user_query"]:
        value = customer_context.get(key)

        if value:
            parts.append(f"{key}: {value}")

    if not parts:
        return "Kayıtlı bağlam yok."

    return " | ".join(parts)


def build_cart_summary(cart_df):
    if cart_df is None or cart_df.empty:
        return {
            "cart_total": 0,
            "cart_count": 0,
            "cart_categories": [],
            "cart_text": "Sepet boş.",
        }

    total = 0

    if "price" in cart_df.columns:
        total = cart_df["price"].apply(safe_number).sum()

    categories = []

    if "category" in cart_df.columns:
        categories = (
            cart_df["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    names = []

    if "product_name" in cart_df.columns:
        names = cart_df["product_name"].dropna().astype(str).tolist()

    cart_text = (
        f"Sepette {len(cart_df)} ürün var. "
        f"Toplam yaklaşık {money(total)}. "
        f"Ürünler: {', '.join(names) if names else '-'}"
    )

    return {
        "cart_total": total,
        "cart_count": len(cart_df),
        "cart_categories": categories,
        "cart_text": cart_text,
    }


def create_payment_help_answer(products_df, customer_analysis, current_results=None):
    """
    Müşteri ödeme alternatifi sorarsa ödeme odaklı cevap üretir.
    """

    target_df = pd.DataFrame()

    if current_results is not None and not current_results.empty:
        target_df = current_results.copy()
    else:
        query_info = convert_customer_analysis_to_query_info(customer_analysis)
        decision_result = make_decision(products_df, query_info)
        target_df = decision_result.get("result_df", pd.DataFrame())

    if target_df is None or target_df.empty:
        return {
            "decision": "PAYMENT_HELP",
            "analysis": customer_analysis,
            "result_df": pd.DataFrame(),
            "answer": (
                "Ödeme seçeneklerini kontrol edebilmem için ürün veya kategori bilgisini biraz daha net yazabilir misiniz? "
                "Örneğin 'senetle buzdolabı', 'havale avantajlı telefon' veya 'taksitli laptop' şeklinde yazabilirsiniz."
            ),
        }

    lines = []

    for _, row in target_df.head(5).iterrows():
        name = row.get("product_name", "")
        price = money(row.get("price", 0))
        bank = safe_number(row.get("bank_transfer_price", 0))
        installment_6 = safe_number(row.get("installment_6_total", 0))
        senet_total = safe_number(row.get("senet_total_price", 0))
        senet_monthly = safe_number(row.get("senet_monthly_9", 0))

        options = []

        if bank > 0:
            options.append(f"havale ile {money(bank)}")

        if installment_6 > 0:
            options.append(f"6 taksit aylık yaklaşık {money(installment_6 / 6)}")

        if senet_total > 0:
            if senet_monthly > 0:
                options.append(f"senetli aylık yaklaşık {money(senet_monthly)}")
            else:
                options.append(f"senetli toplam {money(senet_total)}")

        if not options:
            options.append("ödeme alternatifi bilgisi sınırlı")

        lines.append(
            f"- {name} — liste fiyatı {price}. Seçenekler: {', '.join(options)}"
        )

    answer = (
        "Ödeme seçeneklerine göre uygun alternatifleri hazırladım:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "Kart limitiniz yeterli değilse havale avantajı, taksit veya senetli ödeme seçenekleriyle sepeti tamamlamayı deneyebiliriz."
    )

    return {
        "decision": "PAYMENT_HELP",
        "analysis": customer_analysis,
        "result_df": target_df,
        "answer": answer,
    }


def create_cheaper_alternative_answer(products_df, customer_analysis, current_results=None, cart_df=None):
    """
    Daha ucuz alternatif istenirse cart rescue motorunu aynı mantıkla kullanır.
    """

    rescue_result = run_cart_rescue_flow(
        products_df=products_df,
        customer_analysis=customer_analysis,
        current_results=current_results,
        cart_df=cart_df,
    )

    rescue_result["decision"] = "CHEAPER_ALTERNATIVE"

    return rescue_result


def create_product_recommendation_flow(products_df, customer_analysis):
    """
    Normal ürün öneri akışı.
    """

    query_info = convert_customer_analysis_to_query_info(customer_analysis)

    decision_result = make_decision(products_df, query_info)

    result_df = decision_result.get("result_df", pd.DataFrame())

    if (
        apply_semantic_reranking is not None
        and isinstance(result_df, pd.DataFrame)
        and not result_df.empty
    ):
        result_df = apply_semantic_reranking(
            result_df=result_df,
            user_query=customer_analysis.get("original_query", ""),
        )

        decision_result["result_df"] = result_df

    fallback_answer = decision_result.get("fallback_answer", "")

    if not fallback_answer:
        fallback_answer = create_basic_product_answer(result_df, customer_analysis)

    return {
        "decision": decision_result.get("decision", "PRODUCT_RECOMMENDATION"),
        "analysis": customer_analysis,
        "query_info": query_info,
        "result_df": result_df,
        "answer": fallback_answer,
        "fallback_answer": fallback_answer,
    }


def create_package_flow(products_df, customer_analysis):
    """
    Çeyiz / yeni ev paketi akışı.
    Paket bütçeyi aşarsa otomatik bütçe optimizasyonu yapar.
    """

    query_info = convert_customer_analysis_to_query_info(customer_analysis)

    package_result = make_package_decision(products_df, query_info)

    package_df = package_result.get("result_df", pd.DataFrame())
    package_answer = package_result.get("fallback_answer", "")
    package_query_info = package_result.get("query_info", query_info)

    budget = customer_analysis.get("budget")

    if budget and isinstance(package_df, pd.DataFrame) and not package_df.empty:
        optimization_result = run_budget_optimization(
            products_df=products_df,
            package_df=package_df,
            budget=budget,
        )

        if optimization_result.get("decision") in [
            "BUDGET_OPTIMIZED",
            "BUDGET_PARTIALLY_OPTIMIZED",
        ]:
            optimized_df = optimization_result.get("result_df", package_df)
            optimized_answer = optimization_result.get("answer", package_answer)

            package_query_info["package_total_price"] = optimization_result.get(
                "optimized_total",
                package_query_info.get("package_total_price", 0),
            )

            package_query_info["budget_optimization"] = {
                "decision": optimization_result.get("decision"),
                "original_total": optimization_result.get("original_total"),
                "optimized_total": optimization_result.get("optimized_total"),
                "budget": optimization_result.get("budget"),
                "notes": optimization_result.get("notes", []),
            }

            return {
                "decision": optimization_result.get("decision"),
                "analysis": customer_analysis,
                "query_info": package_query_info,
                "result_df": optimized_df,
                "answer": optimized_answer,
                "fallback_answer": optimized_answer,
            }

    return {
        "decision": package_result.get("decision", "PACKAGE_RECOMMENDATION"),
        "analysis": customer_analysis,
        "query_info": package_query_info,
        "result_df": package_df,
        "answer": package_answer,
        "fallback_answer": package_answer,
    }


def create_basic_product_answer(result_df, customer_analysis):
    if result_df is None or result_df.empty:
        return (
            "İsteğinizi anladım ancak ürün listesinde buna uygun net bir seçenek bulamadım. "
            "Bütçe, marka veya ödeme tercihinizi yazarsanız daha doğru alternatifler önerebilirim."
        )

    lines = []

    for _, row in result_df.head(5).iterrows():
        name = row.get("product_name", "")
        price = money(row.get("price", 0))
        stock = row.get("stock_status", "")
        category = row.get("category", "")

        lines.append(f"- {name} ({category}) — {price} ({stock})")

    return (
        "İhtiyacınıza göre öne çıkan ürünleri hazırladım:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "İsterseniz bunları en uygun fiyat, havale avantajı, taksit veya senetli ödeme seçeneğine göre yeniden sıralayabilirim."
    )


def create_order_support_answer(customer_analysis):
    return {
        "decision": "ORDER_SUPPORT",
        "analysis": customer_analysis,
        "result_df": pd.DataFrame(),
        "answer": (
            "Sipariş veya kargo durumunu kontrol edebilmem için sipariş numaranızı paylaşmanız gerekir. "
            "Örneğin NVD-1002 gibi bir sipariş numarası yazarsanız durum, kargo ve tahmini teslimat bilgisini gösterebilirim."
        ),
    }


def create_general_help_answer(customer_analysis):
    return {
        "decision": "GENERAL_HELP",
        "analysis": customer_analysis,
        "result_df": pd.DataFrame(),
        "answer": (
            "Size ürün seçimi, çeyiz paketi oluşturma, ödeme alternatifi bulma, daha uygun ürün önerme "
            "ve sipariş destek konularında yardımcı olabilirim. "
            "Örneğin '50.000 TL çeyiz paketi yap', 'kart limitim yetmedi' veya 'annem için kolay telefon öner' yazabilirsiniz."
        ),
    }


def run_personal_shopping_assistant(
    products_df,
    user_query,
    current_results=None,
    cart_df=None,
    customer_context=None,
):
    """
    Dışarıdan çağrılacak ana kişisel asistan fonksiyonu.
    Customer Profile Engine ile takip mesajlarını ve müşteri tercihlerini de yönetir.
    """

    if customer_context is None:
        customer_context = {}

    customer_profile = customer_context.get("customer_profile")

    if customer_profile is None:
        customer_profile = create_empty_customer_profile()

    customer_analysis = analyze_customer_message(user_query)

    customer_analysis = enrich_analysis_with_profile(
        customer_analysis=customer_analysis,
        profile=customer_profile,
    )
    ranking_result = run_ranking_flow(
        user_query=user_query,
        current_results=current_results,
    )

    if ranking_result is not None:
        customer_analysis["intent"] = "RANKING_REORDER"

        result = ranking_result

        updated_profile = update_customer_profile(
            profile=customer_profile,
            customer_analysis=customer_analysis,
        )

        result["customer_analysis"] = customer_analysis
        result["analysis_summary"] = explain_customer_analysis(customer_analysis)
        result["context_summary"] = build_context_summary(customer_context)
        result["cart_summary"] = build_cart_summary(cart_df)
        result["customer_profile"] = updated_profile
        result["profile_summary"] = create_profile_summary(updated_profile)

        return result
    intent = customer_analysis.get("intent")

    if intent == "CART_RESCUE":
        result = run_cart_rescue_flow(
            products_df=products_df,
            customer_analysis=customer_analysis,
            current_results=current_results,
            cart_df=cart_df,
        )

    elif intent == "PACKAGE_BUILDING":
        result = create_package_flow(
            products_df=products_df,
            customer_analysis=customer_analysis,
        )

    elif intent == "PAYMENT_ALTERNATIVE":
        result = create_payment_help_answer(
            products_df=products_df,
            customer_analysis=customer_analysis,
            current_results=current_results,
        )

    elif intent == "CHEAPER_ALTERNATIVE":
        result = create_cheaper_alternative_answer(
            products_df=products_df,
            customer_analysis=customer_analysis,
            current_results=current_results,
            cart_df=cart_df,
        )

    elif intent == "ORDER_SUPPORT":
        result = create_order_support_answer(customer_analysis)

    elif intent in ["PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON"]:
        result = create_product_recommendation_flow(
            products_df=products_df,
            customer_analysis=customer_analysis,
        )

    else:
        result = create_general_help_answer(customer_analysis)

    updated_profile = update_customer_profile(
        profile=customer_profile,
        customer_analysis=customer_analysis,
    )

    result["customer_analysis"] = customer_analysis
    result["analysis_summary"] = explain_customer_analysis(customer_analysis)
    result["context_summary"] = build_context_summary(customer_context)
    result["cart_summary"] = build_cart_summary(cart_df)
    result["customer_profile"] = updated_profile
    result["profile_summary"] = create_profile_summary(updated_profile)

    return result