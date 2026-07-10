import os
import re
import html
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# =====================================================
# STRICT PRODUCT FILTER ENGINE
# =====================================================

try:
    from src.product_filter_engine import strict_filter_products
    PRODUCT_FILTER_READY = True
except Exception as e:
    print("Product filter engine yükleme hatası:", e)
    PRODUCT_FILTER_READY = False
    strict_filter_products = None
    
# =====================================================
# TEMEL TEXT / NUMBER HELPERS
# =====================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()
    text = text.translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_number_local(value):
    try:
        if pd.isna(value):
            return 0

        if isinstance(value, str):
            value = value.replace("TL", "").replace(".", "").replace(",", ".").strip()

        return float(value)

    except Exception:
        return 0


def money_local(value):
    return f"{safe_number_local(value):,.0f} TL".replace(",", ".")


# =====================================================
# OPSİYONEL PROJE IMPORTLARI
# =====================================================

try:
    from src.decision_engine import make_decision, safe_number, money
except Exception:
    safe_number = safe_number_local
    money = money_local

    def make_decision(products_df, query_info):
        query = query_info.get("normalized_query", normalize_text(query_info.get("raw_query", "")))
        budget = safe_number(query_info.get("budget", 0))

        brands = query_info.get("brands", []) or []
        product_types = query_info.get("product_types", []) or []
        categories = query_info.get("categories", []) or []
        use_cases = query_info.get("use_cases", []) or []
        payment_priority = query_info.get("payment_priority")

        df = products_df.copy()

        def row_score(row):
            score = 0
            text = normalize_text(" ".join(str(row.get(col, "")) for col in df.columns))

            for token in query.split():
                if len(token) > 2 and token in text:
                    score += 5

            for brand in brands:
                if normalize_text(brand) in text:
                    score += 25

            for product_type in product_types:
                pt = normalize_text(product_type)

                if pt in text:
                    score += 25

                if pt == "buzdolabi" and ("buzdolabi" in text or "no frost" in text):
                    score += 30

                if pt == "camasir_makinesi" and "camasir" in text:
                    score += 30

                if pt == "bulasik_makinesi" and "bulasik" in text:
                    score += 30

                if pt == "televizyon" and ("televizyon" in text or "smart tv" in text or "tv" in text):
                    score += 30

                if pt == "laptop" and ("laptop" in text or "bilgisayar" in text or "notebook" in text):
                    score += 30

                if pt == "telefon" and ("telefon" in text or "iphone" in text or "galaxy" in text):
                    score += 30

            for category in categories:
                if normalize_text(category) in text:
                    score += 18

            for use_case in use_cases:
                uc = normalize_text(use_case)

                if uc in text:
                    score += 18

                if uc == "ceyiz" and (
                    "beyaz esya" in text
                    or "buzdolabi" in text
                    or "camasir" in text
                    or "bulasik" in text
                    or "supurge" in text
                ):
                    score += 18

                if uc == "ogrenci" and (
                    "laptop" in text
                    or "telefon" in text
                    or "tablet" in text
                    or "bilgisayar" in text
                ):
                    score += 16

            if budget and safe_number(row.get("price", 0)) <= budget:
                score += 18

            if budget and safe_number(row.get("price", 0)) > budget:
                score -= 10

            if "senet" in query and safe_number(row.get("senet_total_price", 0)) > 0:
                score += 16

            if "havale" in query and safe_number(row.get("bank_transfer_price", 0)) > 0:
                score += 16

            if "taksit" in query and safe_number(row.get("installment_6_total", 0)) > 0:
                score += 14

            if payment_priority == "lowest_monthly" and safe_number(row.get("senet_monthly_9", 0)) > 0:
                score += 20

            if payment_priority == "lowest_total" and safe_number(row.get("bank_transfer_price", 0)) > 0:
                score += 18

            if payment_priority == "card_installment" and safe_number(row.get("installment_6_total", 0)) > 0:
                score += 16

            if normalize_text(row.get("stock_status", "")) == "stokta":
                score += 6

            return score

        if not df.empty:
            df["score"] = df.apply(row_score, axis=1)
            df = df.sort_values("score", ascending=False)

            if df["score"].max() > 0:
                df = df[df["score"] > 0]

        return {
            "result_df": df.head(8),
            "query_info": query_info,
            "decision": "Karar motoru ürünleri NLP analizi, bütçe, ödeme tercihi ve stok durumuna göre sıraladı.",
            "fallback_answer": "Talebinize göre en uygun ürünleri listeledim.",
        }


try:
    from src.nlp_engine import analyze_user_query, analysis_to_short_summary
    NLP_ENGINE_READY = True

    def analyze_query(query):
        """
        Eski karar motorunun beklediği analyze_query formatını korur.
        Ama içeride yeni ultra NLP motorunu kullanır.
        """
        analysis = analyze_user_query(query)

        payments = []

        if analysis.get("payment_priority") == "lowest_monthly":
            payments.append("senet")

        if analysis.get("payment_priority") == "lowest_total":
            payments.append("havale")

        if analysis.get("payment_priority") == "card_installment":
            payments.append("taksit")

        return {
            "raw_query": query,
            "normalized_query": analysis.get("normalized_query", normalize_text(query)),
            "budget": analysis.get("budget"),
            "payments": payments,
            "intents": analysis.get("intents", []),
            "primary_intent": analysis.get("primary_intent", "general_question"),
            "brands": analysis.get("brands", []),
            "product_types": analysis.get("product_types", []),
            "categories": analysis.get("categories", []),
            "use_cases": analysis.get("use_cases", []),
            "payment_priority": analysis.get("payment_priority"),
            "order_number": analysis.get("order_number"),
            "urgency": analysis.get("urgency"),
            "sentiment": analysis.get("sentiment"),
            "confidence": analysis.get("confidence", 0),
            "nlp_analysis": analysis,
        }

except Exception as e:
    print("Ultra NLP yüklenemedi, basit NLP kullanılacak:", e)
    NLP_ENGINE_READY = False

    def analyze_user_query(query):
        q = normalize_text(query)

        nums = re.findall(r"\d+", q.replace(".", ""))
        budget = None

        if nums:
            big_nums = [int(x) for x in nums if len(x) >= 4]
            budget = max(big_nums) if big_nums else None

        intents = []

        if any(x in q for x in ["senet", "senetli", "elden odeme", "aylik"]):
            intents.append("senet")

        if any(x in q for x in ["havale", "pesin", "nakit", "en uygun"]):
            intents.append("cash_transfer")

        if any(x in q for x in ["taksit", "kart"]):
            intents.append("installment")

        if any(x in q for x in ["stok", "var mi"]):
            intents.append("stock")

        if any(x in q for x in ["siparis", "nvd", "kargo", "takip"]):
            intents.append("order_tracking")

        if not intents:
            intents = ["general_question"]

        payment_priority = None

        if any(x in q for x in ["senet", "senetli", "aylik", "elden odeme"]):
            payment_priority = "lowest_monthly"
        elif any(x in q for x in ["havale", "pesin", "nakit", "en uygun"]):
            payment_priority = "lowest_total"
        elif any(x in q for x in ["taksit", "kart"]):
            payment_priority = "card_installment"

        order_number = None
        order_match = re.search(r"NVD[-\s]?\d+", str(query).upper())

        if order_match:
            order_number = order_match.group(0).replace(" ", "-")

        brands = []
        for brand in ["beko", "vestel", "samsung", "apple", "philips", "arcelik", "lenovo", "hp", "asus"]:
            if brand in q:
                brands.append(brand)

        product_types = []

        if any(x in q for x in ["buzdolabi", "buz dolabi", "no frost"]):
            product_types.append("buzdolabi")

        if any(x in q for x in ["camasir", "camasir makinesi"]):
            product_types.append("camasir_makinesi")

        if any(x in q for x in ["bulasik", "bulasik makinesi"]):
            product_types.append("bulasik_makinesi")

        if any(x in q for x in ["tv", "televizyon", "smart tv"]):
            product_types.append("televizyon")

        if any(x in q for x in ["laptop", "bilgisayar", "notebook"]):
            product_types.append("laptop")

        if any(x in q for x in ["telefon", "iphone", "galaxy"]):
            product_types.append("telefon")

        use_cases = []

        if "ceyiz" in q or "ev diziyorum" in q:
            use_cases.append("ceyiz")

        if "ogrenci" in q:
            use_cases.append("ogrenci")

        return {
            "original_query": query,
            "normalized_query": q,
            "intents": intents,
            "primary_intent": intents[0],
            "brands": brands,
            "product_types": product_types,
            "categories": [],
            "use_cases": use_cases,
            "budget": budget,
            "payment_priority": payment_priority,
            "order_number": order_number,
            "urgency": "normal",
            "sentiment": "neutral",
            "confidence": 55,
        }

    def analysis_to_short_summary(analysis):
        return (
            f"Niyet: {analysis.get('primary_intent')} | "
            f"Bütçe: {analysis.get('budget')} | "
            f"Ödeme: {analysis.get('payment_priority')} | "
            f"Güven: %{analysis.get('confidence', 0)}"
        )

    def analyze_query(query):
        analysis = analyze_user_query(query)

        payments = []

        if analysis.get("payment_priority") == "lowest_monthly":
            payments.append("senet")

        if analysis.get("payment_priority") == "lowest_total":
            payments.append("havale")

        if analysis.get("payment_priority") == "card_installment":
            payments.append("taksit")

        return {
            "raw_query": query,
            "normalized_query": analysis.get("normalized_query", normalize_text(query)),
            "budget": analysis.get("budget"),
            "payments": payments,
            "intents": analysis.get("intents", []),
            "primary_intent": analysis.get("primary_intent", "general_question"),
            "brands": analysis.get("brands", []),
            "product_types": analysis.get("product_types", []),
            "categories": analysis.get("categories", []),
            "use_cases": analysis.get("use_cases", []),
            "payment_priority": analysis.get("payment_priority"),
            "order_number": analysis.get("order_number"),
            "confidence": analysis.get("confidence", 0),
            "nlp_analysis": analysis,
        }


try:
    from src.context_engine import (
        create_empty_customer_context,
        apply_customer_context,
        update_customer_context,
    )
except Exception:
    def create_empty_customer_context():
        return {}

    def apply_customer_context(query_info, context):
        merged = dict(context or {})
        merged.update(query_info or {})
        return merged

    def update_customer_context(context, query_info):
        new_context = dict(context or {})
        for key, value in (query_info or {}).items():
            if value not in [None, "", [], {}]:
                new_context[key] = value
        return new_context


try:
    from src.package_engine import is_package_request, make_package_decision, generate_package_text
except Exception:
    def is_package_request(query_info):
        q = normalize_text(query_info.get("raw_query", "") or query_info.get("normalized_query", ""))
        return any(word in q for word in ["ceyiz", "paket", "set", "ev diziyorum", "ev kuruyorum"])

    def make_package_decision(products_df, query_info):
        result = make_decision(products_df, query_info)
        df = result.get("result_df", pd.DataFrame()).copy()

        if not df.empty:
            df["package_group"] = df["category"]

            q = normalize_text(query_info.get("raw_query", "") or query_info.get("normalized_query", ""))

            if "ceyiz" in q:
                preferred = df[
                    df["category"].astype(str).apply(normalize_text).isin(
                        ["beyaz esya", "televizyon", "kucuk ev aleti"]
                    )
                ]

                if not preferred.empty:
                    df = preferred

        package_total = float(df.head(8)["price"].sum()) if (not df.empty and "price" in df.columns) else 0
        result["result_df"] = df.head(8)
        result["decision"] = "Paket / çeyiz talebi algılandı ve ürünler paket mantığıyla sıralandı."
        result["package_summary"] = {
            "package_type": "fallback_package",
            "requested_budget": query_info.get("budget"),
            "selected_total": package_total,
            "selected_count": len(df.head(8)) if not df.empty else 0,
            "budget_status": "Fallback paket motoru çalıştı.",
            "missing_groups": [],
        }
        return result

    def generate_package_text(decision_result):
        df = decision_result.get("result_df", pd.DataFrame())
        summary = decision_result.get("package_summary", {})

        if df is None or df.empty:
            return "Paket oluşturmak için uygun ürün bulunamadı."

        lines = ["Paket önerisi hazırlandı.", ""]

        for _, row in df.iterrows():
            group = row.get("package_group", row.get("category", "Ürün"))
            lines.append(f"- {group}: {row.get('product_name')} | {money(row.get('price', 0))} | Stok: {row.get('stock_status')}")

        lines.append("")
        lines.append(f"Paket toplamı: {money(summary.get('selected_total', df['price'].sum() if 'price' in df.columns else 0))}")

        if summary.get("requested_budget"):
            lines.append(f"Talep edilen bütçe: {money(summary.get('requested_budget'))}")
            lines.append(f"Bütçe durumu: {summary.get('budget_status', '-')}")

        if summary.get("missing_groups"):
            lines.append("Eksik kalan kategoriler: " + ", ".join(summary.get("missing_groups")))

        return "\n".join(lines)


try:
    from src.memory_engine import (
        update_user_memory,
        apply_memory_to_query,
        log_user_behavior,
        load_behavior_log,
        memory_summary_text,
        get_user_memory,
    )
    MEMORY_ENGINE_READY = True
except Exception as e:
    print("Memory engine yükleme hatası:", e)
    MEMORY_ENGINE_READY = False

    def update_user_memory(user_id, query_info, result_df=None):
        return {}

    def apply_memory_to_query(user_id, query_info):
        return query_info, {
            "active": False,
            "reason": "Memory engine aktif değil.",
            "used_fields": [],
        }

    def log_user_behavior(*args, **kwargs):
        return {}

    def load_behavior_log(limit=100):
        return pd.DataFrame()

    def memory_summary_text(user_id):
        return "Memory engine aktif değil."

    def get_user_memory(user_id):
        return {}


try:
    from src.metrics_engine import (
        calculate_ai_metrics,
        metrics_to_dataframe,
        get_recent_activity,
        get_guardrail_report,
        get_product_interest_report,
        get_payment_interest_report,
        get_top_product_report,
    )
    METRICS_ENGINE_READY = True
