import os
import re
import html
import unicodedata
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# =====================================================
# OPSİYONEL PROJE IMPORTLARI
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


try:
    from src.decision_engine import make_decision, safe_number, money
except Exception:
    safe_number = safe_number_local
    money = money_local

    def make_decision(products_df, query_info):
        query = query_info.get("normalized_query", normalize_text(query_info.get("raw_query", "")))
        budget = safe_number(query_info.get("budget", 0))

        df = products_df.copy()

        def row_score(row):
            score = 0
            text = normalize_text(" ".join(str(row.get(col, "")) for col in df.columns))

            for token in query.split():
                if len(token) > 2 and token in text:
                    score += 5

            if budget and safe_number(row.get("price", 0)) <= budget:
                score += 12

            if "senet" in query and safe_number(row.get("senet_total_price", 0)) > 0:
                score += 12

            if "havale" in query and safe_number(row.get("bank_transfer_price", 0)) > 0:
                score += 12

            if "taksit" in query and safe_number(row.get("installment_6_total", 0)) > 0:
                score += 10

            if normalize_text(row.get("stock_status", "")) == "stokta":
                score += 4

            return score

        if not df.empty:
            df["score"] = df.apply(row_score, axis=1)
            df = df.sort_values("score", ascending=False)

            if df["score"].max() > 0:
                df = df[df["score"] > 0]

        return {
            "result_df": df.head(8),
            "query_info": query_info,
            "decision": "Karar motoru ürünleri sıraladı.",
            "fallback_answer": "Talebinize göre en uygun ürünleri listeledim.",
        }


try:
    from src.nlp_engine import analyze_query