except Exception as e:
    print("Metrics engine yükleme hatası:", e)
    METRICS_ENGINE_READY = False

    def calculate_ai_metrics():
        return {
            "total_queries": 0,
            "customer_queries": 0,
            "store_queries": 0,
            "guardrail_events": 0,
            "strict_filter_events": 0,
            "semantic_events": 0,
            "package_events": 0,
            "top_product_types": [],
            "top_brands": [],
            "top_payments": [],
            "top_products": [],
            "top_guardrail_categories": [],
            "last_updated": "-",
        }

    def metrics_to_dataframe(metric_list, name_col="Alan", value_col="Değer"):
        return pd.DataFrame(metric_list or [], columns=[name_col, value_col])

    def get_recent_activity(limit=50):
        return pd.DataFrame()

    def get_guardrail_report():
        return pd.DataFrame()

    def get_product_interest_report():
        return pd.DataFrame()

    def get_payment_interest_report():
        return pd.DataFrame()

    def get_top_product_report():
        return pd.DataFrame()


try:
    from src.vision_engine import (
        visual_search_products,
        vision_query_text,
        detect_visual_product_type,
        build_visual_query_from_image,
    )
    VISION_ENGINE_READY = True
except Exception as e:
    print("Vision engine yükleme hatası:", e)
    VISION_ENGINE_READY = False

    def visual_search_products(products_df, description="", filename="", top_k=8, detected_types=None):
        return pd.DataFrame(), {
            "active": False,
            "reason": "Vision engine aktif değil.",
            "detected_types": detected_types or [],
            "filename": filename,
            "description": description,
        }

    def vision_query_text(description="", filename="", detected_types=None, gemini_description="", keywords=None):
        parts = []
        if detected_types:
            parts.extend(detected_types)
        if keywords:
            parts.extend(keywords)
        if gemini_description:
            parts.append(gemini_description)
        if description:
            parts.append(description)
        if filename:
            parts.append(filename)
        return " ".join(parts).strip()

    def detect_visual_product_type(description="", filename=""):
        return []

    def build_visual_query_from_image(image_bytes=None, filename="", manual_description="", manual_type_text=""):
        generated_query = " ".join([manual_type_text or "", manual_description or "", filename or ""]).strip()
        return {
            "generated_query": generated_query,
            "combined_description": generated_query,
            "detected_types": detect_visual_product_type(generated_query, filename),
            "gemini_result": {
                "success": False,
                "reason": "Vision engine aktif değil.",
                "product_type": None,
                "detected_types": [],
                "description": "",
                "keywords": [],
                "confidence": 0,
            },
        }


try:
    from src.semantic_engine import (
        apply_semantic_reranking,
        semantic_candidate_search,
        explain_semantic_match,
    )
    SEMANTIC_ENGINE_READY = True
except Exception as e:
    print("Semantic engine yükleme hatası:", e)
    SEMANTIC_ENGINE_READY = False

    def apply_semantic_reranking(result_df, user_query):
        return result_df

    def semantic_candidate_search(products_df, user_query, top_k=12, min_score=0.01):
        return products_df

    def explain_semantic_match(row, user_query):
        return "Semantic engine aktif değil."


try:
    from src.guardrail_engine import analyze_guardrail
    GUARDRAIL_READY = True
except Exception as e:
    print("Guardrail engine yükleme hatası:", e)
    GUARDRAIL_READY = False

    def analyze_guardrail(user_query, mode="customer"):
        return {
            "blocked": False,
            "risk_level": "low",
            "category": "safe",
            "reason": "Guardrail aktif değil.",
            "safe_response": None,
            "checked_at": None,
            "mode": mode,
        }


try:
    from src.response_engine import (
        generate_premium_customer_answer,
        generate_premium_store_answer,
    )
    RESPONSE_ENGINE_READY = True
except Exception as e:
    print("Response engine yükleme hatası:", e)
    RESPONSE_ENGINE_READY = False
    generate_premium_customer_answer = None
    generate_premium_store_answer = None


try:
    from src.llm_answer_engine import generate_customer_answer_with_llm
except Exception:
    def generate_customer_answer_with_llm(decision_result):
        df = decision_result.get("result_df", pd.DataFrame())

        if df.empty:
            return "Talebinize uygun ürün bulamadım. Ürün adı, bütçe veya ödeme tercihinizi biraz daha net yazabilirsiniz."

        first = df.iloc[0]

        return (
            f"Talebinize göre en güçlü seçenek {first.get('product_name')} görünüyor. "
            f"Liste fiyatı {money(first.get('price', 0))}. "
            f"Ürün kartlarında ödeme, taksit ve senetli ödeme seçeneklerini inceleyebilirsiniz."
        )


try:
    from llm_service import (
        generate_store_llm_answer,
        generate_customer_llm_answer,
        product_row_to_dict,
        is_llm_ready,
    )
    LLM_READY = is_llm_ready()

except Exception as e:
    print("LLM servis yükleme hatası:", e)
    generate_store_llm_answer = None
    generate_customer_llm_answer = None
    product_row_to_dict = None
    LLM_READY = False


try:
    from src.llm_provider_router import call_best_available_llm
except Exception:
    call_best_available_llm = None


# =====================================================
# SAYFA AYARI
# =====================================================

st.set_page_config(
    page_title="Nevade AI Commerce Hub",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =====================================================
# EXTERNAL CSS LOADER
# =====================================================

def load_external_css(css_path="assets/app_design.css"):
    css_file = Path(css_path)
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS dosyası bulunamadı: {css_path}")


load_external_css()



# =====================================================
# SESSION STATE
# =====================================================

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


init_state("logged_in", False)
init_state("user_email", "")
init_state("user_role", "")
init_state("page", "dashboard")
init_state("cart", [])
init_state("cart_notice", "")
init_state("compare_items", [])
init_state("customer_messages", [])
init_state("store_messages", [])
init_state("last_results", pd.DataFrame())
init_state("last_query_info", {})
init_state("last_decision", "")
init_state("last_filter_info", {})
init_state("last_semantic_info", {})
init_state("last_package_summary", {})
init_state("last_guardrail_info", {})
init_state("last_memory_info", {})
init_state("last_vision_info", {})
init_state("last_uploaded_image_name", "")
init_state("last_fallback_answer", "")
init_state("support_result", None)
init_state("quick_action_history", [])
init_state("customer_context", create_empty_customer_context())
init_state("login_email", "admin@nevade.com")
init_state("login_password", "1234")

init_state(
    "orders",
    [
        {
            "order_id": "NVD-1001",
            "customer_name": "Ayşe Yılmaz",
            "product_name": "Apple iPhone 15 Telefon",
            "status": "Kargoda",
            "payment_type": "Havale",
            "cargo_company": "Yurtiçi Kargo",
            "tracking_no": "TRK123456",
            "estimated_delivery": "20 Haziran 2026",
            "address": "İstanbul / Bakırköy",
            "store": "Bakırköy Mağazası",
            "created_at": "18 Haziran 2026",
            "total_price": 51499,
            "items": [
                {
                    "product_name": "Apple iPhone 15 Telefon",
                    "price": 51499,
                    "quantity": 1,
                    "line_total": 51499,
                }
            ],
        },
        {
            "order_id": "NVD-1002",
            "customer_name": "Mehmet Kaya",
            "product_name": "Beko No Frost Buzdolabı 500 L",
            "status": "Hazırlanıyor",
            "payment_type": "Senetli",
            "cargo_company": "Horoz Lojistik",
            "tracking_no": "HRZ987654",
            "estimated_delivery": "22 Haziran 2026",
            "address": "İstanbul / Merter",
            "store": "Merter Mağazası",
            "created_at": "19 Haziran 2026",
            "total_price": 21900,
            "items": [
                {
                    "product_name": "Beko No Frost Buzdolabı 500 L",
                    "price": 21900,
                    "quantity": 1,
                    "line_total": 21900,
                }
            ],
        },
    ],
)


USERS = {
    "admin@nevade.com": {"password": "1234", "role": "admin", "name": "Sistem Yöneticisi"},
    "magaza@nevade.com": {"password": "1234", "role": "store", "name": "Mağaza Personeli"},
    "musteri@nevade.com": {"password": "1234", "role": "customer", "name": "Değerli Müşterimiz"},
}


# =====================================================
# GENEL HELPERS
# =====================================================

def clean_str(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def escape_html_text(text):
    return html.escape("" if text is None else str(text))


def text_to_html(text):
    return escape_html_text(text).replace("\n", "<br>")


def render_iframe_html(html_code, height=680):
    """Ham HTML'i güncel Streamlit API'siyle gösterir.

    st.iframe bir URL içindir; ham HTML metni için resmi karşılık st.html'dir.
    """
    st.html(html_code)


def md_block(html_text, **kwargs):
    """
    Çok satırlı HTML bloklarını st.markdown ile gönderirken satır başındaki
    girintileri temizler. Girinti bırakılırsa Streamlit'in markdown ön işleyicisi
    4+ boşluklu satırları kod bloğu sanıp HTML'i kaçırıyor (escape ediyor) —
    tam olarak giriş ekranındaki boş/ham kod kutusu hatasının sebebi buydu.
    """
    cleaned_lines = [line.strip() for line in html_text.strip("\n").splitlines()]
    st.markdown("\n".join(cleaned_lines), unsafe_allow_html=True)


def go_page(page):
    st.session_state.page = page
    st.rerun()


# =====================================================
# DATA
# =====================================================

def demo_products():
    return pd.DataFrame(
        [
            {
                "product_id": "P001",
                "product_name": "Beko No Frost Buzdolabı 500 L",
                "category": "Beyaz Eşya",
                "brand": "Beko",
                "price": 18500,
                "cash_price": 17900,
                "bank_transfer_price": 17650,
                "card_price": 18500,
                "installment_6_total": 19500,
                "senet_total_price": 21900,
                "senet_monthly_9": 2433,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Çeyiz, ev, aile kullanımı",
                "features": "No Frost, geniş hacim, sessiz çalışma",
                "description": "Çeyiz ve ev kullanımı için uygun geniş hacimli buzdolabı.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
            {
                "product_id": "P002",
                "product_name": "Vestel 7 kg Çamaşır Makinesi",
                "category": "Beyaz Eşya",
                "brand": "Vestel",
                "price": 15120,
                "cash_price": 14800,
                "bank_transfer_price": 14560,
                "card_price": 15120,
                "installment_6_total": 15850,
                "senet_total_price": 17779,
                "senet_monthly_9": 1975,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Çeyiz, ev, günlük kullanım",
                "features": "Enerji verimli, 7 kg kapasite",
                "description": "Çeyiz paketi için ekonomik çamaşır makinesi seçeneği.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
            {
                "product_id": "P003",
                "product_name": "Samsung 50 inç Akıllı Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "price": 12900,
                "cash_price": 12650,
                "bank_transfer_price": 12490,
                "card_price": 12900,
                "installment_6_total": 13700,
                "senet_total_price": 15900,
                "senet_monthly_9": 1766,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Salon, film, dizi, çeyiz",
                "features": "Smart TV, 4K görüntü, geniş ekran",
                "description": "Çeyiz ve salon kullanımı için uygun akıllı televizyon.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
            {
                "product_id": "P004",
                "product_name": "Philips Elektrikli Süpürge",
                "category": "Küçük Ev Aleti",
                "brand": "Philips",
                "price": 3999,
                "cash_price": 3899,
                "bank_transfer_price": 3799,
                "card_price": 3999,
                "installment_6_total": 4299,
                "senet_total_price": 4999,
                "senet_monthly_9": 555,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Çeyiz, ev temizliği, günlük kullanım",
                "features": "Güçlü emiş, hafif gövde",
                "description": "Çeyiz paketi için tamamlayıcı süpürge seçeneği.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
            {
                "product_id": "P005",
                "product_name": "Lenovo IdeaPad Slim 5 Laptop",
                "category": "Bilgisayar",
                "brand": "Lenovo",
                "price": 24900,
                "cash_price": 24300,
                "bank_transfer_price": 23950,
                "card_price": 24900,
                "installment_6_total": 26300,
                "senet_total_price": 29700,
                "senet_monthly_9": 3300,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Öğrenci, ofis, günlük kullanım",
                "features": "16 GB RAM, 512 GB SSD, hafif kasa",
                "description": "Öğrenci ve ofis kullanımı için dengeli fiyat performans laptop.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
            {
                "product_id": "P006",
                "product_name": "Samsung Galaxy A55 256 GB Telefon",
                "category": "Cep Telefonu",
                "brand": "Samsung",
                "price": 19900,
                "cash_price": 19300,
                "bank_transfer_price": 18950,
                "card_price": 19900,
                "installment_6_total": 21100,
                "senet_total_price": 23400,
                "senet_monthly_9": 2600,
                "stock_status": "Stokta",
                "payment_options": "Kart, Havale, Taksit, Senet",
                "use_case": "Günlük kullanım, sosyal medya, kamera",
                "features": "256 GB hafıza, AMOLED ekran, güçlü batarya",
                "description": "Günlük kullanım ve sosyal medya için uygun güçlü telefon.",
                "product_link": "https://www.nevade.com/",
                "image_link": "",
            },
        ]
    )


@st.cache_data(show_spinner=False)
def load_products():
    path = "data/products.csv"

    if os.path.exists(path):
        try:
            df = pd.read_csv(path)

            if not df.empty:
                return df

        except Exception as e:
            print("CSV yükleme hatası:", e)

    return demo_products()


def prepare_products(df):
    df = df.copy()

    numeric_cols = [
        "price",
        "cash_price",
        "bank_transfer_price",
        "card_price",
        "installment_6_total",
        "senet_total_price",
        "senet_monthly_9",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = df[col].apply(safe_number)

    text_cols = [
        "product_id",
        "product_name",
        "category",
        "brand",
        "stock_status",
        "payment_options",
        "use_case",
        "features",
        "description",
        "product_link",
        "image_link",
        "warranty",
    ]

    for col in text_cols:
        if col not in df.columns:
            df[col] = ""

    df["search_text"] = (
        df["product_name"].astype(str)
        + " "
        + df["category"].astype(str)
        + " "
        + df["brand"].astype(str)
        + " "
        + df["description"].astype(str)
        + " "
        + df["features"].astype(str)
        + " "
        + df["payment_options"].astype(str)
        + " "
        + df["use_case"].astype(str)
    ).apply(normalize_text)

    return df


def save_products(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/products.csv", index=False)


# =====================================================
# SEPET / SİPARİŞ
# =====================================================

def add_product_to_cart(row):
    product = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    product_id = str(product.get("product_id", "")) or f"NO_ID_{abs(hash(product.get('product_name', 'urun')))}"

    for item in st.session_state.cart:
        if str(item.get("product_id")) == product_id:
            item["quantity"] = int(item.get("quantity", 1)) + 1
            st.session_state.cart_notice = f"{product.get('product_name')} sepetteki adedi artırıldı."
            return

    product["quantity"] = 1
    st.session_state.cart.append(product)
    st.session_state.cart_notice = f"{product.get('product_name')} sepete eklendi."


def get_cart_total():
    return sum(
        safe_number(item.get("price", 0)) * int(item.get("quantity", 1))
        for item in st.session_state.cart
    )


def get_last_order():
    if not st.session_state.orders:
        return None

    return st.session_state.orders[-1]


def find_order(query):
    q = normalize_text(query)

    for order in st.session_state.orders:
        for key in ["order_id", "customer_name", "product_name", "tracking_no"]:
            value = normalize_text(order.get(key, ""))

            if value and value in q:
                return order

    return None


def create_order_from_cart(customer_name, address, payment_type, store_name):
    if not st.session_state.cart:
        return None

    next_no = 1000

    for order in st.session_state.orders:
        match = re.search(r"NVD-(\d+)", str(order.get("order_id", "")))

        if match:
            next_no = max(next_no, int(match.group(1)))

    now = datetime.now()
    items = []

    for item in st.session_state.cart:
        quantity = int(item.get("quantity", 1))
        price = safe_number(item.get("price", 0))

        items.append(
            {
                "product_id": item.get("product_id", ""),
                "product_name": item.get("product_name", ""),
                "price": price,
                "quantity": quantity,
                "line_total": price * quantity,
            }
        )

    total = sum(item["line_total"] for item in items)

    if len(items) == 1:
        product_name = items[0]["product_name"]
    else:
        product_name = f"{items[0]['product_name']} + {len(items) - 1} ürün"

    order = {
        "order_id": f"NVD-{next_no + 1}",
        "customer_name": customer_name or "Demo Müşteri",
        "product_name": product_name,
        "status": "Hazırlanıyor",
        "payment_type": payment_type,
        "cargo_company": "Horoz Lojistik" if total > 15000 else "Yurtiçi Kargo",
        "tracking_no": f"TRK{now.strftime('%H%M%S')}",
        "estimated_delivery": (now + timedelta(days=3)).strftime("%d.%m.%Y"),
        "address": address,
        "store": store_name,
        "created_at": now.strftime("%d.%m.%Y %H:%M"),
        "total_price": total,
        "items": items,
    }

    st.session_state.orders.append(order)
    st.session_state.cart = []

    return order


def order_text(order):
    if not order:
        return "Siparişinizi bulabilmem için sipariş numarası gerekir. Örnek: NVD-1001"

    return (
        f"Sipariş No: {order.get('order_id')}\n"
        f"Durum: {order.get('status')}\n"
        f"Ürün: {order.get('product_name')}\n"
        f"Müşteri: {order.get('customer_name')}\n"
        f"Ödeme: {order.get('payment_type')}\n"
        f"Kargo: {order.get('cargo_company')} / {order.get('tracking_no')}\n"
        f"Tahmini Teslimat: {order.get('estimated_delivery')}\n"
        f"Adres: {order.get('address')}\n"
        f"Toplam: {money(order.get('total_price', 0))}"
    )


# =====================================================
# AI FONKSİYONLARI
# =====================================================

def is_clean_ai_answer(answer):
    """
    LLM cevabı müşteriye/personeline gösterilmeye uygun mu kontrol eder.
    Prompt sızıntısı, İngilizce/Çince karışması, çok kısa cevap gibi durumları engeller.
    """

    if not answer:
        return False

    raw = str(answer).strip()
    text = normalize_text(raw)

    if len(raw) < 80:
        return False

    bad_patterns = [
        "prompt",
        "system message",
        "sistem mesaji",
        "kurallar",
        "cevap formati",
        "as an ai",
        "i cannot",
        "i can't",
        "json",
        "```",
        "customer relationship",
        "management",
        "business manifest",
        "travel manifest",
        "nevada",
        "以下",
        "使用",
        "doğrulanmış ürün verisi",
        "dogrulanmis urun verisi",
    ]

    for pattern in bad_patterns:
        if normalize_text(pattern) in text or pattern in raw:
            return False

    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", raw):
        return False

    turkish_signals = [
        "müşteri", "musteri",
        "ürün", "urun",
        "ödeme", "odeme",
        "stok",
        "fiyat",
        "taksit",
        "senet",
        "havale",
        "personel",
        "sipariş", "siparis",
        "kargo",
    ]

    hit = sum(1 for word in turkish_signals if normalize_text(word) in text)

    return hit >= 2


def get_payment_values(row):
    price = safe_number(row.get("price", 0))
    cash = safe_number(row.get("cash_price", 0))
    bank = safe_number(row.get("bank_transfer_price", 0))
    card = safe_number(row.get("card_price", 0))
    installment_6 = safe_number(row.get("installment_6_total", 0))
    senet_total = safe_number(row.get("senet_total_price", 0))
    senet_monthly = safe_number(row.get("senet_monthly_9", 0))

    options = [
        ("Peşin", cash),
        ("Havale", bank),
        ("Kart", card),
        ("6 Taksit", installment_6),
        ("Senetli", senet_total),
    ]

    valid_options = [item for item in options if item[1] > 0]

    return {
        "price": price,
        "cash": cash,
        "bank": bank,
        "card": card,
        "installment_6": installment_6,
        "installment_6_monthly": installment_6 / 6 if installment_6 else 0,
        "senet_total": senet_total,
        "senet_monthly": senet_monthly,
        "best_option": min(valid_options, key=lambda x: x[1]) if valid_options else None,
    }


def detect_store_intent(query):
    q = normalize_text(query)
    intents = []

    checks = {
        "senet_uygunluk": ["senet", "elden odeme", "aylik"],
        "odeme": ["odeme", "havale", "kart", "taksit", "pesin", "nakit"],
        "stok": ["stok", "var mi", "mevcut"],
        "kargo": ["kargo", "teslimat"],
        "siparis": ["siparis", "nvd", "takip"],
        "fatura": ["fatura"],
        "iade": ["iade", "iptal"],
    }

    for intent, words in checks.items():
        if any(word in q for word in words):
            intents.append(intent)

    return intents or ["genel"]


def product_context(row):
    values = get_payment_values(row)
    best_name = ""
    best_value = 0

    if values["best_option"]:
        best_name, best_value = values["best_option"]

    return {
        "product_name": clean_str(row.get("product_name")),
        "brand": clean_str(row.get("brand")),
        "category": clean_str(row.get("category")),
        "stock_status": clean_str(row.get("stock_status")),
        "list_price": money(row.get("price", 0)),
        "bank_transfer_price": money(row.get("bank_transfer_price", 0)),
        "installment_6_total": money(row.get("installment_6_total", 0)),
        "installment_6_monthly": money(values["installment_6_monthly"]),
        "senet_total_price": money(row.get("senet_total_price", 0)),
        "senet_monthly_9": money(row.get("senet_monthly_9", 0)),
        "best_payment_name": best_name,
        "best_payment_value": money(best_value),
        "features": clean_str(row.get("features")),
        "description": clean_str(row.get("description")),
    }


def get_product_dict_ultra(row):
    """
    Ürün satırını hem eski app hem llm_service için güvenli dict formatına çevirir.
    """

    if row is None:
        return {}

    try:
        if product_row_to_dict:
            converted = product_row_to_dict(row)
            if converted:
                return converted
    except Exception:
        pass

    return {
        "urun_adi": clean_str(row.get("product_name")),
        "kategori": clean_str(row.get("category")),
        "marka": clean_str(row.get("brand")),
        "liste_fiyati": money(row.get("price", 0)),
        "pesin_fiyati": money(row.get("cash_price", 0)),
        "havale_fiyati": money(row.get("bank_transfer_price", 0)),
        "kart_fiyati": money(row.get("card_price", 0)),
        "6_taksit_toplam": money(row.get("installment_6_total", 0)),
        "6_taksit_aylik": money(safe_number(row.get("installment_6_total", 0)) / 6),
        "senetli_toplam": money(row.get("senet_total_price", 0)),
        "senetli_aylik": money(row.get("senet_monthly_9", 0)),
        "stok": clean_str(row.get("stock_status")),
        "garanti": clean_str(row.get("warranty", "")),
        "aciklama": clean_str(row.get("description")),
        "ozellikler": clean_str(row.get("features")),
        "kullanim_amaci": clean_str(row.get("use_case")),
        "odeme_secenekleri": clean_str(row.get("payment_options")),
    }


def build_enriched_intents(question, query_info):
    """
    LLM'e düz intent listesi değil, zengin NLP bağlamı gönderir.
    """

    analysis = query_info.get("nlp_analysis")

    if not analysis:
        analysis = analyze_user_query(question)

    return {
        "summary": analysis_to_short_summary(analysis),
        "intents": analysis.get("intents", []),
        "primary_intent": analysis.get("primary_intent", "general_question"),
        "brands": analysis.get("brands", []),
        "product_types": analysis.get("product_types", []),
        "categories": analysis.get("categories", []),
        "use_cases": analysis.get("use_cases", []),
        "budget": analysis.get("budget"),
        "payment_priority": analysis.get("payment_priority"),
        "order_number": analysis.get("order_number"),
        "urgency": analysis.get("urgency"),
        "sentiment": analysis.get("sentiment"),
        "confidence": analysis.get("confidence", 0),
        "legacy_payments": query_info.get("payments", []),
    }


def create_customer_fallback_answer(decision_result):
    """
    Müşteri AI için LLM çalışmazsa temiz cevap üretir.
    """

    if is_package_request(decision_result.get("query_info", {})):
        try:
            package_text = generate_package_text(decision_result)

            if package_text:
                return (
                    package_text
                    + "\n\nBu paketi sepete ekleyebilir veya bütçeye göre daha ekonomik / daha üst segment alternatiflerle yeniden düzenleyebilirsiniz."
                )
        except Exception as e:
            print("Package text hata:", e)

    if RESPONSE_ENGINE_READY and generate_premium_customer_answer:
        try:
            user_query = decision_result.get("query_info", {}).get("raw_query", "")
            return generate_premium_customer_answer(decision_result, user_query)
        except Exception as e:
            print("Premium customer response hata:", e)

    df = decision_result.get("result_df", pd.DataFrame())
    query_info = decision_result.get("query_info", {})
    analysis = query_info.get("nlp_analysis", {})

    if df is None or df.empty:
        return (
            "Talebinize uygun ürünü netleştiremedim. "
            "Ürün türü, marka, bütçe veya ödeme tercihinizi biraz daha detaylı yazabilirsiniz."
        )

    first = df.iloc[0]
    product = get_product_dict_ultra(first)

    payment_priority = analysis.get("payment_priority") or query_info.get("payment_priority")

    if payment_priority == "lowest_total":
        payment_text = f"Toplamda avantajlı ödeme için havale fiyatı öne çıkıyor: {product.get('havale_fiyati')}."
    elif payment_priority == "lowest_monthly":
        payment_text = (
            f"Aylık düşük ödeme için senetli ödeme seçeneği değerlendirilebilir. "
            f"Senetli toplam: {product.get('senetli_toplam')}, aylık: {product.get('senetli_aylik')}."
        )
    elif payment_priority == "card_installment":
        payment_text = f"Kredi kartı ile 6 taksit toplamı: {product.get('6_taksit_toplam')}."
    else:
        payment_text = (
            f"Havale, kart taksit ve senetli ödeme seçenekleri müşterinin tercihine göre değerlendirilebilir. "
            f"Havale: {product.get('havale_fiyati')}, senetli aylık: {product.get('senetli_aylik')}."
        )

    return (
        f"Önerim:\n"
        f"{product.get('urun_adi')} talebinize en uygun seçeneklerden biri olarak görünüyor.\n\n"
        f"Neden uygun?\n"
        f"{product.get('aciklama') or 'Ürün özellikleri ve ödeme seçenekleri talebinizle uyumlu görünüyor.'} "
        f"Stok durumu: {product.get('stok')}.\n\n"
        f"Ödeme avantajı:\n"
        f"Liste fiyatı: {product.get('liste_fiyati')}. {payment_text}\n\n"
        f"Sonraki adım:\n"
        f"Ürünü sepete ekleyebilir, ödeme seçeneğini karşılaştırabilir veya mağaza personelinden stok teyidi alabilirsiniz."
    )


def store_fallback(question, row):
    if RESPONSE_ENGINE_READY and generate_premium_store_answer:
        try:
            decision_result = {
                "result_df": pd.DataFrame([row]),
                "query_info": analyze_query(question),
                "filter_info": st.session_state.get("last_filter_info", {}),
            }
            return generate_premium_store_answer(decision_result, question)
        except Exception as e:
            print("Premium store response hata:", e)

    intents = detect_store_intent(question)
    values = get_payment_values(row)

    if values["best_option"]:
        best_sentence = f"Toplam tutar açısından en avantajlı seçenek: {values['best_option'][0]} - {money(values['best_option'][1])}."
    else:
        best_sentence = "En avantajlı ödeme seçeneği hesaplanamadı."

    return (
        f"Müşteri talebi:\n"
        f"Müşteri {', '.join(intents)} konusunda bilgi istiyor.\n\n"
        f"Önerilen ürün:\n"
        f"- Ürün: {row.get('product_name')}\n"
        f"- Marka: {row.get('brand')}\n"
        f"- Kategori: {row.get('category')}\n"
        f"- Stok: {row.get('stock_status')}\n"
        f"- Liste fiyatı: {money(row.get('price', 0))}\n\n"
        f"Ödeme değerlendirmesi:\n"
        f"- Havale: {money(row.get('bank_transfer_price', 0))}\n"
        f"- 6 taksit toplam: {money(row.get('installment_6_total', 0))} / aylık yaklaşık {money(values['installment_6_monthly'])}\n"
        f"- Senetli toplam: {money(row.get('senet_total_price', 0))} / aylık yaklaşık {money(row.get('senet_monthly_9', 0))}\n\n"
        f"En iyi öneri:\n"
        f"{best_sentence}\n\n"
        f"Müşteriye söylenecek hazır cevap:\n"
        f"“{row.get('product_name')} stokta görünüyor. Toplamda en uygun ödeme için havale seçeneği, aylık ödeme kolaylığı için senetli ödeme seçeneği değerlendirilebilir.”\n\n"
        f"Personel aksiyonu:\n"
        f"- Stok ve ödeme koşullarını son kez teyit edin.\n"
        f"- Müşteri toplam uygun fiyat istiyorsa havaleyi, aylık düşük ödeme istiyorsa senetli seçeneği anlatın."
    )


def store_product_answer(products_df, question):
    """
    Mağaza AI ultra akış:
    1. Guardrail kontrolü yapılır.
    2. Sipariş sorgusu kontrol edilir.
    3. Ultra NLP analizi yapılır.
    4. Strict ürün filtresi kategori karışmasını engeller.
    5. Semantic search aday havuzunu anlam bazlı iyileştirir.
    6. Karar motoru doğru ürünü seçer.
    7. LLM yalnızca doğrulanmış veriden cevap üretir.
    """

    guardrail_info = analyze_guardrail(question, mode="store")
    st.session_state.last_guardrail_info = guardrail_info

    if guardrail_info.get("blocked"):
        return (
            guardrail_info.get("safe_response")
            or "Bu talep güvenlik nedeniyle işleme alınmadı. Ürün, ödeme, stok veya sipariş bilgisi konusunda yardımcı olabilirim."
        )

    competitor_note = None
    if guardrail_info.get("category") in ["competitor_comparison", "rude_language"]:
        competitor_note = guardrail_info.get("safe_response")

    order = find_order(question)

    if order:
        answer = order_text(order)
        if competitor_note:
            return competitor_note + "\n\n" + answer
        return answer

    user_id = st.session_state.user_email or "store_user"

    query_info = analyze_query(question)
    query_info, memory_info = apply_memory_to_query(user_id, query_info)
    st.session_state.last_memory_info = memory_info

    analysis = query_info.get("nlp_analysis", analyze_user_query(question))

    if PRODUCT_FILTER_READY and strict_filter_products:
        filtered_products_df, filter_info = strict_filter_products(products_df, question)
    else:
        filtered_products_df = products_df
        filter_info = {
            "active": False,
            "reason": "Product filter engine aktif değil.",
            "detected_types": [],
            "package_query": False,
        }

    semantic_info = {
        "active": False,
        "reason": "Semantic engine aktif değil.",
        "top_score": 0,
    }

    semantic_products_df = filtered_products_df

    if SEMANTIC_ENGINE_READY and filtered_products_df is not None and not filtered_products_df.empty:
        try:
            if not filter_info.get("package_query"):
                semantic_products_df = semantic_candidate_search(
                    filtered_products_df,
                    question,
                    top_k=12,
                    min_score=0.01,
                )

                top_score = 0

                if "semantic_score" in semantic_products_df.columns and not semantic_products_df.empty:
                    top_score = float(semantic_products_df["semantic_score"].max())

                semantic_info = {
                    "active": True,
                    "reason": "Semantic candidate search çalıştı.",
                    "top_score": round(top_score, 4),
                }
            else:
                semantic_info = {
                    "active": False,
                    "reason": "Paket / çeyiz sorgusunda kategori çeşitliliği için semantic ön eleme kapatıldı.",
                    "top_score": 0,
                }
        except Exception as e:
            print("Semantic candidate search hata:", e)

    enriched_intents = build_enriched_intents(question, query_info)
    enriched_intents["strict_filter"] = filter_info
    enriched_intents["semantic_search"] = semantic_info
    enriched_intents["guardrail"] = guardrail_info

    query_info["strict_filter"] = filter_info
    query_info["semantic_search"] = semantic_info
    query_info["guardrail"] = guardrail_info

    if is_package_request(query_info):
        decision_result = make_package_decision(semantic_products_df, query_info)
    else:
        decision_result = make_decision(semantic_products_df, query_info)

    st.session_state.last_package_summary = decision_result.get("package_summary", {})
    result_df = decision_result.get("result_df", pd.DataFrame())

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        result_df = apply_semantic_reranking(result_df, question)

    decision_result["result_df"] = result_df
    decision_result["query_info"] = query_info
    decision_result["filter_info"] = filter_info
    decision_result["semantic_info"] = semantic_info
    decision_result["guardrail_info"] = guardrail_info

    if filter_info.get("reason"):
        old_decision = clean_str(decision_result.get("decision", ""))
        decision_result["decision"] = f"{filter_info.get('reason')} {semantic_info.get('reason', '')} {old_decision}".strip()

    st.session_state.last_filter_info = filter_info
    st.session_state.last_semantic_info = semantic_info

    if result_df is None or result_df.empty:
        try:
            update_user_memory(user_id, query_info, result_df)
            log_user_behavior(
                user_id=user_id,
                role="store",
                query=question,
                query_info=query_info,
                result_df=result_df,
                guardrail_info=guardrail_info,
                filter_info=filter_info,
                semantic_info=semantic_info,
                package_summary=decision_result.get("package_summary", {}),
            )
        except Exception as e:
            print("Memory/log store empty hata:", e)

        if filter_info.get("active"):
            answer = (
                "Müşteri net bir ürün tipi belirtti ancak katalogda bu ürün tipine uygun ürün bulunamadı. "
                f"Filtre bilgisi: {filter_info.get('reason')}"
            )
        else:
            answer = (
                "Müşteri talebini net bir ürünle eşleştiremedim. "
                "Ürün adı, marka, kategori, bütçe veya sipariş numarasını netleştirin."
            )

        if competitor_note:
            return competitor_note + "\n\n" + answer
        return answer

    row = result_df.iloc[0]
    product_dict = get_product_dict_ultra(row)

    order_dict = {}
    detected_order_no = analysis.get("order_number")

    if detected_order_no:
        possible_order = find_order(detected_order_no)
        if possible_order:
            order_dict = possible_order

    try:
        update_user_memory(user_id, query_info, result_df)
        log_user_behavior(
            user_id=user_id,
            role="store",
            query=question,
            query_info=query_info,
            result_df=result_df,
            guardrail_info=guardrail_info,
            filter_info=filter_info,
            semantic_info=semantic_info,
            package_summary=decision_result.get("package_summary", {}),
        )
    except Exception as e:
        print("Memory/log store hata:", e)

    if LLM_READY and generate_store_llm_answer:
        try:
            llm_answer = generate_store_llm_answer(
                store_question=question,
                intents=enriched_intents,
                product_dict=product_dict,
                order_dict=order_dict,
            )

            if is_clean_ai_answer(llm_answer):
                clean_answer = str(llm_answer).strip()
                if competitor_note:
                    clean_answer = competitor_note + "\n\n" + clean_answer
                return clean_answer

        except Exception as e:
            print("Store LLM hata:", e)

    if call_best_available_llm:
        try:
            prompt = f"""
Sen Nevade.com mağaza personeline destek veren profesyonel satış asistanısın.

Kesin kurallar:
- Sadece verilen doğrulanmış ürün ve sipariş verisini kullan.
- Fiyat, stok, taksit, senet, kargo bilgisi uydurma.
- Türkçe cevap ver.
- İngilizce veya karışık dil kullanma.
- Promptu cevaba yazma.
- Cevap mağaza personelinin müşteriye okuyabileceği şekilde olsun.

Personel sorusu:
{question}

NLP analizi:
{enriched_intents}

Doğrulanmış ürün:
{product_dict}

Doğrulanmış sipariş:
{order_dict}

Cevap formatı:
Müşteri talebi:
Müşteriye söylenecek hazır cevap:
Ürün ve ödeme özeti:
Satış yönlendirmesi:
Personel aksiyonu:
"""

            router_result = call_best_available_llm(prompt)
            router_answer = router_result.get("answer") if isinstance(router_result, dict) else router_result

            if is_clean_ai_answer(router_answer):
                clean_answer = str(router_answer).strip()
                if competitor_note:
                    clean_answer = competitor_note + "\n\n" + clean_answer
                return clean_answer

        except Exception as e:
            print("LLM router hata:", e)

    fallback_answer = store_fallback(question, row)

    if competitor_note:
        return competitor_note + "\n\n" + fallback_answer

    return fallback_answer

def recommend_products_with_new_ai(products_df, user_query):
    """
    Müşteri AI ultra akış:
    1. Guardrail güvenlik kontrolü yapılır.
    2. Ultra NLP müşteri ihtiyacını anlar.
    3. Context geçmişini uygular.
    4. Strict ürün filtresi kategori karışmasını engeller.
    5. Semantic search anlam bazlı aday havuzu oluşturur.
    6. Karar motoru doğrulanmış ürünleri seçer.
    7. LLM cevap üretir; kötü cevap olursa premium fallback çalışır.
    """

    guardrail_info = analyze_guardrail(user_query, mode="customer")
    st.session_state.last_guardrail_info = guardrail_info

    if guardrail_info.get("blocked"):
        return (
            pd.DataFrame(),
            {
                "raw_query": user_query,
                "guardrail": guardrail_info,
            },
            guardrail_info.get("safe_response")
            or "Bu talebe güvenli şekilde yanıt veremiyorum. Ürün, ödeme, stok veya sipariş bilgisi konusunda yardımcı olabilirim.",
        )

    competitor_note = None
    if guardrail_info.get("category") in ["competitor_comparison", "rude_language"]:
        competitor_note = guardrail_info.get("safe_response")

    user_id = st.session_state.user_email or "anonymous"

    query_info = analyze_query(user_query)

    query_info, memory_info = apply_memory_to_query(user_id, query_info)
    st.session_state.last_memory_info = memory_info

    query_info = apply_customer_context(
        query_info,
        st.session_state.customer_context,
    )

    context_product_types = query_info.get("product_types", []) or []
    context_brands = query_info.get("brands", []) or []

    filter_question = " ".join(
        [
            user_query,
            " ".join([str(x) for x in context_product_types]),
            " ".join([str(x) for x in context_brands]),
        ]
    )

    if PRODUCT_FILTER_READY and strict_filter_products:
        filtered_products_df, filter_info = strict_filter_products(products_df, filter_question)
    else:
        filtered_products_df = products_df
        filter_info = {
            "active": False,
            "reason": "Product filter engine aktif değil.",
            "detected_types": [],
            "package_query": False,
        }

    semantic_info = {
        "active": False,
        "reason": "Semantic engine aktif değil.",
        "top_score": 0,
    }

    semantic_products_df = filtered_products_df

    if SEMANTIC_ENGINE_READY and filtered_products_df is not None and not filtered_products_df.empty:
        try:
            if not filter_info.get("package_query"):
                semantic_products_df = semantic_candidate_search(
                    filtered_products_df,
                    user_query,
                    top_k=12,
                    min_score=0.01,
                )

                top_score = 0

                if "semantic_score" in semantic_products_df.columns and not semantic_products_df.empty:
                    top_score = float(semantic_products_df["semantic_score"].max())

                semantic_info = {
                    "active": True,
                    "reason": "Semantic candidate search çalıştı.",
                    "top_score": round(top_score, 4),
                }
            else:
                semantic_info = {
                    "active": False,
                    "reason": "Paket / çeyiz sorgusunda kategori çeşitliliği için semantic ön eleme kapatıldı.",
                    "top_score": 0,
                }
        except Exception as e:
            print("Semantic candidate search hata:", e)

    query_info["strict_filter"] = filter_info
    query_info["semantic_search"] = semantic_info
    query_info["guardrail"] = guardrail_info

    if is_package_request(query_info):
        decision_result = make_package_decision(semantic_products_df, query_info)
    else:
        decision_result = make_decision(semantic_products_df, query_info)

    st.session_state.last_package_summary = decision_result.get("package_summary", {})
    result_df = decision_result.get("result_df", pd.DataFrame())

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        result_df = apply_semantic_reranking(result_df, user_query)

    decision_result["result_df"] = result_df
    decision_result["query_info"] = decision_result.get("query_info", query_info)
    decision_result["filter_info"] = filter_info
    decision_result["semantic_info"] = semantic_info
    decision_result["guardrail_info"] = guardrail_info

    if filter_info.get("reason"):
        old_decision = clean_str(decision_result.get("decision", ""))
        decision_result["decision"] = f"{filter_info.get('reason')} {semantic_info.get('reason', '')} {old_decision}".strip()

    final_answer = None

    if LLM_READY and generate_customer_llm_answer and isinstance(result_df, pd.DataFrame) and not result_df.empty:
        try:
            first_product = result_df.iloc[0]
            product_dict = get_product_dict_ultra(first_product)

            final_answer = generate_customer_llm_answer(
                customer_question=user_query,
                product_dict=product_dict,
                result_count=len(result_df),
            )

            if not is_clean_ai_answer(final_answer):
                final_answer = None

        except Exception as e:
            print("Customer LLM hata:", e)
            final_answer = None

    if not final_answer:
        try:
            candidate = generate_customer_answer_with_llm(decision_result)

            if is_clean_ai_answer(candidate):
                final_answer = candidate

        except Exception as e:
            print("Customer answer engine hata:", e)
            final_answer = None

    if not final_answer:
        final_answer = create_customer_fallback_answer(decision_result)

    if competitor_note:
        final_answer = competitor_note + "\n\n" + final_answer

    st.session_state.customer_context = update_customer_context(
        st.session_state.customer_context,
        query_info,
    )

    result_df = decision_result.get("result_df", pd.DataFrame())
    final_query_info = decision_result.get("query_info", query_info)

    try:
        update_user_memory(user_id, query_info, result_df)
        log_user_behavior(
            user_id=user_id,
            role="customer",
            query=user_query,
            query_info=query_info,
            result_df=result_df,
            guardrail_info=guardrail_info,
            filter_info=filter_info,
            semantic_info=semantic_info,
            package_summary=decision_result.get("package_summary", {}),
        )
    except Exception as e:
        print("Memory/log customer hata:", e)

    st.session_state.last_decision = decision_result.get("decision", "")
    st.session_state.last_filter_info = filter_info
    st.session_state.last_semantic_info = semantic_info
    st.session_state.last_guardrail_info = guardrail_info
    st.session_state.last_fallback_answer = decision_result.get("fallback_answer", "")

    return result_df, final_query_info, final_answer


# =====================================================
# UI HELPERS
# =====================================================

def ai_percent(row):
    base = safe_number(row.get("final_ai_score", 0)) or safe_number(row.get("score", 0)) or 70

    if normalize_text(row.get("stock_status", "")) == "stokta":
        base += 4

    if safe_number(row.get("bank_transfer_price", 0)) > 0:
        base += 2

    if safe_number(row.get("senet_total_price", 0)) > 0:
        base += 2

    return int(min(98, max(55, round(base))))


def sub_head(text):
    """Sayfa içi tutarlı, marka renkli küçük başlık."""
    st.markdown(f'<div class="nv-subhead">{escape_html_text(text)}</div>', unsafe_allow_html=True)


def render_page_head(badge, title, desc=None, stats=None):
    """Tüm iç sayfalarda tekrar eden başlık + istatistik şeridi + ayraç bloğu."""
    st.markdown(f'<div class="brand-badge">{escape_html_text(badge)}</div>', unsafe_allow_html=True)
    st.markdown(f'<h2 class="section-head">{escape_html_text(title)}</h2>', unsafe_allow_html=True)

    if desc:
        st.markdown(f'<p class="section-desc">{escape_html_text(desc)}</p>', unsafe_allow_html=True)

    if stats:
        chips = "".join(
            f'<div class="nv-stat-chip"><b>{escape_html_text(value)}</b><span>{escape_html_text(label)}</span></div>'
            for label, value in stats
        )
        st.markdown(f'<div class="nv-stat-strip">{chips}</div>', unsafe_allow_html=True)

    st.markdown('<div class="nv-section-divider"></div>', unsafe_allow_html=True)


def assist_tip(icon, title, text):
    md_block(
        f"""
        <div class="nv-assist-tip">
            <div class="nv-assist-tip-icon">{escape_html_text(icon)}</div>
            <div class="nv-assist-tip-text">
                <b>{escape_html_text(title)}</b>
                <span>{escape_html_text(text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chat_panel(messages, empty_text, title, mode):
    user_label = "Mağaza Yetkilisi" if mode == "store" else "Müşteri"
    user_avatar = "M" if mode == "store" else "S"

    if not messages:
        body = f"""
        <div class="empty-chat">
            <div>
                <div class="empty-avatar">N</div>
                <div class="empty-title">Asistan hazır</div>
                <div class="empty-text">{text_to_html(empty_text)}</div>
                <div class="empty-suggestion">Örnek: Beko buzdolabı senetle olur mu?</div>
            </div>
        </div>
        """
    else:
        bubbles = []

        for message in messages:
            css_type = "user" if message.get("role") in ["user", "store"] else "ai"
            label = user_label if css_type == "user" else "Nevade AI"
            avatar = user_avatar if css_type == "user" else "N"
            time_label = escape_html_text(message.get("time", ""))
            time_html = f'<div class="msg-time">{time_label}</div>' if time_label else ""

            bubbles.append(
                f"""
                <div class="msg-row {css_type}-row">
                    <div class="msg-avatar {css_type}-avatar">{avatar}</div>
                    <div class="msg-bubble {css_type}-bubble">
                        <div class="msg-label">{label}</div>
                        <div>{text_to_html(message.get("text", ""))}</div>
                        {time_html}
                    </div>
                </div>
                """
            )

        body = "".join(bubbles)

    status = "Yapay Zeka Aktif" if LLM_READY else "Algoritma Aktif"
    message_count = len(messages)

    html_code = f"""
    <html>
    <head>
    <style>
    body {{
        margin: 0;
        font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial;
        background: transparent;
    }}

    .chat-shell {{
        height: 660px;
        border-radius: 34px;
        overflow: hidden;
        background:
            radial-gradient(circle at 0% 0%, rgba(20,92,224,.10), transparent 36%),
            radial-gradient(circle at 100% 100%, rgba(255,122,30,.07), transparent 40%),
            linear-gradient(145deg, rgba(255,255,255,.97), rgba(255,255,255,.80));
        border: 1px solid rgba(255,255,255,.85);
        box-shadow:
            0 34px 90px rgba(10,25,60,.11),
            inset 0 1px 0 rgba(255,255,255,.92);
        display: flex;
        flex-direction: column;
    }}

    .chat-header {{
        padding: 22px 26px;
        border-bottom: 1px solid rgba(226,232,240,.95);
        background:
            radial-gradient(circle at 0% 0%, rgba(20,92,224,.11), transparent 38%),
            radial-gradient(circle at 100% 0%, rgba(123,47,247,.11), transparent 38%),
            linear-gradient(135deg, #fff, #f8fafc);
        position: relative;
    }}

    .chat-header:before {{
        content: "";
        position: absolute;
        inset: 0 0 auto 0;
        height: 4px;
        background: linear-gradient(115deg, #0A1F44, #145CE0, #7B2FF7, #FF3D8A, #FF7A1E);
        background-size: 220% 100%;
        animation: auroraFlow 9s linear infinite;
    }}

    .chat-topline {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }}

    .chat-title-group {{ display:flex; align-items:center; gap:12px; }}

    .chat-title-avatar {{
        width: 40px; height: 40px; border-radius: 13px;
        background: linear-gradient(135deg, #145CE0, #7B2FF7, #FF3D8A);
        color: #fff; font-weight: 950; font-size: 17px;
        display:flex; align-items:center; justify-content:center;
        box-shadow: 0 10px 20px rgba(20,92,224,.25);
    }}

    .chat-title {{
        font-size: 21px;
        font-weight: 950;
        color: #020617;
        letter-spacing: -.5px;
    }}

    .chat-title-count {{
        font-size: 11.5px;
        color: #64748b;
        font-weight: 700;
        margin-top: 1px;
    }}

    .chat-status {{
        padding: 8px 13px;
        border-radius: 999px;
        background: rgba(20,92,224,.08);
        border: 1px solid rgba(20,92,224,.16);
        color: #145CE0;
        font-size: 11px;
        font-weight: 950;
        white-space: nowrap;
        display:flex; align-items:center; gap:6px;
    }}

    .chat-status:before {{
        content:"";
        width:7px; height:7px; border-radius:99px;
        background: radial-gradient(circle at 35% 30%, #fff, #29E47D 60%);
        box-shadow: 0 0 0 3px rgba(41,228,125,.18);
    }}

    .chat-sub {{
        margin-top: 9px;
        color: #64748b;
        font-size: 12.5px;
        line-height: 1.6;
        font-weight: 600;
    }}

    .chat-scroll {{
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        box-sizing: border-box;
        background:
            radial-gradient(circle at 10% 12%, rgba(20,92,224,.05), transparent 35%),
            radial-gradient(circle at 90% 80%, rgba(255,61,138,.05), transparent 36%),
            #fbfcfe;
        scroll-behavior: smooth;
    }}

    .msg-row {{
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
        align-items: flex-end;
    }}

    .user-row {{ justify-content: flex-end; }}
    .ai-row {{ justify-content: flex-start; }}
    .user-row .msg-avatar {{ order: 2; }}

    .msg-avatar {{
        width: 30px; height: 30px; min-width: 30px; border-radius: 10px;
        display:flex; align-items:center; justify-content:center;
        font-size: 12.5px; font-weight: 950; color:#fff;
    }}
    .ai-avatar {{ background: linear-gradient(135deg, #145CE0, #7B2FF7); }}
    .user-avatar {{ background: linear-gradient(135deg, #FF3D8A, #FF7A1E); }}

    .msg-bubble {{
        max-width: 78%;
        padding: 14px 17px;
        border-radius: 20px;
        font-size: 13.7px;
        line-height: 1.75;
        word-break: break-word;
        animation: fadeIn .22s ease-out;
    }}

    .user-bubble {{
        color: white;
        background: linear-gradient(135deg, #0A1F44, #7B2FF7 55%, #FF3D8A);
        border-bottom-right-radius: 6px;
        box-shadow: 0 16px 32px rgba(123,47,247,.20);
    }}

    .ai-bubble {{
        color: #243b53;
        background: #ffffff;
        border: 1px solid rgba(226,232,240,.96);
        border-bottom-left-radius: 6px;
        box-shadow: 0 14px 30px rgba(10,25,60,.06);
    }}

    .msg-label {{
        font-size: 10px;
        font-weight: 950;
        letter-spacing: .4px;
        text-transform: uppercase;
        opacity: .68;
        margin-bottom: 6px;
    }}

    .msg-time {{
        font-size: 9.5px;
        opacity: .55;
        margin-top: 7px;
        font-weight: 700;
    }}

    .empty-chat {{
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 32px;
        box-sizing: border-box;
        color: #64748b;
    }}

    .empty-avatar {{
        width: 54px; height: 54px; border-radius: 18px;
        background: linear-gradient(135deg, #145CE0, #7B2FF7, #FF3D8A);
        color: #fff; font-weight: 950; font-size: 22px;
        display:flex; align-items:center; justify-content:center;
        margin: 0 auto 14px;
        box-shadow: 0 16px 30px rgba(123,47,247,.22);
    }}

    .empty-title {{
        font-size: 22px;
        font-weight: 950;
        color: #020617;
        margin-bottom: 8px;
    }}

    .empty-text {{
        font-size: 13.5px;
        line-height: 1.7;
        margin-bottom: 16px;
    }}

    .empty-suggestion {{
        max-width: 480px;
        padding: 13px 17px;
        border-radius: 16px;
        background: rgba(20,92,224,.05);
        border: 1px solid rgba(20,92,224,.14);
        color: #145CE0;
        font-size: 12.5px;
        line-height: 1.55;
        font-weight: 800;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes auroraFlow {{
        0% {{ background-position: 0% 0%; }}
        100% {{ background-position: 220% 0%; }}
    }}
    </style>
    </head>

    <body>
        <div class="chat-shell">
            <div class="chat-header">
                <div class="chat-topline">
                    <div class="chat-title-group">
                        <div class="chat-title-avatar">N</div>
                        <div>
                            <div class="chat-title">{escape_html_text(title)}</div>
                            <div class="chat-title-count">{message_count} mesaj</div>
                        </div>
                    </div>
                    <div class="chat-status">{status}</div>
                </div>
                <div class="chat-sub">
                    Karar motoru veriyi doğrular, LLM cevabı doğal dile çevirir. Yeni mesajda konuşma otomatik en alta kayar.
                </div>
            </div>

            <div class="chat-scroll" id="chatScroll">
                {body}
            </div>
        </div>

        <script>
            const chatScroll = document.getElementById('chatScroll');
            if (chatScroll) {{
                chatScroll.scrollTop = chatScroll.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """

    render_iframe_html(html_code, height=680)



def visual_dataframe(df, title="Veri Tablosu", subtitle="", height=420):
    """Premium tablo başlığı + güvenli dataframe. HTML div içine st.dataframe gömmeyiz."""
    safe_title = html.escape(str(title or "Veri Tablosu"))
    safe_sub = html.escape(str(subtitle or ""))

    if df is None or getattr(df, "empty", True):
        md_block(
            f"""
            <div class="nv-empty-state">
                <div class="nv-empty-icon">⌁</div>
                <div>
                    <div class="nv-empty-title">{safe_title}</div>
                    <div class="nv-empty-sub">Gösterilecek veri bulunamadı.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    row_count = len(df)
    col_count = len(df.columns) if hasattr(df, "columns") else 0

    md_block(
        f"""
        <div class="nv-table-banner">
            <div class="nv-table-left">
                <div class="nv-table-eyebrow">DATA VIEW</div>
                <div class="nv-table-title">{safe_title}</div>
                <div class="nv-table-subtitle">{safe_sub}</div>
            </div>
            <div class="nv-table-count-pill">{row_count} satır · {col_count} kolon</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kwargs = {"use_container_width": True}
    if height is not None:
        kwargs["height"] = int(height) if isinstance(height, (int, float)) else height
    st.dataframe(df, **kwargs)

def render_mini_cart_bar():
    item_count = sum(int(item.get("quantity", 1)) for item in st.session_state.cart)
    total = get_cart_total()
    last_order = get_last_order()
    last_order_no = last_order.get("order_id", "-") if last_order else "-"

    modules = [
        ("NLP", "Ultra" if NLP_ENGINE_READY else "Basit"),
        ("LLM", "Açık" if LLM_READY else "Fallback"),
        ("Strict", "Aktif" if PRODUCT_FILTER_READY else "Fallback"),
        ("Semantic", "Aktif" if SEMANTIC_ENGINE_READY else "Fallback"),
        ("Guardrail", "Aktif" if GUARDRAIL_READY else "Fallback"),
        ("Memory", "Aktif" if MEMORY_ENGINE_READY else "Fallback"),
        ("Metrics", "Aktif" if METRICS_ENGINE_READY else "Fallback"),
        ("Vision", "Aktif" if VISION_ENGINE_READY else "Fallback"),
    ]
    module_html = "".join([f'<span class="nv-live-chip"><b>{html.escape(k)}</b>{html.escape(v)}</span>' for k, v in modules])

    md_block(
        f"""
        <div class="nv-livebar">
            <div class="nv-live-main">
                <div class="nv-live-orb"></div>
                <div>
                    <div class="nv-live-title">Canlı Ticaret Durumu</div>
                    <div class="nv-live-sub">
                        Sepet <b>{item_count}</b> ürün · Toplam <b>{money(total)}</b> · Sipariş <b>{len(st.session_state.orders)}</b> · Son <b>{last_order_no}</b>
                    </div>
                </div>
            </div>
            <div class="nv-live-modules">{module_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_app_header():
    current_user = st.session_state.get("current_user", {}) or {}
    user_name = current_user.get("name") or current_user.get("email") or "Nevade Kullanıcısı"
    user_role = {
        "admin": "Sistem Yöneticisi",
        "store": "Mağaza Personeli",
        "customer": "Müşteri Paneli",
    }.get(st.session_state.get("user_role", ""), current_user.get("role", "AI Panel"))
    user_email = st.session_state.get("user_email", "") or current_user.get("email", "") or "admin@nevade.com"

    md_block(
        f"""
        <section class="nv-hero-shell">
            <div class="nv-hero-bg-shape nv-shape-one"></div>
            <div class="nv-hero-bg-shape nv-shape-two"></div>
            <div class="nv-hero-content">
                <div class="nv-brand-panel">
                    <div class="nv-logo-premium">N</div>
                    <div>
                        <div class="nv-overline">NEVADE AI COMMERCE</div>
                        <h1 class="nv-hero-heading">Satış destek, ürün öneri ve görsel arama paneli</h1>
                        <p class="nv-hero-copy">
                            Katalog verisini doğrulayan karar motoru, güvenli cevap katmanı, senetli ödeme akışı ve görsel ürün algılama tek premium arayüzde.
                        </p>
                    </div>
                </div>
                <div class="nv-user-glass-card">
                    <div class="nv-user-topline">
                        <span>Aktif Oturum</span>
                        <span class="nv-online-dot"></span>
                    </div>
                    <div class="nv-user-name">{html.escape(str(user_name))}</div>
                    <div class="nv-user-role">{html.escape(str(user_role))}</div>
                    <div class="nv-user-email">{html.escape(str(user_email))}</div>
                    <div class="nv-hero-pills">
                        <span>AI Engine</span><span>Vision</span><span>Metrics</span><span>Guardrail</span>
                    </div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

def render_topbar():
    role = {
        "admin": "Sistem Yöneticisi",
        "store": "Mağaza Çalışanı",
        "customer": "Değerli Müşterimiz",
    }.get(st.session_state.user_role, "Kullanıcı")

    pages = [
        ("dashboard", "Kontrol", "⌂"),
        ("customer_ai", "Müşteri AI", "✦"),
        ("store_ai", "Mağaza AI", "◆"),
        ("quick_actions", "Hızlı", "⚡"),
        ("cart_checkout", "Sepet", "◈"),
        ("orders", "Sipariş", "▣"),
        ("compare", "Karşılaştır", "⇄"),
        ("products", "Katalog", "▥"),
        ("memory", "Memory", "◎"),
        ("metrics", "Metrics", "▤"),
        ("vision", "Görsel", "◉"),
    ]

    md_block(
        f"""
        <div class="nv-nav-head">
            <div>
                <div class="nv-nav-kicker">COMMERCE HUB</div>
                <div class="nv-nav-title">Operasyon modülleri</div>
            </div>
            <div class="nv-nav-role">{html.escape(str(role))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        columns = st.columns(len(pages) + 1, gap="small")
        for index, (page_id, label, icon) in enumerate(pages):
            with columns[index]:
                button_type = "primary" if st.session_state.get("page") == page_id else "secondary"
                if st.button(f"{icon} {label}", use_container_width=True, key=f"nav_{page_id}", type=button_type):
                    go_page(page_id)

        with columns[-1]:
            if st.button("⎋ Çıkış", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_role = ""
                st.session_state.page = "dashboard"
                st.rerun()

    render_mini_cart_bar()

def product_card(row, key_prefix, query_info=None, compact=False):
    product_id = clean_str(row.get("product_id", "")) or f"{key_prefix}_{abs(hash(row.get('product_name', 'urun')))}"
    product_name = clean_str(row.get("product_name", "İsimsiz Ürün"))
    category = clean_str(row.get("category", "-"))
    brand = clean_str(row.get("brand", "-"))
    image_link = clean_str(row.get("image_link", ""))
    percent = ai_percent(row)

    if percent >= 90:
        label = "Çok Uygun"
    elif percent >= 80:
        label = "Uygun"
    elif percent >= 70:
        label = "Değerlendirilebilir"
    else:
        label = "Alternatif"

    tags = []
    if normalize_text(row.get("stock_status", "")) == "stokta":
        tags.append('<span class="nv-tag">Stokta</span>')
    if safe_number(row.get("bank_transfer_price", 0)) > 0:
        tags.append('<span class="nv-tag orange">Havale avantajı</span>')
    if safe_number(row.get("senet_total_price", 0)) > 0:
        tags.append('<span class="nv-tag purple">Senetli ödeme</span>')

    card = st.container(border=True)
    with card:
        image_col, info_col = st.columns([1, 2.65], gap="large")

        with image_col:
            img_box = st.container(border=True)
            with img_box:
                if image_link:
                    try:
                        st.image(image_link, width="stretch")
                    except Exception:
                        st.markdown('<div class="nv-image-slot"><div class="nv-no-image">N</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="nv-image-slot"><div class="nv-no-image">N</div></div>', unsafe_allow_html=True)

        with info_col:
            if clean_str(row.get("package_group", "")):
                st.markdown(
                    f'<div class="brand-badge">Paket Kategorisi: {html.escape(str(row.get("package_group")))}</div>',
                    unsafe_allow_html=True,
                )

            md_block(
                f"""
                <div class="nv-product-top">
                    <div>
                        <div class="nv-product-name">{html.escape(product_name)}</div>
                        <div class="nv-product-meta">{html.escape(category)} · {html.escape(brand)} · Ürün Kodu: {html.escape(str(product_id))}</div>
                    </div>
                    <div class="nv-score-chip"><b>%{percent}</b><span>{label}</span></div>
                </div>
                <div class="nv-score-bar-wrap">
                    <div class="nv-score-bar-label"><span>AI Eşleşme Skoru</span><span>%{percent}</span></div>
                    <div class="nv-score-bar"><div class="nv-score-bar-fill" style="width:{percent}%;"></div></div>
                </div>
                <div class="nv-product-price-row">
                    <div class="nv-product-price">{money(row.get("price", 0))}</div>
                    <div>{''.join(tags)}</div>
                </div>
                <div class="nv-product-desc">{html.escape(clean_str(row.get("description", "Açıklama bulunmuyor.")))}</div>
                """,
                unsafe_allow_html=True,
            )

            if clean_str(row.get("features", "")):
                st.caption(row.get("features", ""))

            if not compact:
                tab1, tab2, tab3 = st.tabs(["AI Öneri Nedeni", "Ödeme Modelleri", "Satış Notu"])
                with tab1:
                    st.write(row.get("description", "Açıklama bulunmuyor."))
                    if clean_str(row.get("features", "")):
                        st.write(row.get("features", ""))
                with tab2:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Peşin:** {money(row.get('cash_price', 0))}")
                        st.write(f"**Havale:** {money(row.get('bank_transfer_price', 0))}")
                    with c2:
                        st.write(f"**Kart:** {money(row.get('card_price', 0))}")
                        st.write(f"**6 Taksit:** {money(row.get('installment_6_total', 0))}")
                    with c3:
                        st.write(f"**Senetli Toplam:** {money(row.get('senet_total_price', 0))}")
                        st.write(f"**Senetli Aylık:** {money(row.get('senet_monthly_9', 0))}")
                with tab3:
                    values = get_payment_values(row)
                    if values["best_option"]:
                        st.success(f"Toplam tutarda en avantajlı seçenek: {values['best_option'][0]} - {money(values['best_option'][1])}")
                    if values["senet_total"] > 0:
                        st.info(f"Aylık düşük ödeme için senetli seçenek anlatılabilir: {money(values['senet_monthly'])}/ay")

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("Sepete Ekle", key=f"cart_{key_prefix}_{product_id}", width="stretch"):
                    add_product_to_cart(row)
                    st.rerun()
            with b2:
                if st.button("Karşılaştır", key=f"comp_{key_prefix}_{product_id}", width="stretch"):
                    existing_ids = [str(item.get("product_id")) for item in st.session_state.compare_items]
                    if str(product_id) not in existing_ids:
                        st.session_state.compare_items.append(row.to_dict() if hasattr(row, "to_dict") else dict(row))
                        st.success("Karşılaştırma listesine eklendi.")
                    else:
                        st.info("Bu ürün zaten karşılaştırma listesinde.")
            with b3:
                if row.get("product_link"):
                    st.link_button("Ürüne Git", row.get("product_link"), width="stretch")


def order_card(order):
    md_block(
        f"""
        <div class="order-card">
            <div class="status-pill">{order.get("status")}</div>
            <div class="order-title">{order.get("order_id")} | {order.get("product_name")}</div>
            <div class="order-detail">
                <b>Müşteri:</b> {order.get("customer_name")}<br>
                <b>Ödeme:</b> {order.get("payment_type")}<br>
                <b>Kargo:</b> {order.get("cargo_company")} / {order.get("tracking_no")}<br>
                <b>Tahmini Teslimat:</b> {order.get("estimated_delivery")}<br>
                <b>Adres:</b> {order.get("address")}<br>
                <b>Toplam:</b> {money(order.get("total_price", 0))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Sipariş ürünleri"):
        visual_dataframe(pd.DataFrame(order.get("items", [])), title="Sipariş Ürünleri", subtitle="Sipariş içindeki ürün kalemleri")


# =====================================================
# PAGES
# =====================================================

def set_login_credentials(email, password):
    st.session_state["login_email"] = email
    st.session_state["login_password"] = password


def render_login_page():
    st.write("")

    left, right = st.columns([1.15, 0.95], gap="large")

    with left:
        features = [
            ("◆", "Karar Motoru", "Ürünü, bütçeyi, stok durumunu ve ödeme alternatiflerini güvenli veri üzerinden seçer; LLM'in fiyat uydurmasını engeller."),
            ("✦", "Satış Dili AI", "Karar motorunun doğruladığı veriyi müşteri ve mağaza personeli için doğal, ikna edici cevaba dönüştürür."),
            ("◈", "Operasyon Merkezi", "Sepet, sipariş, kargo, fatura, iade ve mağaza destek süreçlerini tek panelde birleştirir."),
        ]

        feature_rows_html = "".join(
            f"""
            <div class="nv-login-feature-row nv-login-feature-row-{i}">
                <div class="nv-login-feature-icon">{icon}</div>
                <div>
                    <div class="nv-login-feature-title">{escape_html_text(title)}</div>
                    <div class="nv-login-feature-desc">{escape_html_text(desc)}</div>
                </div>
            </div>
            """
            for i, (icon, title, desc) in enumerate(features)
        )

        stat_items = [
            ("✧", "NLP Motoru", "Ultra" if NLP_ENGINE_READY else "Basit", NLP_ENGINE_READY),
            ("✦", "LLM Katmanı", "Aktif" if LLM_READY else "Fallback", LLM_READY),
            ("◈", "Guardrail", "Açık" if GUARDRAIL_READY else "Fallback", GUARDRAIL_READY),
            ("◉", "Görsel Arama", "Açık" if VISION_ENGINE_READY else "Fallback", VISION_ENGINE_READY),
        ]

        stats_html = "".join(
            f"""
            <div class="nv-login-stat">
                <div class="nv-login-stat-dot {'good' if ready else 'warn'}"></div>
                <div class="nv-login-stat-icon">{icon}</div>
                <div class="nv-login-stat-body"><b>{value}</b><span>{label}</span></div>
            </div>
            """
            for icon, label, value, ready in stat_items
        )

        md_block(
            f"""
            <div class="nv-login-hero">
                <div class="nv-login-hero-top">
                    <div class="brand-badge" style="background:rgba(255,255,255,.18); border-color:rgba(255,255,255,.30); color:#fff;">
                        NEVADE AI COMMERCE HUB
                    </div>
                    <h1 class="nv-login-hero-heading">
                        E-ticareti LLM + karar<br>motoru seviyesine taşı.
                    </h1>
                    <p class="nv-login-hero-copy">
                        Ürün önerisi, çeyiz paketi, senetli ödeme, havale avantajı, mağaza personel
                        desteği, sipariş takibi ve müşteri hizmetleri akışını tek premium panelde
                        birleştiren yapay zeka destekli ticaret asistanı.
                    </p>
                </div>
                {feature_rows_html}
                <div class="nv-login-stats">
                    {stats_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        login_card = st.container(border=True)
        with login_card:
            md_block(
                """
                <div class="nv-login-card-head">
                    <div class="brand-badge">GÜVENLİ GİRİŞ</div>
                    <div class="nv-login-card-title">Nevade Panel</div>
                    <div class="nv-login-card-sub">Rolünüzü seçin, bilgiler otomatik doldurulsun; ya da doğrudan kendi bilgilerinizi girin.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.button(
                    "⌂ Yönetici",
                    key="role_admin",
                    width="stretch",
                    on_click=set_login_credentials,
                    args=("admin@nevade.com", "1234"),
                )
            with rc2:
                st.button(
                    "◆ Mağaza",
                    key="role_store",
                    width="stretch",
                    on_click=set_login_credentials,
                    args=("magaza@nevade.com", "1234"),
                )
            with rc3:
                st.button(
                    "✦ Müşteri",
                    key="role_customer",
                    width="stretch",
                    on_click=set_login_credentials,
                    args=("musteri@nevade.com", "1234"),
                )

            email = st.text_input("Kullanıcı E-Posta Adresi", key="login_email")
            password = st.text_input("Şifre", key="login_password", type="password")

            if st.button("Sisteme Giriş Yap →", width="stretch", type="primary"):
                if email in USERS and USERS[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_role = USERS[email]["role"]
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Hatalı e-posta adresi veya şifre.")

            md_block(
                """
                <div class="nv-login-fineprint">
                    Demo hesaplar: admin@nevade.com · magaza@nevade.com · musteri@nevade.com — şifre: 1234
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.metric("AI Katmanı", "NLP + LLM", "Güvenli hibrit yapı")
        with b2:
            st.metric("Sepet Akışı", "Aktif", "Ürün → Sepet → Sipariş")
        with b3:
            st.metric("NLP Durumu", "Ultra" if NLP_ENGINE_READY else "Basit", "Niyet ve varlık analizi")
        with b4:
            st.metric("LLM Durumu", "Hazır" if LLM_READY else "Fallback", "Doğal cevap motoru")


def dashboard(products_df):
    stats = [
        ("Toplam Ürün", len(products_df)),
        ("Sipariş", len(st.session_state.orders)),
        ("Sepet Ürün", sum(int(item.get("quantity", 1)) for item in st.session_state.cart)),
        ("Sepet Toplamı", money(get_cart_total())),
    ]
    render_page_head(
        "EXECUTIVE COMMERCE DASHBOARD",
        "Nevade AI Yönetim Paneli",
        "Karar motoru güvenli veriyi seçer, LLM bu veriyi satışa ve müşteri deneyimine uygun dile dönüştürür.",
        stats=stats,
    )

    st.caption(f"NLP: {'Ultra aktif' if NLP_ENGINE_READY else 'Basit mod'} · LLM: {'Aktif' if LLM_READY else 'Fallback'}")

    md_block(
        """
        <div class="luxury-kpi">
            <h3>Nevade AI Commerce Hub — Üst Segment Demo</h3>
            <p>
                Bu panelde LLM doğrudan ürün veya fiyat kararı vermez. Önce NLP kullanıcı niyetini analiz eder,
                karar motoru doğrulanmış ürün, stok, fiyat ve ödeme verisini seçer. LLM yalnızca bu güvenli veriyi
                müşteri ve mağaza personeli diline çevirir.
            </p>
        </div>
        <div class="premium-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")

    with left:
        md_block(
            """
            <div class="premium-card">
                <h3>LLM Kontrollü Ticaret Akışı</h3>
                <p><b>1. Ultra NLP:</b> Kullanıcı niyetini, bütçeyi, ödeme isteğini ve ürün tipini algılar.</p>
                <p><b>2. Karar Motoru:</b> Doğru ürün, stok, fiyat ve ödeme seçeneğini seçer.</p>
                <p><b>3. LLM:</b> Veriyi doğal müşteri/personel diline çevirir.</p>
                <p><b>4. Kalite Filtresi:</b> Karışık dil, prompt sızıntısı veya kötü cevap varsa engeller.</p>
                <p><b>5. Fallback:</b> LLM kötü cevap verirse güvenli premium cevap üretir.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        sub_head("Canlı Operasyon Özeti")

        if not st.session_state.cart:
            st.info("Sepet şu anda boş.")
        else:
            for item in st.session_state.cart:
                quantity = int(item.get("quantity", 1))
                price = safe_number(item.get("price", 0))
                st.write(f"- **{item.get('product_name')}** x {quantity} - {money(price * quantity)}")

            if st.button("Sepeti Temizle", width="stretch"):
                st.session_state.cart = []
                st.rerun()

        sub_head("Son Sipariş")
        st.info(order_text(get_last_order()))

        sub_head("Kullanıcı Hafızası")
        if MEMORY_ENGINE_READY:
            st.info(memory_summary_text(st.session_state.user_email or "anonymous"))
        else:
            st.warning("Memory engine aktif değil.")


def customer_page(products_df):
    stats = [
        ("Sohbet Mesajı", len(st.session_state.customer_messages)),
        ("Son Sonuç", len(st.session_state.last_results) if isinstance(st.session_state.last_results, pd.DataFrame) else 0),
        ("Guardrail", "Güvenli" if not (st.session_state.last_guardrail_info or {}).get("blocked") else "Engellendi"),
    ]
    render_page_head(
        "CUSTOMER AI EXPERIENCE",
        "Akıllı Müşteri Asistanı",
        "Müşteri doğal dilde yazar; sistem ürün, ödeme ve uygunluk kararını üretir.",
        stats=stats,
    )

    left, right = st.columns([1.45, 2], gap="large")

    with left:
        chat_panel(
            st.session_state.customer_messages,
            "Müşteri asistanı hazır. Bir ürün, bütçe veya ödeme isteği yazın.",
            "Müşteri AI",
            "customer",
        )

        assist_tip(
            "✦",
            "Nasıl daha iyi sonuç alırım?",
            "Ürün tipi, bütçe ve ödeme tercihinizi (senet / havale / taksit) tek cümlede belirtirseniz karar motoru daha isabetli eşleştirir.",
        )

        with st.form("customer_form", clear_on_submit=True):
            question = st.text_input(
                "Müşteri Talebi",
                placeholder="Örn: 50000 TL çeyiz paketi istiyorum, senetli olsun",
            )
            submitted = st.form_submit_button("Gönder", width="stretch", type="primary")

        if submitted and question.strip():
            now_label = datetime.now().strftime("%H:%M")
            st.session_state.customer_messages.append({"role": "user", "text": question, "time": now_label})

            with st.spinner("Ultra NLP, karar motoru ve LLM birlikte çalışıyor..."):
                results, query_info, answer = recommend_products_with_new_ai(products_df, question)
                st.session_state.last_results = results
                st.session_state.last_query_info = query_info
                st.session_state.customer_messages.append(
                    {"role": "assistant", "text": answer, "time": datetime.now().strftime("%H:%M")}
                )

            st.rerun()

        sub_head("Hızlı Yanıtlar")

        quick_columns = st.columns(4)

        actions = [
            ("Daha ucuzunu göster", "Daha ucuzu var mı?"),
            ("Senetli ödeme", "Senetli ödeme seçeneğini göster"),
            ("Havale avantajı", "Havale avantajı olan seçenekleri göster"),
            ("Sepete git", "GO_CART"),
        ]

        for index, (label, quick_query) in enumerate(actions):
            with quick_columns[index]:
                if st.button(label, key=f"quick_{index}", width="stretch"):
                    if quick_query == "GO_CART":
                        go_page("cart_checkout")

                    now_label = datetime.now().strftime("%H:%M")
                    st.session_state.customer_messages.append({"role": "user", "text": quick_query, "time": now_label})
                    results, query_info, answer = recommend_products_with_new_ai(products_df, quick_query)
                    st.session_state.last_results = results
                    st.session_state.last_query_info = query_info
                    st.session_state.customer_messages.append(
                        {"role": "assistant", "text": answer, "time": datetime.now().strftime("%H:%M")}
                    )
                    st.rerun()

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Sohbeti Sıfırla", width="stretch"):
                st.session_state.customer_messages = []
                st.session_state.customer_context = create_empty_customer_context()
                st.session_state.last_results = pd.DataFrame()
                st.session_state.last_filter_info = {}
                st.session_state.last_semantic_info = {}
                st.session_state.last_package_summary = {}
                st.session_state.last_guardrail_info = {}
                st.rerun()

        with c2:
            if st.button("Sepete Git", width="stretch"):
                go_page("cart_checkout")

    with right:
        sub_head("AI Eşleşen Ürünler")

        if st.session_state.last_query_info:
            with st.expander("Algılanan Müşteri İsteği", expanded=False):
                st.json(st.session_state.last_query_info)

                if st.session_state.last_guardrail_info:
                    st.markdown("**Guardrail**")
                    st.json(st.session_state.last_guardrail_info)

                if st.session_state.last_memory_info:
                    st.markdown("**Memory**")
                    st.json(st.session_state.last_memory_info)

                if st.session_state.last_filter_info:
                    st.markdown("**Strict Filter**")
                    st.json(st.session_state.last_filter_info)

                if st.session_state.last_semantic_info:
                    st.markdown("**Semantic Search**")
                    st.json(st.session_state.last_semantic_info)

                if st.session_state.last_package_summary:
                    st.markdown("**Package Summary**")
                    st.json(st.session_state.last_package_summary)

                st.markdown(
                    f'<div class="decision-box"><strong>Karar:</strong> {st.session_state.last_decision}</div>',
                    unsafe_allow_html=True,
                )

        if st.session_state.last_results.empty:
            st.info("Henüz ürün eşleşmesi yok.")
        else:
            st.write(f"Toplam **{len(st.session_state.last_results)}** ürün listeleniyor.")

            for index, row in st.session_state.last_results.iterrows():
                product_card(row, f"cust_{index}", st.session_state.last_query_info)


def store_page(products_df):
    stats = [
        ("Mağaza Sorgusu", len(st.session_state.store_messages)),
        ("Aktif Sipariş", len(st.session_state.orders)),
        ("Guardrail", "Güvenli" if not (st.session_state.last_guardrail_info or {}).get("blocked") else "Engellendi"),
    ]
    render_page_head(
        "STORE AI SALES COPILOT",
        "Mağaza Personel Asistanı",
        "Karar motoru doğru veriyi bulur, LLM bunu personele hazır satış cevabı olarak sunar.",
        stats=stats,
    )

    left, right = st.columns([1.45, 2], gap="large")

    with left:
        chat_panel(
            st.session_state.store_messages,
            "Mağaza personeli için ürün, ödeme, senet, stok ve sipariş sorgusu hazır.",
            "Mağaza AI",
            "store",
        )

        assist_tip(
            "◆",
            "Personel için ipucu",
            "Sipariş numarası (NVD-...) yazarsanız doğrudan sipariş kartını getirir; ürün + ödeme türü yazarsanız en avantajlı seçeneği önerir.",
        )

        with st.form("store_form", clear_on_submit=True):
            question = st.text_input(
                "Personel Sorusu",
                placeholder="Örn: Beko buzdolabı senetle olur mu, en avantajlı ödeme ne?",
            )
            submitted = st.form_submit_button("Sorgula", width="stretch", type="primary")

        if submitted and question.strip():
            now_label = datetime.now().strftime("%H:%M")
            st.session_state.store_messages.append({"role": "store", "text": question, "time": now_label})

            with st.spinner("Ultra NLP veriyi analiz ediyor, karar motoru ürünü seçiyor, LLM cevabı hazırlıyor..."):
                answer = store_product_answer(products_df, question)
                st.session_state.store_messages.append(
                    {"role": "assistant", "text": answer, "time": datetime.now().strftime("%H:%M")}
                )

            st.rerun()

        if st.button("Mağaza Sohbetini Temizle", width="stretch"):
            st.session_state.store_messages = []
            st.rerun()

    with right:
        sub_head("Son Siparişler ve Operasyon Durumu")

        for order in st.session_state.orders[-5:][::-1]:
            order_card(order)


def cart_page():
    render_page_head("CART TO ORDER FLOW", "Sepet ve Sipariş Oluşturma")

    a, b, c = st.columns(3)

    with a:
        st.metric("Sepetteki Ürün", len(st.session_state.cart))

    with b:
        st.metric("Sepet Toplamı", money(get_cart_total()))

    with c:
        st.metric("Sipariş Sayısı", len(st.session_state.orders))

    if not st.session_state.cart:
        st.info("Sepet boş. Ürün kartlarından sepete ürün ekleyebilirsiniz.")
        return

    sub_head("Sepetteki Ürünler")

    for index, item in enumerate(st.session_state.cart):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.4, 1, 1, 1])
            quantity = int(item.get("quantity", 1))
            price = safe_number(item.get("price", 0))

            with c1:
                st.write(f"**{item.get('product_name')}**")
                st.caption(f"{item.get('category')} | {item.get('brand')}")

            with c2:
                st.metric("Adet", quantity)

            with c3:
                st.metric("Toplam", money(price * quantity))

            with c4:
                if st.button("Kaldır", key=f"remove_{index}", width="stretch"):
                    st.session_state.cart.pop(index)
                    st.rerun()

    sub_head("Sipariş Bilgileri")

    with st.form("checkout_form"):
        customer_name = st.text_input("Müşteri Adı", value="Demo Müşteri")
        address = st.text_area("Teslimat Adresi", value="İstanbul / Demo Adres", height=90)

        c1, c2 = st.columns(2)

        with c1:
            payment_type = st.selectbox("Ödeme Tipi", ["Kart", "Havale", "Senetli", "Peşin", "Kapıda Ödeme"])

        with c2:
            store_name = st.selectbox(
                "Mağaza / Kanal",
                ["Online Mağaza", "Merter Mağazası", "Bakırköy Mağazası", "Çağrı Merkezi"],
            )

        submitted = st.form_submit_button("Siparişi Tamamla", width="stretch", type="primary")

    if submitted:
        order = create_order_from_cart(customer_name, address, payment_type, store_name)
        st.session_state.support_result = {
            "action": "Sipariş oluşturuldu",
            "response": order_text(order),
        }
        go_page("orders")


def orders_page():
    active_count = sum(1 for o in st.session_state.orders if o.get("status") != "Kargoda")
    stats = [
        ("Toplam Sipariş", len(st.session_state.orders)),
        ("Aktif İşlemde", active_count),
        ("Son Sipariş", get_last_order().get("order_id", "-") if get_last_order() else "-"),
    ]
    render_page_head("ORDER MANAGEMENT", "Sipariş Yönetimi", stats=stats)

    if st.session_state.support_result:
        md_block(
            f"""
            <div class="success-hero">
                <b>{st.session_state.support_result.get("action")}</b><br><br>
                {text_to_html(st.session_state.support_result.get("response"))}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

    for order in st.session_state.orders[::-1]:
        order_card(order)


def quick_page():
    render_page_head("SERVICE OPERATIONS", "Hızlı İşlemler")

    left, right = st.columns([1, 1.4], gap="large")

    categories = {
        "Sipariş / Kargo": ["Siparişim nerede?", "Kargom nerede?", "Sipariş detaylarımı göster"],
        "Fatura": ["Faturama nasıl ulaşabilirim?"],
        "İade / İptal": ["İade talebi oluştur", "Siparişimi iptal etmek istiyorum"],
        "Sepet / Ödeme": ["Sepetimi göster", "Senetli alışveriş bilgisi", "Taksit fırsatları", "Havale avantajı"],
    }

    with left:
        category = st.selectbox("Kategori", list(categories.keys()))
        action = st.selectbox("İşlem", categories[category])
        query = st.text_input("Sipariş No / Takip No / Müşteri Adı", placeholder="Örn: NVD-1003")

        if st.button("İşlemi Çalıştır", width="stretch", type="primary"):
            order = find_order(query) if query else get_last_order()

            if "Sipariş" in category:
                answer = order_text(order)
            elif "Fatura" in category:
                answer = f"Fatura bilgisi hazır.\n\n{order_text(order)}"
            elif action == "Sepetimi göster":
                answer = f"Sepet toplamı: {money(get_cart_total())}\nÜrün adedi: {len(st.session_state.cart)}"
            else:
                answer = "İşlem kaydı oluşturuldu. Müşteri hizmetleri bu talebi inceleyebilir."

            st.session_state.support_result = {
                "action": action,
                "response": answer,
            }

            st.session_state.quick_action_history.append(
                {
                    "category": category,
                    "action": action,
                    "query": query,
                    "response": answer,
                }
            )

            st.rerun()

    with right:
        sub_head("İşlem Sonucu")

        if st.session_state.support_result:
            md_block(
                f"""
                <div class="quick-result-box">
                    <strong>{st.session_state.support_result.get("action")}</strong><br><br>
                    {text_to_html(st.session_state.support_result.get("response"))}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Bir işlem seçip çalıştırdığınızda sonuç burada görünecek.")

        sub_head("Son Siparişler")

        for order in st.session_state.orders[-3:][::-1]:
            order_card(order)


def compare_page():
    render_page_head("COMPARISON MATRIX", "Ürün Karşılaştırma")

    if not st.session_state.compare_items:
        st.info("Karşılaştırma listeniz boş. Katalog veya AI sonuçlarından 'Karşılaştır' butonuyla ürün ekleyin.")
        return

    if st.button("Listeyi Boşalt", width="stretch"):
        st.session_state.compare_items = []
        st.rerun()

    compare_df = pd.DataFrame(st.session_state.compare_items)

    visible_cols = [
        col
        for col in [
            "product_id",
            "product_name",
            "category",
            "brand",
            "price",
            "bank_transfer_price",
            "senet_total_price",
            "stock_status",
        ]
        if col in compare_df.columns
    ]

    visual_dataframe(compare_df[visible_cols], title="Karşılaştırma Matrisi", subtitle="Seçili ürünlerin fiyat, marka ve stok karşılaştırması")

    sub_head("Ürün Kartları")

    for index, row in compare_df.iterrows():
        product_card(row, f"compare_{index}", compact=True)


def products_page(products_df):
    in_stock = int((products_df["stock_status"].apply(normalize_text) == "stokta").sum()) if "stock_status" in products_df.columns else 0
    avg_price = money(products_df["price"].mean()) if "price" in products_df.columns and not products_df.empty else money(0)
    stats = [
        ("Toplam Ürün", len(products_df)),
        ("Stokta", in_stock),
        ("Ortalama Fiyat", avg_price),
    ]
    render_page_head("PRODUCT CATALOG", "Ürün Kataloğu", stats=stats)

    with st.expander("Yeni Ürün Ekleme Paneli", expanded=False):
        with st.form("add_product_form"):
            sub_head("Temel Bilgiler")
            c1, c2 = st.columns(2)
            with c1:
                product_id = st.text_input("Ürün Kodu", placeholder="P007")
                category = st.selectbox("Kategori", ["Beyaz Eşya", "Televizyon", "Küçük Ev Aleti", "Cep Telefonu", "Bilgisayar"])
            with c2:
                product_name = st.text_input("Ürün İsmi")
                brand = st.text_input("Marka")

            sub_head("Fiyat ve Stok")
            c3, c4 = st.columns(2)
            with c3:
                price = st.number_input("Liste Fiyatı", min_value=0, value=10000)
            with c4:
                stock = st.selectbox("Stok Durumu", ["Stokta", "Tükendi", "Sınırlı Stok"])

            sub_head("Açıklama")
            description = st.text_area("Açıklama")
            use_case = st.text_input("Kullanım Amacı", value="Ev, günlük kullanım")
            features = st.text_input("Özellikler", value="Demo özellik")

            submitted = st.form_submit_button("Ürünü Kaydet", width="stretch", type="primary")

            if submitted and product_id and product_name:
                new_row = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "brand": brand,
                    "price": price,
                    "cash_price": price * 0.95,
                    "bank_transfer_price": price * 0.93,
                    "card_price": price,
                    "installment_6_total": price * 1.05,
                    "senet_total_price": price * 1.20,
                    "senet_monthly_9": price * 1.20 / 9,
                    "stock_status": stock,
                    "payment_options": "Kart, Havale, Taksit, Senet",
                    "use_case": use_case,
                    "features": features,
                    "description": description,
                    "product_link": "https://www.nevade.com/",
                    "image_link": "",
                }

                updated_df = pd.concat([products_df, pd.DataFrame([new_row])], ignore_index=True)
                save_products(updated_df)

                st.success("Ürün eklendi.")
                st.rerun()

    visible_cols = [
        col
        for col in [
            "product_id",
            "product_name",
            "category",
            "brand",
            "price",
            "bank_transfer_price",
            "senet_total_price",
            "stock_status",
        ]
        if col in products_df.columns
    ]

    visual_dataframe(products_df[visible_cols], title="Ürün Kataloğu", subtitle="Nevade ürünleri, fiyat ve stok bilgileri")




def memory_page():
    render_page_head("CUSTOMER MEMORY", "Kullanıcı Hafızası ve Davranış Logları")

    user_id = st.session_state.user_email or "anonymous"

    sub_head("Hafıza Özeti")
    st.info(memory_summary_text(user_id))

    sub_head("Ham Kullanıcı Hafızası")
    try:
        st.json(get_user_memory(user_id))
    except Exception as e:
        st.warning(f"Hafıza okunamadı: {e}")

    sub_head("Son Davranış Logları")
    logs = load_behavior_log(limit=100)

    if logs is None or logs.empty:
        st.info("Henüz davranış logu yok.")
    else:
        visual_dataframe(logs, title="Davranış Logları", subtitle="Kullanıcı sorguları ve AI etkileşim kayıtları")




def metrics_page():
    render_page_head(
        "AI PERFORMANCE METRICS",
        "AI Performans ve Kullanım Metrikleri",
        "Sistem kullanımını, müşteri ilgisini, ödeme tercihlerini ve güvenlik olaylarını ölçer.",
    )

    if not METRICS_ENGINE_READY:
        st.warning("Metrics engine aktif değil. src/metrics_engine.py dosyasını eklediğinizde bu sayfa otomatik aktif olur.")

    metrics = calculate_ai_metrics()

    a, b, c, d = st.columns(4)

    with a:
        st.metric("Toplam Sorgu", metrics.get("total_queries", 0))

    with b:
        st.metric("Müşteri Sorgusu", metrics.get("customer_queries", 0))

    with c:
        st.metric("Mağaza Sorgusu", metrics.get("store_queries", 0))

    with d:
        st.metric("Guardrail Olayı", metrics.get("guardrail_events", 0))

    e, f, g, h = st.columns(4)

    with e:
        st.metric("Strict Filter", metrics.get("strict_filter_events", 0))

    with f:
        st.metric("Semantic Search", metrics.get("semantic_events", 0))

    with g:
        st.metric("Paket Sorgusu", metrics.get("package_events", 0))

    with h:
        st.metric("Son Güncelleme", metrics.get("last_updated", "-"))

    st.markdown('<div class="nv-section-divider"></div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        sub_head("En Çok Sorulan Ürün Tipleri")
        product_report = get_product_interest_report()

        if product_report is None or product_report.empty:
            st.info("Henüz ürün tipi verisi yok.")
        else:
            visual_dataframe(product_report, title="Ürün Tipi İlgisi", subtitle="Müşterilerin en çok sorduğu ürün kategorileri")

        sub_head("Ödeme Tercihleri")
        payment_report = get_payment_interest_report()

        if payment_report is None or payment_report.empty:
            st.info("Henüz ödeme tercihi verisi yok.")
        else:
            visual_dataframe(payment_report, title="Ödeme Tercihleri", subtitle="Senet, kart, havale ve taksit ilgi dağılımı")

    with right:
        sub_head("En Çok Önerilen Ürünler")
        top_product_report = get_top_product_report()

        if top_product_report is None or top_product_report.empty:
            st.info("Henüz ürün öneri verisi yok.")
        else:
            visual_dataframe(top_product_report, title="En Çok Önerilen Ürünler", subtitle="AI karar motorunun öne çıkardığı ürünler")

        sub_head("Guardrail Kategorileri")
        guardrail_report = get_guardrail_report()

        if guardrail_report is None or guardrail_report.empty:
            st.info("Henüz guardrail verisi yok.")
        else:
            visual_dataframe(guardrail_report, title="Guardrail Kategorileri", subtitle="Güvenlik ve politika filtreleme olayları")

    sub_head("Son AI Aktivitesi")
    recent = get_recent_activity(limit=100)

    if recent is None or recent.empty:
        st.info("Henüz aktivite logu yok.")
    else:
        visual_dataframe(recent, title="Son AI Aktivitesi", subtitle="Son müşteri/mağaza etkileşimleri")



def vision_page(products_df):
    render_page_head(
        "VISUAL PRODUCT SEARCH",
        "Görsel ile Ürün Bulma",
        "Müşteri ürün görseli yükler; sistem Gemini Vision + manuel ürün tipi + semantic search ile en yakın katalog ürünlerini bulur.",
    )

    left, right = st.columns([1, 1.5], gap="large")

    with left:
        uploaded_file = st.file_uploader(
            "Ürün görseli yükle",
            type=["png", "jpg", "jpeg", "webp"],
        )

        visual_type_label = st.selectbox(
            "Görseldeki ürün tipi",
            [
                "Otomatik / emin değilim",
                "Buzdolabı",
                "Mini buzdolabı / içecek soğutucu",
                "Çamaşır makinesi",
                "Bulaşık makinesi",
                "Televizyon",
                "Süpürge",
                "Laptop / bilgisayar",
                "Telefon",
                "Klima",
                "Fırın / ankastre",
            ],
        )

        description = st.text_area(
            "Görsel / ürün açıklaması",
            placeholder="Örn: Balkonda içecek saklamak için küçük buzdolabı gibi bir ürün arıyorum.",
            height=120,
        )

        if uploaded_file is not None:
            st.image(uploaded_file, caption=uploaded_file.name, width="stretch")
            st.session_state.last_uploaded_image_name = uploaded_file.name

        type_to_query = {
            "Otomatik / emin değilim": "",
            "Buzdolabı": "buzdolabi no frost sogutucu",
            "Mini buzdolabı / içecek soğutucu": "mini buzdolabi minibar icecek sogutucu kucuk buzdolabi",
            "Çamaşır makinesi": "camasir makinesi",
            "Bulaşık makinesi": "bulasik makinesi",
            "Televizyon": "televizyon smart tv",
            "Süpürge": "supurge temizlik",
            "Laptop / bilgisayar": "laptop bilgisayar notebook ogrenci",
            "Telefon": "telefon iphone galaxy android",
            "Klima": "klima",
            "Fırın / ankastre": "firin ankastre ocak",
        }

        use_gemini_vision = st.checkbox(
            "Gemini Vision ile görseli otomatik analiz et",
            value=True,
        )

        sub_head("Hızlı Görsel Arama Testleri")
        t1, t2 = st.columns(2)

        with t1:
            if st.button("Mini buzdolabı örneği", width="stretch"):
                description = "Balkonda içecek saklamak için küçük buzdolabı gibi bir şey arıyorum"
                visual_type_label = "Mini buzdolabı / içecek soğutucu"

        with t2:
            if st.button("Laptop örneği", width="stretch"):
                description = "Öğrenci için ders ve sunum yapmalık bilgisayar"
                visual_type_label = "Laptop / bilgisayar"

        if st.button("Görselden Ürün Ara", width="stretch", type="primary"):
            filename = uploaded_file.name if uploaded_file is not None else ""
            image_bytes = uploaded_file.getvalue() if uploaded_file is not None and use_gemini_vision else None
            manual_type_text = type_to_query.get(visual_type_label, "")

            visual_query_data = build_visual_query_from_image(
                image_bytes=image_bytes,
                filename=filename,
                manual_description=description,
                manual_type_text=manual_type_text,
            )

            generated_query = visual_query_data.get("generated_query", "")
            combined_description = visual_query_data.get("combined_description", "")
            detected_types = visual_query_data.get("detected_types", [])
            gemini_result = visual_query_data.get("gemini_result", {})

            results, vision_info = visual_search_products(
                products_df,
                description=combined_description,
                filename=filename,
                top_k=8,
                detected_types=detected_types,
            )

            vision_info["gemini_result"] = gemini_result
            vision_info["generated_query"] = generated_query
            vision_info["manual_type"] = visual_type_label

            st.session_state.last_results = results
            st.session_state.last_vision_info = vision_info

            if generated_query:
                try:
                    ai_results, query_info, answer = recommend_products_with_new_ai(products_df, generated_query)

                    # Görsel eşleşmesi boş değilse onu koruyoruz.
                    # Böylece buzdolabı görselinde müşteri AI yanlışlıkla TV'ye kayarsa liste bozulmaz.
                    if results is not None and not results.empty:
                        st.session_state.last_results = results
                    elif ai_results is not None and not ai_results.empty:
                        st.session_state.last_results = ai_results

                    st.session_state.last_query_info = query_info
                    st.session_state.customer_messages.append(
                        {
                            "role": "user",
                            "text": f"Görsel arama: {generated_query}",
                            "time": datetime.now().strftime("%H:%M"),
                        }
                    )
                    st.session_state.customer_messages.append(
                        {
                            "role": "assistant",
                            "text": answer,
                            "time": datetime.now().strftime("%H:%M"),
                        }
                    )

                except Exception as e:
                    st.warning(f"Görsel arama çalıştı ama müşteri AI pipeline bağlantısında hata oluştu: {e}")

            st.rerun()

    with right:
        sub_head("Görsel Arama Sonucu")

        if st.session_state.last_vision_info:
            with st.expander("Vision Info", expanded=False):
                st.json(st.session_state.last_vision_info)

        if st.session_state.last_results is None or st.session_state.last_results.empty:
            st.info("Henüz görsel arama sonucu yok.")
        else:
            for index, row in st.session_state.last_results.iterrows():
                product_card(row, f"vision_{index}")


# =====================================================
# APP
# =====================================================

products_df = prepare_products(load_products())

if not st.session_state.logged_in:
    render_login_page()
else:
    render_app_header()
    render_topbar()

    if st.session_state.cart_notice:
        st.success(st.session_state.cart_notice)
        st.session_state.cart_notice = ""

    page = st.session_state.page

    if page == "dashboard":
        dashboard(products_df)

    elif page == "customer_ai":
        customer_page(products_df)

    elif page == "store_ai":
        store_page(products_df)

    elif page == "quick_actions":
        quick_page()

    elif page == "cart_checkout":
        cart_page()

    elif page == "orders":
        orders_page()

    elif page == "compare":
        compare_page()

    elif page == "products":
        products_page(products_df)

    elif page == "memory":
        memory_page()

    elif page == "metrics":
        metrics_page()

    elif page == "vision":
        vision_page(products_df)

    else:
        dashboard(products_df)