except Exception:
    def analyze_query(query):
        q = normalize_text(query)

        nums = re.findall(r"\d+", q.replace(".", ""))
        budget = None

        if nums:
            big_nums = [int(x) for x in nums if len(x) >= 4]
            budget = max(big_nums) if big_nums else None

        payments = []

        if "senet" in q or "elden odeme" in q:
            payments.append("senet")

        if "havale" in q:
            payments.append("havale")

        if "taksit" in q:
            payments.append("taksit")

        return {
            "raw_query": query,
            "normalized_query": q,
            "budget": budget,
            "payments": payments,
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
        return query_info

    def update_customer_context(context, query_info):
        new_context = dict(context or {})
        new_context.update(query_info or {})
        return new_context


try:
    from src.package_engine import is_package_request, make_package_decision
except Exception:
    def is_package_request(query_info):
        q = normalize_text(query_info.get("raw_query", "") or query_info.get("normalized_query", ""))
        return any(word in q for word in ["ceyiz", "paket", "set", "ev diziyorum"])

    def make_package_decision(products_df, query_info):
        result = make_decision(products_df, query_info)
        df = result.get("result_df", pd.DataFrame()).copy()

        if not df.empty:
            df["package_group"] = df["category"]

        result["result_df"] = df.head(8)
        result["decision"] = "Paket / çeyiz talebi algılandı."
        return result


try:
    from src.semantic_engine import apply_semantic_reranking
except Exception:
    def apply_semantic_reranking(result_df, user_query):
        return result_df


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
    from llm_service import generate_store_llm_answer, product_row_to_dict

    try:
        from llm_service import is_llm_ready
        LLM_READY = is_llm_ready()
    except Exception:
        LLM_READY = True

except Exception:
    generate_store_llm_answer = None
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
# ULTRA PREMIUM CSS
# =====================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    .block-container {
        max-width: 1680px;
        padding-top: 0rem !important;
        padding-bottom: 4rem !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 8%, rgba(30, 64, 175, 0.20), transparent 28%),
            radial-gradient(circle at 92% 8%, rgba(124, 58, 237, 0.18), transparent 32%),
            radial-gradient(circle at 48% 95%, rgba(245, 158, 11, 0.12), transparent 34%),
            linear-gradient(135deg, #f8fafc 0%, #eef2ff 42%, #f8fafc 100%);
        color: #0f172a;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px);
        background-size: 42px 42px;
        mask-image: linear-gradient(to bottom, rgba(0,0,0,0.55), transparent 75%);
        pointer-events: none;
        z-index: 0;
    }

    section.main > div {
        position: relative;
        z-index: 1;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 32px !important;
        border: 1px solid rgba(255, 255, 255, 0.75) !important;
        background:
            linear-gradient(145deg, rgba(255,255,255,0.92), rgba(255,255,255,0.72)) !important;
        box-shadow:
            0 28px 80px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.92);
        backdrop-filter: blur(28px);
    }

    .stButton > button {
        border-radius: 18px !important;
        min-height: 50px !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        letter-spacing: 0.2px;
        border: 1px solid rgba(226, 232, 240, 0.95) !important;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.92)) !important;
        color: #1e3a8a !important;
        box-shadow:
            0 14px 34px rgba(15, 23, 42, 0.055),
            inset 0 1px 0 rgba(255,255,255,0.9);
        transition: all 0.22s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px) scale(1.01);
        background:
            linear-gradient(135deg, #1e3a8a 0%, #4c1d95 55%, #7c2d12 100%) !important;
        color: #ffffff !important;
        border-color: transparent !important;
        box-shadow:
            0 24px 55px rgba(30, 58, 138, 0.26),
            0 8px 20px rgba(124, 58, 237, 0.14);
    }

    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 18px !important;
        border: 1px solid rgba(203, 213, 225, 0.82) !important;
        background: rgba(255,255,255,0.92) !important;
        box-shadow:
            inset 0 1px 2px rgba(15,23,42,0.035),
            0 12px 30px rgba(15, 23, 42, 0.035);
        min-height: 50px !important;
        font-size: 14px !important;
    }

    div[data-testid="stMetric"] {
        background:
            radial-gradient(circle at 0% 0%, rgba(30,64,175,0.08), transparent 38%),
            linear-gradient(145deg, rgba(255,255,255,0.96), rgba(255,255,255,0.78));
        border: 1px solid rgba(255,255,255,0.78);
        border-radius: 28px;
        padding: 26px;
        box-shadow:
            0 24px 65px rgba(15, 23, 42, 0.07),
            inset 0 1px 0 rgba(255,255,255,0.9);
    }

    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-weight: 800 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 950 !important;
        letter-spacing: -1px;
    }

    .brand-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: 999px;
        background:
            linear-gradient(135deg, rgba(30,64,175,0.10), rgba(124,58,237,0.10));
        border: 1px solid rgba(30, 64, 175, 0.16);
        color: #1e3a8a;
        font-size: 11px;
        font-weight: 950;
        text-transform: uppercase;
        letter-spacing: 1.6px;
        margin-bottom: 18px;
        box-shadow: 0 12px 30px rgba(30,64,175,0.08);
    }

    .hero-title {
        font-size: clamp(42px, 5vw, 72px);
        line-height: 0.98;
        letter-spacing: -3.2px;
        font-weight: 950;
        color: #020617;
        margin: 0 0 24px 0;
    }

    .hero-title span {
        background: linear-gradient(90deg, #1e3a8a 0%, #6d28d9 48%, #b45309 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        max-width: 920px;
        color: #475569;
        font-size: 18px;
        line-height: 1.78;
        font-weight: 500;
        margin-bottom: 32px;
    }

    .section-head {
        font-size: 38px;
        line-height: 1.12;
        font-weight: 950;
        color: #020617;
        margin-bottom: 8px;
        letter-spacing: -1.4px;
    }

    .section-desc {
        color: #475569;
        font-size: 15.5px;
        line-height: 1.72;
        margin-bottom: 26px;
        max-width: 950px;
    }

    .module-card,
    .premium-card,
    .order-card,
    .quick-result-box,
    .success-hero {
        background:
            radial-gradient(circle at 0% 0%, rgba(30,64,175,0.08), transparent 38%),
            linear-gradient(145deg, rgba(255,255,255,0.96), rgba(255,255,255,0.78));
        border: 1px solid rgba(255,255,255,0.82);
        border-radius: 30px;
        padding: 28px;
        box-shadow:
            0 28px 70px rgba(15, 23, 42, 0.07),
            inset 0 1px 0 rgba(255,255,255,0.9);
    }

    .module-card {
        min-height: 210px;
        transition: 0.22s ease;
    }

    .module-card:hover {
        transform: translateY(-4px);
        box-shadow:
            0 38px 90px rgba(15, 23, 42, 0.11),
            inset 0 1px 0 rgba(255,255,255,0.95);
    }

    .module-card h3,
    .premium-card h3 {
        margin: 0 0 12px 0;
        color: #020617;
        font-size: 23px;
        font-weight: 950;
        letter-spacing: -0.5px;
    }

    .module-card p,
    .premium-card p {
        color: #475569;
        line-height: 1.72;
        font-size: 14.5px;
        margin: 0;
        font-weight: 500;
    }

    .product-price {
        font-size: 36px;
        font-weight: 950;
        background: linear-gradient(90deg, #1e3a8a, #6d28d9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 12px 0;
        letter-spacing: -1px;
    }

    .topbar-title {
        font-size: 27px;
        font-weight: 950;
        color: #020617;
        letter-spacing: -0.9px;
    }

    .mini-cart {
        background:
            radial-gradient(circle at 0% 0%, rgba(245,158,11,0.16), transparent 38%),
            radial-gradient(circle at 100% 0%, rgba(124,58,237,0.11), transparent 38%),
            linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.72));
        border: 1px solid rgba(255,255,255,0.78);
        border-radius: 30px;
        padding: 20px 24px;
        margin: 14px 0 24px 0;
        box-shadow:
            0 26px 65px rgba(15,23,42,0.07),
            inset 0 1px 0 rgba(255,255,255,0.9);
        backdrop-filter: blur(24px);
    }

    .mini-cart-title {
        color: #020617;
        font-size: 17px;
        font-weight: 950;
        margin-bottom: 5px;
        letter-spacing: -0.3px;
    }

    .mini-cart-sub {
        color: #475569;
        font-size: 13.5px;
        line-height: 1.65;
        font-weight: 600;
    }

    .package-box {
        background:
            linear-gradient(135deg, rgba(124,58,237,0.09), rgba(30,64,175,0.06));
        border: 1px solid rgba(124,58,237,0.18);
        border-radius: 18px;
        padding: 13px 17px;
        color: #4c1d95;
        font-size: 13.5px;
        font-weight: 900;
        margin-bottom: 14px;
        box-shadow: 0 14px 34px rgba(124,58,237,0.07);
    }

    .decision-box,
    .soft-note {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.94), rgba(255,255,255,0.76));
        border: 1px solid rgba(255,255,255,0.80);
        border-radius: 22px;
        padding: 18px 22px;
        color: #475569;
        font-size: 13.5px;
        line-height: 1.75;
        box-shadow: 0 18px 44px rgba(15,23,42,0.045);
    }

    .decision-box {
        background:
            linear-gradient(135deg, rgba(30,64,175,0.07), rgba(124,58,237,0.06));
        border-color: rgba(30,64,175,0.14);
        color: #1e3a8a;
        font-weight: 700;
    }

    .order-title {
        font-size: 23px;
        font-weight: 950;
        color: #020617;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }

    .order-detail {
        color: #475569;
        font-size: 14px;
        line-height: 1.82;
        font-weight: 500;
    }

    .status-pill {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 999px;
        background:
            linear-gradient(135deg, rgba(34,197,94,0.10), rgba(30,64,175,0.08));
        color: #166534;
        border: 1px solid rgba(34,197,94,0.20);
        font-size: 12px;
        font-weight: 950;
        margin-bottom: 10px;
    }

    .luxury-kpi {
        background: linear-gradient(135deg, #020617 0%, #1e1b4b 48%, #451a03 100%);
        border-radius: 34px;
        padding: 28px;
        color: white;
        box-shadow:
            0 36px 90px rgba(15, 23, 42, 0.26),
            inset 0 1px 0 rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.16);
    }

    .luxury-kpi h3 {
        font-size: 22px;
        font-weight: 950;
        margin: 0 0 8px 0;
        letter-spacing: -0.5px;
    }

    .luxury-kpi p {
        color: rgba(255,255,255,0.72);
        font-size: 14px;
        line-height: 1.7;
        margin: 0;
    }

    .premium-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(30,64,175,0.18), rgba(124,58,237,0.18), transparent);
        margin: 24px 0;
    }

    @media(max-width: 980px) {
        .hero-title {
            font-size: 42px;
            letter-spacing: -1.6px;
        }

        .section-head {
            font-size: 30px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
init_state("support_result", None)
init_state("quick_action_history", [])
init_state("customer_context", create_empty_customer_context())

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
    "admin@nevade.com": {"password": "1234", "role": "admin"},
    "magaza@nevade.com": {"password": "1234", "role": "store"},
    "musteri@nevade.com": {"password": "1234", "role": "customer"},
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
        "senet_uygunluk": ["senet", "elden odeme"],
        "odeme": ["odeme", "havale", "kart", "taksit", "pesin"],
        "stok": ["stok", "var mi"],
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


def store_fallback(question, row):
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
    order = find_order(question)

    if order:
        return order_text(order)

    intents = detect_store_intent(question)
    query_info = analyze_query(question)

    if is_package_request(query_info):
        result = make_package_decision(products_df, query_info)
    else:
        result = make_decision(products_df, query_info)

    result_df = result.get("result_df", pd.DataFrame())

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        result_df = apply_semantic_reranking(result_df, question)

    if result_df.empty:
        return (
            "Müşteri talebini net bir ürünle eşleştiremedim. "
            "Ürün adı, marka, kategori veya sipariş numarasını netleştirin."
        )

    row = result_df.iloc[0]

    prompt = f"""
Sen Nevade.com mağaza personeline destek veren üst segment satış asistanısın.

Kurallar:
- Sadece doğrulanmış veriyi kullan.
- Fiyat uydurma.
- Ürün uydurma.
- Türkçe cevap ver.
- Promptu cevaba yazma.

Personel sorusu:
{question}

Algılanan niyetler:
{intents}

Doğrulanmış ürün verisi:
{product_context(row)}

Cevap formatı:
Müşteri talebi:
Müşteriye söylenecek hazır cevap:
Ürün ve ödeme özeti:
Satış yönlendirmesi:
Personel aksiyonu:
"""

    if call_best_available_llm:
        try:
            result = call_best_available_llm(prompt)
            answer = result.get("answer") if isinstance(result, dict) else result

            if answer and len(str(answer)) > 80 and "prompt" not in normalize_text(answer):
                return str(answer).strip()

        except Exception as e:
            print("LLM router hata:", e)

    if LLM_READY and generate_store_llm_answer:
        try:
            answer = generate_store_llm_answer(
                store_question=question,
                intents=intents,
                product_dict=product_context(row),
                order_dict={},
            )

            if answer and len(str(answer)) > 80 and "prompt" not in normalize_text(answer):
                return str(answer).strip()

        except Exception as e:
            print("Store LLM hata:", e)

    return store_fallback(question, row)


def recommend_products_with_new_ai(products_df, user_query):
    query_info = analyze_query(user_query)

    query_info = apply_customer_context(
        query_info,
        st.session_state.customer_context,
    )

    if is_package_request(query_info):
        result = make_package_decision(products_df, query_info)
    else:
        result = make_decision(products_df, query_info)

    result_df = result.get("result_df", pd.DataFrame())

    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        result_df = apply_semantic_reranking(result_df, user_query)

    result["result_df"] = result_df

    try:
        answer = generate_customer_answer_with_llm(result)

        if not answer or len(str(answer)) < 20:
            answer = result.get("fallback_answer", "")

    except Exception:
        answer = result.get("fallback_answer", "")

    st.session_state.customer_context = update_customer_context(
        st.session_state.customer_context,
        query_info,
    )

    st.session_state.last_decision = result.get("decision", "")

    return result_df, result.get("query_info", query_info), answer


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


def chat_panel(messages, empty_text, title, mode):
    user_label = "Mağaza Yetkilisi" if mode == "store" else "Müşteri"

    if not messages:
        body = f"""
        <div class="empty-chat">
            <div>
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

            bubbles.append(
                f"""
                <div class="msg-row {css_type}-row">
                    <div class="msg-bubble {css_type}-bubble">
                        <div class="msg-label">{label}</div>
                        <div>{text_to_html(message.get("text", ""))}</div>
                    </div>
                </div>
                """
            )

        body = "".join(bubbles)

    status = "Yapay Zeka Aktif" if LLM_READY else "Algoritma Aktif"

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
        height: 640px;
        border-radius: 34px;
        overflow: hidden;
        background:
            radial-gradient(circle at 0% 0%, rgba(30,64,175,.09), transparent 36%),
            linear-gradient(145deg, rgba(255,255,255,.96), rgba(255,255,255,.78));
        border: 1px solid rgba(255,255,255,.82);
        box-shadow:
            0 34px 90px rgba(15,23,42,.10),
            inset 0 1px 0 rgba(255,255,255,.90);
    }}

    .chat-header {{
        padding: 24px 28px;
        border-bottom: 1px solid rgba(226,232,240,.95);
        background:
            radial-gradient(circle at 0% 0%, rgba(30,64,175,.11), transparent 38%),
            radial-gradient(circle at 100% 0%, rgba(124,58,237,.11), transparent 38%),
            linear-gradient(135deg, #fff, #f8fafc);
    }}

    .chat-topline {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }}

    .chat-title {{
        font-size: 23px;
        font-weight: 950;
        color: #020617;
        letter-spacing: -.6px;
    }}

    .chat-status {{
        padding: 8px 13px;
        border-radius: 999px;
        background: rgba(30,64,175,.08);
        border: 1px solid rgba(30,64,175,.14);
        color: #1e3a8a;
        font-size: 11px;
        font-weight: 950;
        white-space: nowrap;
    }}

    .chat-sub {{
        margin-top: 8px;
        color: #64748b;
        font-size: 13px;
        line-height: 1.6;
        font-weight: 600;
    }}

    .chat-scroll {{
        height: 525px;
        overflow-y: auto;
        padding: 26px;
        box-sizing: border-box;
        background:
            radial-gradient(circle at 10% 12%, rgba(30,64,175,.05), transparent 35%),
            radial-gradient(circle at 90% 80%, rgba(245,158,11,.06), transparent 36%),
            #fbfcfe;
        scroll-behavior: smooth;
    }}

    .msg-row {{
        display: flex;
        margin-bottom: 16px;
    }}

    .user-row {{
        justify-content: flex-end;
    }}

    .ai-row {{
        justify-content: flex-start;
    }}

    .msg-bubble {{
        max-width: 84%;
        padding: 16px 19px;
        border-radius: 24px;
        font-size: 14px;
        line-height: 1.78;
        word-break: break-word;
        animation: fadeIn .22s ease-out;
    }}

    .user-bubble {{
        color: white;
        background: linear-gradient(135deg, #1e3a8a, #4c1d95, #7c2d12);
        border-bottom-right-radius: 7px;
        box-shadow: 0 18px 38px rgba(30,64,175,.22);
    }}

    .ai-bubble {{
        color: #243b53;
        background: #ffffff;
        border: 1px solid rgba(226,232,240,.96);
        border-bottom-left-radius: 7px;
        box-shadow: 0 16px 35px rgba(30,64,175,.08);
    }}

    .msg-label {{
        font-size: 11px;
        font-weight: 950;
        letter-spacing: .45px;
        text-transform: uppercase;
        opacity: .72;
        margin-bottom: 7px;
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

    .empty-title {{
        font-size: 25px;
        font-weight: 950;
        color: #020617;
        margin-bottom: 8px;
    }}

    .empty-text {{
        font-size: 14px;
        line-height: 1.7;
        margin-bottom: 18px;
    }}

    .empty-suggestion {{
        max-width: 520px;
        padding: 14px 18px;
        border-radius: 18px;
        background: rgba(30,64,175,.05);
        border: 1px solid rgba(30,64,175,.12);
        color: #1e3a8a;
        font-size: 13px;
        line-height: 1.55;
        font-weight: 800;
    }}

    @keyframes fadeIn {{
        from {{
            opacity: 0;
            transform: translateY(6px);
        }}

        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    </style>
    </head>

    <body>
        <div class="chat-shell">
            <div class="chat-header">
                <div class="chat-topline">
                    <div class="chat-title">{escape_html_text(title)}</div>
                    <div class="chat-status">{status}</div>
                </div>
                <div class="chat-sub">
                    Yeni mesaj geldiğinde konuşma otomatik en alta kayar. Karar motoru veriyi doğrular, LLM cevabı premium dile çevirir.
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

    components.html(html_code, height=665, scrolling=False)


def render_mini_cart_bar():
    item_count = sum(int(item.get("quantity", 1)) for item in st.session_state.cart)
    total = get_cart_total()
    last_order = get_last_order()
    last_order_no = last_order.get("order_id", "-") if last_order else "-"

    st.markdown(
        f"""
        <div class="mini-cart">
            <div class="mini-cart-title">Canlı Ticaret Durumu</div>
            <div class="mini-cart-sub">
                Sepet: <b>{item_count} ürün</b> |
                Sepet toplamı: <b>{money(total)}</b> |
                Sipariş: <b>{len(st.session_state.orders)}</b> |
                Son sipariş: <b>{last_order_no}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topbar():
    role = {
        "admin": "Sistem Yöneticisi",
        "store": "Mağaza Çalışanı",
        "customer": "Değerli Müşterimiz",
    }.get(st.session_state.user_role, "Kullanıcı")

    with st.container(border=True):
        left, right = st.columns([2.5, 1], gap="large")

        with left:
            st.markdown('<div class="topbar-title">Nevade AI Commerce Hub</div>', unsafe_allow_html=True)
            st.caption("LLM destekli alışveriş asistanı, karar motoru, sepet, sipariş ve mağaza operasyon paneli")

        with right:
            st.write(f"**Rol:** {role}")
            st.caption(st.session_state.user_email)

        columns = st.columns(9)

        pages = [
            ("dashboard", "Kontrol Paneli"),
            ("customer_ai", "Müşteri AI"),
            ("store_ai", "Mağaza AI"),
            ("quick_actions", "Hızlı İşlemler"),
            ("cart_checkout", "Sepet / Sipariş"),
            ("orders", "Siparişler"),
            ("compare", "Karşılaştır"),
            ("products", "Katalog"),
        ]

        for index, (page_id, label) in enumerate(pages):
            with columns[index]:
                if st.button(label, use_container_width=True, key=f"nav_{page_id}"):
                    go_page(page_id)

        with columns[8]:
            if st.button("Çıkış", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_role = ""
                st.session_state.page = "dashboard"
                st.rerun()

    render_mini_cart_bar()


def product_card(row, key_prefix, query_info=None, compact=False):
    product_id = clean_str(row.get("product_id", "")) or f"{key_prefix}_{abs(hash(row.get('product_name', 'urun')))}"

    with st.container(border=True):
        image_col, info_col = st.columns([1, 2.7], gap="large")

        with image_col:
            image_link = clean_str(row.get("image_link", ""))

            if image_link:
                try:
                    st.image(image_link, use_container_width=True)
                except Exception:
                    st.info("Görsel yüklenemedi")
            else:
                st.info("Görsel Mevcut Değil")

        with info_col:
            if clean_str(row.get("package_group", "")):
                st.markdown(
                    f'<div class="package-box">Paket Kategorisi: {row.get("package_group")}</div>',
                    unsafe_allow_html=True,
                )

            percent = ai_percent(row)

            if percent >= 90:
                label = "Çok Uygun"
            elif percent >= 80:
                label = "Uygun"
            elif percent >= 70:
                label = "Değerlendirilebilir"
            else:
                label = "Düşük Eşleşme"

            st.markdown(f"### {row.get('product_name', 'İsimsiz Ürün')}")
            st.caption(f"Kategori: {row.get('category', '-')} | Marka: {row.get('brand', '-')}")

            st.markdown(f"**Yapay Zeka Uygunluk Skoru:** %{percent} — **{label}**")

            tags = []

            if normalize_text(row.get("stock_status", "")) == "stokta":
                tags.append("Stokta")

            if safe_number(row.get("bank_transfer_price", 0)) > 0:
                tags.append("Havale Avantajı")

            if safe_number(row.get("senet_total_price", 0)) > 0:
                tags.append("Senetli Ödeme")

            if tags:
                st.write(" ".join([f"[{tag}]" for tag in tags]))

            st.markdown(
                f'<div class="product-price">{money(row.get("price", 0))}</div>',
                unsafe_allow_html=True,
            )

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
                        st.success(
                            f"Toplam tutarda en avantajlı seçenek: {values['best_option'][0]} - {money(values['best_option'][1])}"
                        )

                    if values["senet_total"] > 0:
                        st.info(
                            f"Aylık düşük ödeme için senetli seçenek anlatılabilir: {money(values['senet_monthly'])}/ay"
                        )

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("Sepete Ekle", key=f"cart_{key_prefix}_{product_id}", use_container_width=True):
                    add_product_to_cart(row)
                    st.rerun()

            with b2:
                if st.button("Karşılaştır", key=f"comp_{key_prefix}_{product_id}", use_container_width=True):
                    existing_ids = [str(item.get("product_id")) for item in st.session_state.compare_items]

                    if str(product_id) not in existing_ids:
                        st.session_state.compare_items.append(row.to_dict() if hasattr(row, "to_dict") else dict(row))
                        st.success("Karşılaştırma listesine eklendi.")
                    else:
                        st.info("Bu ürün zaten karşılaştırma listesinde.")

            with b3:
                if row.get("product_link"):
                    st.link_button("Ürüne Git", row.get("product_link"), use_container_width=True)


def order_card(order):
    st.markdown(
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
        st.dataframe(pd.DataFrame(order.get("items", [])), use_container_width=True)


# =====================================================
# PAGES
# =====================================================

def render_login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)

    left, right = st.columns([1.2, 0.9], gap="large")

    with left:
        st.markdown(
            """
            <div class="brand-badge">NEVADE AI COMMERCE HUB</div>
            <h1 class="hero-title">
                E-ticareti<br>
                <span>LLM + karar motoru</span><br>
                seviyesine taşı.
            </h1>
            <p class="hero-subtitle">
                Ürün önerisi, çeyiz paketi, senetli ödeme, havale avantajı,
                mağaza personel desteği, sipariş takibi ve müşteri hizmetleri akışını
                tek premium panelde birleştiren yapay zeka destekli ticaret asistanı.
            </p>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)

        cards = [
            (
                "CORE ENGINE",
                "Karar Motoru",
                "Ürünü, bütçeyi, stok durumunu ve ödeme alternatiflerini güvenli veri üzerinden seçer. LLM’in fiyat uydurmasını engeller.",
            ),
            (
                "LLM LAYER",
                "Satış Dili AI",
                "Karar motorunun doğruladığı veriyi müşteri ve mağaza personeli için doğal, ikna edici ve profesyonel cevaba dönüştürür.",
            ),
            (
                "OPS HUB",
                "Operasyon Merkezi",
                "Sepet, sipariş, kargo, fatura, iade ve mağaza destek süreçlerini tek premium panelde birleştirir.",
            ),
        ]

        for col, (badge, title, desc) in zip([c1, c2, c3], cards):
            with col:
                st.markdown(
                    f"""
                    <div class="module-card">
                        <div class="brand-badge">{badge}</div>
                        <h3>{title}</h3>
                        <p>{desc}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align:center; margin-bottom:22px;">
                    <div class="brand-badge">GÜVENLİ GİRİŞ</div>
                    <h2 style="font-size:31px; font-weight:950; color:#0f172a; margin-bottom:8px;">
                        Nevade Panel
                    </h2>
                    <p style="color:#475569; font-size:14px; line-height:1.7;">
                        Rolünüze göre müşteri, mağaza ve yönetim ekranlarına erişin.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            email = st.text_input("Kullanıcı E-Posta Adresi", value="admin@nevade.com")
            password = st.text_input("Şifre", value="1234", type="password")

            if st.button("Sisteme Giriş Yap", use_container_width=True):
                if email in USERS and USERS[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_role = USERS[email]["role"]
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Hatalı e-posta adresi veya şifre.")

            st.markdown("---")

            st.markdown(
                """
                <div class="soft-note">
                    <b>Demo hesaplar</b><br><br>
                    admin@nevade.com / 1234<br>
                    magaza@nevade.com / 1234<br>
                    musteri@nevade.com / 1234
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        st.metric("AI Katmanı", "LLM + Rule", "Güvenli hibrit yapı")

    with b2:
        st.metric("Sepet Akışı", "Aktif", "Ürün -> Sepet -> Sipariş")

    with b3:
        st.metric("Destek", "Aktif", "Kargo, fatura, iade")

    with b4:
        st.metric("LLM Durumu", "Hazır" if LLM_READY else "Fallback", "Doğal cevap motoru")


def dashboard(products_df):
    st.markdown('<div class="brand-badge">EXECUTIVE COMMERCE DASHBOARD</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Nevade AI <span>Yönetim Paneli</span></h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-subtitle">Karar motoru güvenli veriyi seçer, LLM bu veriyi satışa ve müşteri deneyimine uygun dile dönüştürür.</p>',
        unsafe_allow_html=True,
    )

    a, b, c, d = st.columns(4)

    with a:
        st.metric("Toplam Ürün", len(products_df))

    with b:
        st.metric("Sipariş", len(st.session_state.orders))

    with c:
        st.metric("Sepet Ürün", sum(int(item.get("quantity", 1)) for item in st.session_state.cart))

    with d:
        st.metric("Sepet Toplamı", money(get_cart_total()))

    st.write("")

    st.markdown(
        """
        <div class="luxury-kpi">
            <h3>Nevade AI Commerce Hub — Üst Segment Demo</h3>
            <p>
                Bu panelde LLM doğrudan ürün veya fiyat kararı vermez. Önce karar motoru doğrulanmış ürün,
                stok, fiyat ve ödeme verisini seçer. LLM yalnızca bu güvenli veriyi müşteri ve mağaza personeli
                diline çevirir.
            </p>
        </div>
        <div class="premium-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown(
            """
            <div class="premium-card">
                <h3>LLM Kontrollü Ticaret Akışı</h3>
                <p><b>1. NLP:</b> Kullanıcı niyetini algılar.</p>
                <p><b>2. Karar Motoru:</b> Doğru ürün, stok, fiyat ve ödeme seçeneğini seçer.</p>
                <p><b>3. LLM:</b> Veriyi doğal müşteri/personel diline çevirir.</p>
                <p><b>4. Fallback:</b> LLM kötü cevap verirse güvenli premium cevap üretir.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("### Canlı Operasyon Özeti")

        if not st.session_state.cart:
            st.info("Sepet şu anda boş.")
        else:
            for item in st.session_state.cart:
                quantity = int(item.get("quantity", 1))
                price = safe_number(item.get("price", 0))
                st.write(f"- **{item.get('product_name')}** x {quantity} - {money(price * quantity)}")

            if st.button("Sepeti Temizle", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

        st.markdown("### Son Sipariş")
        st.info(order_text(get_last_order()))


def customer_page(products_df):
    st.markdown('<div class="brand-badge">CUSTOMER AI EXPERIENCE</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Akıllı Müşteri Asistanı</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">Müşteri doğal dilde yazar; sistem ürün, ödeme ve uygunluk kararını üretir.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.45, 2], gap="large")

    with left:
        chat_panel(
            st.session_state.customer_messages,
            "Müşteri asistanı hazır. Bir ürün, bütçe veya ödeme isteği yazın.",
            "Müşteri AI",
            "customer",
        )

        with st.form("customer_form", clear_on_submit=True):
            question = st.text_input(
                "Müşteri Talebi",
                placeholder="Örn: 50000 TL çeyiz paketi istiyorum, senetli olsun",
            )
            submitted = st.form_submit_button("Gönder", use_container_width=True)

        if submitted and question.strip():
            st.session_state.customer_messages.append({"role": "user", "text": question})

            with st.spinner("Karar motoru ve LLM birlikte çalışıyor..."):
                results, query_info, answer = recommend_products_with_new_ai(products_df, question)
                st.session_state.last_results = results
                st.session_state.last_query_info = query_info
                st.session_state.customer_messages.append({"role": "assistant", "text": answer})

            st.rerun()

        st.markdown("### Hızlı Yanıtlar")

        quick_columns = st.columns(4)

        actions = [
            ("Daha ucuzunu göster", "Daha ucuzu var mı?"),
            ("Senetli ödeme", "Senetli ödeme seçeneğini göster"),
            ("Havale avantajı", "Havale avantajı olan seçenekleri göster"),
            ("Sepete git", "GO_CART"),
        ]

        for index, (label, quick_query) in enumerate(actions):
            with quick_columns[index]:
                if st.button(label, key=f"quick_{index}", use_container_width=True):
                    if quick_query == "GO_CART":
                        go_page("cart_checkout")

                    st.session_state.customer_messages.append({"role": "user", "text": quick_query})
                    results, query_info, answer = recommend_products_with_new_ai(products_df, quick_query)
                    st.session_state.last_results = results
                    st.session_state.last_query_info = query_info
                    st.session_state.customer_messages.append({"role": "assistant", "text": answer})
                    st.rerun()

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Sohbeti Sıfırla", use_container_width=True):
                st.session_state.customer_messages = []
                st.session_state.customer_context = create_empty_customer_context()
                st.session_state.last_results = pd.DataFrame()
                st.rerun()

        with c2:
            if st.button("Sepete Git", use_container_width=True):
                go_page("cart_checkout")

    with right:
        st.markdown("### AI Eşleşen Ürünler")

        if st.session_state.last_query_info:
            with st.expander("Algılanan Müşteri İsteği", expanded=False):
                st.json(st.session_state.last_query_info)
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
    st.markdown('<div class="brand-badge">STORE AI SALES COPILOT</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Mağaza Personel Asistanı</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">Karar motoru doğru veriyi bulur, LLM bunu personele hazır satış cevabı olarak sunar.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.45, 2], gap="large")

    with left:
        chat_panel(
            st.session_state.store_messages,
            "Mağaza personeli için ürün, ödeme, senet, stok ve sipariş sorgusu hazır.",
            "Mağaza AI",
            "store",
        )

        with st.form("store_form", clear_on_submit=True):
            question = st.text_input(
                "Personel Sorusu",
                placeholder="Örn: Beko buzdolabı senetle olur mu, en avantajlı ödeme ne?",
            )
            submitted = st.form_submit_button("Sorgula", use_container_width=True)

        if submitted and question.strip():
            st.session_state.store_messages.append({"role": "store", "text": question})

            with st.spinner("Karar motoru veriyi seçiyor, LLM cevabı hazırlıyor..."):
                answer = store_product_answer(products_df, question)
                st.session_state.store_messages.append({"role": "assistant", "text": answer})

            st.rerun()

        if st.button("Mağaza Sohbetini Temizle", use_container_width=True):
            st.session_state.store_messages = []
            st.rerun()

    with right:
        st.markdown("### Son Siparişler ve Operasyon Durumu")

        for order in st.session_state.orders[-5:][::-1]:
            order_card(order)


def cart_page():
    st.markdown('<div class="brand-badge">CART TO ORDER FLOW</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Sepet ve Sipariş Oluşturma</h2>', unsafe_allow_html=True)

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

    st.markdown("### Sepetteki Ürünler")

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
                if st.button("Kaldır", key=f"remove_{index}", use_container_width=True):
                    st.session_state.cart.pop(index)
                    st.rerun()

    st.markdown("### Sipariş Bilgileri")

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

        submitted = st.form_submit_button("Siparişi Tamamla", use_container_width=True)

    if submitted:
        order = create_order_from_cart(customer_name, address, payment_type, store_name)
        st.session_state.support_result = {
            "action": "Sipariş oluşturuldu",
            "response": order_text(order),
        }
        go_page("orders")


def orders_page():
    st.markdown('<div class="brand-badge">ORDER MANAGEMENT</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Sipariş Yönetimi</h2>', unsafe_allow_html=True)

    if st.session_state.support_result:
        st.markdown(
            f"""
            <div class="success-hero">
                <b>{st.session_state.support_result.get("action")}</b><br><br>
                {text_to_html(st.session_state.support_result.get("response"))}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for order in st.session_state.orders[::-1]:
        order_card(order)


def quick_page():
    st.markdown('<div class="brand-badge">SERVICE OPERATIONS</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Hızlı İşlemler</h2>', unsafe_allow_html=True)

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

        if st.button("İşlemi Çalıştır", use_container_width=True):
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
        st.markdown("### İşlem Sonucu")

        if st.session_state.support_result:
            st.markdown(
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

        st.markdown("### Son Siparişler")

        for order in st.session_state.orders[-3:][::-1]:
            order_card(order)


def compare_page():
    st.markdown('<div class="brand-badge">COMPARISON MATRIX</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Ürün Karşılaştırma</h2>', unsafe_allow_html=True)

    if not st.session_state.compare_items:
        st.info("Karşılaştırma listeniz boş.")
        return

    if st.button("Listeyi Boşalt", use_container_width=True):
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

    st.dataframe(compare_df[visible_cols], use_container_width=True)

    for index, row in compare_df.iterrows():
        product_card(row, f"compare_{index}", compact=True)


def products_page(products_df):
    st.markdown('<div class="brand-badge">PRODUCT CATALOG</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-head">Ürün Kataloğu</h2>', unsafe_allow_html=True)

    with st.expander("Yeni Ürün Ekleme Paneli", expanded=False):
        with st.form("add_product_form"):
            product_id = st.text_input("Ürün Kodu", placeholder="P005")
            product_name = st.text_input("Ürün İsmi")
            category = st.selectbox("Kategori", ["Beyaz Eşya", "Televizyon", "Küçük Ev Aleti", "Cep Telefonu", "Bilgisayar"])
            brand = st.text_input("Marka")
            price = st.number_input("Liste Fiyatı", min_value=0, value=10000)
            stock = st.selectbox("Stok Durumu", ["Stokta", "Tükendi"])
            description = st.text_area("Açıklama")

            submitted = st.form_submit_button("Ürünü Kaydet", use_container_width=True)

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
        for col in ["product_id", "product_name", "category", "brand", "price", "stock_status"]
        if col in products_df.columns
    ]

    st.dataframe(products_df[visible_cols], use_container_width=True)


# =====================================================
# APP
# =====================================================

products_df = prepare_products(load_products())

if not st.session_state.logged_in:
    render_login_page()
else:
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

    else:
        dashboard(products_df)