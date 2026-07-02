import streamlit as st
import pandas as pd

from src.assistant_service import (
    load_products,
    run_customer_assistant,
    run_store_assistant,
    get_quick_customer_prompts,
    get_quick_store_prompts,
    get_ai_capabilities,
    calculate_product_metrics,
    calculate_cart_summary,
    get_products_by_ids,
)

from src.customer_intelligence_engine import money, safe_number


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Nevade AI Personal Shopping Assistant",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================
# PREMIUM CSS
# =====================================================

st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .premium-header {
        background: linear-gradient(135deg, #101828 0%, #1d2939 55%, #344054 100%);
        padding: 28px 32px;
        border-radius: 24px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 20px 50px rgba(16, 24, 40, 0.18);
    }

    .premium-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }

    .premium-subtitle {
        font-size: 15px;
        color: #d0d5dd;
        max-width: 900px;
    }

    .metric-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(208, 213, 221, 0.75);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 30px rgba(16, 24, 40, 0.07);
        min-height: 110px;
    }

    .metric-label {
        color: #667085;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .metric-value {
        color: #101828;
        font-size: 25px;
        font-weight: 800;
    }

    .glass-card {
        background: rgba(255,255,255,0.96);
        border: 1px solid rgba(208, 213, 221, 0.7);
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 12px 35px rgba(16, 24, 40, 0.08);
        margin-bottom: 18px;
    }

    .section-title {
        font-size: 20px;
        font-weight: 800;
        color: #101828;
        margin-bottom: 8px;
    }

    .section-subtitle {
        color: #667085;
        font-size: 13px;
        margin-bottom: 16px;
    }

    .ai-answer {
        background: #ffffff;
        border-left: 6px solid #1d2939;
        border-radius: 18px;
        padding: 22px;
        color: #101828;
        font-size: 15px;
        line-height: 1.65;
        white-space: pre-wrap;
        box-shadow: 0 12px 30px rgba(16, 24, 40, 0.08);
    }

    .badge {
        display: inline-block;
        padding: 7px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 800;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    .badge-success {
        background: #dcfae6;
        color: #067647;
    }

    .badge-warning {
        background: #fef0c7;
        color: #b54708;
    }

    .badge-payment {
        background: #e0f2fe;
        color: #026aa2;
    }

    .badge-budget {
        background: #ede9fe;
        color: #6941c6;
    }

    .badge-package {
        background: #fce7f3;
        color: #c11574;
    }

    .badge-default {
        background: #f2f4f7;
        color: #344054;
    }

    .product-card {
        background: #ffffff;
        border: 1px solid #eaecf0;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 12px 32px rgba(16, 24, 40, 0.08);
        height: 100%;
        margin-bottom: 16px;
    }

    .product-name {
        font-size: 17px;
        font-weight: 800;
        color: #101828;
        line-height: 1.3;
        margin-bottom: 8px;
    }

    .product-meta {
        color: #667085;
        font-size: 13px;
        margin-bottom: 12px;
    }

    .price-main {
        font-size: 23px;
        font-weight: 900;
        color: #101828;
        margin-bottom: 4px;
    }

    .price-label {
        font-size: 12px;
        color: #667085;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .payment-row {
        background: #f8fafc;
        border-radius: 14px;
        padding: 10px 12px;
        margin-top: 8px;
        color: #344054;
        font-size: 13px;
        border: 1px solid #eaecf0;
    }

    .stock-ok {
        color: #067647;
        font-weight: 800;
    }

    .stock-warn {
        color: #b54708;
        font-weight: 800;
    }

    .profile-box {
        background: #101828;
        color: white;
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 16px;
    }

    .profile-title {
        font-size: 14px;
        font-weight: 800;
        color: #f9fafb;
        margin-bottom: 8px;
    }

    .profile-text {
        color: #d0d5dd;
        font-size: 13px;
        line-height: 1.5;
    }

    .capability-card {
        background: #ffffff;
        border: 1px solid #eaecf0;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.06);
        min-height: 130px;
    }

    .capability-title {
        color: #101828;
        font-weight: 800;
        font-size: 15px;
        margin-bottom: 8px;
    }

    .capability-desc {
        color: #667085;
        font-size: 13px;
        line-height: 1.45;
    }

    .small-muted {
        color: #667085;
        font-size: 12px;
    }

    div.stButton > button {
        border-radius: 14px;
        border: 1px solid #d0d5dd;
        background: white;
        color: #101828;
        font-weight: 700;
        padding: 0.55rem 0.9rem;
    }

    div.stButton > button:hover {
        border-color: #101828;
        color: #101828;
        background: #f9fafb;
    }

    .stTextInput > div > div > input {
        border-radius: 16px;
    }

    .stTextArea textarea {
        border-radius: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# SESSION STATE
# =====================================================

if "customer_context" not in st.session_state:
    st.session_state.customer_context = {}

if "store_context" not in st.session_state:
    st.session_state.store_context = {}

if "last_results" not in st.session_state:
    st.session_state.last_results = None

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "cart_ids" not in st.session_state:
    st.session_state.cart_ids = []

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_prompt" not in st.session_state:
    st.session_state.active_prompt = ""


# =====================================================
# DATA
# =====================================================

@st.cache_data
def cached_products():
    return load_products("data/products.csv")


products_df = cached_products()


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def badge_class(badge_type):
    mapping = {
        "success": "badge-success",
        "warning": "badge-warning",
        "payment": "badge-payment",
        "budget": "badge-budget",
        "package": "badge-package",
        "default": "badge-default",
    }
    return mapping.get(badge_type, "badge-default")


def render_header():
    st.markdown(
        """
        <div class="premium-header">
            <div class="premium-title">Nevade AI Personal Shopping Assistant</div>
            <div class="premium-subtitle">
                Kişisel ürün önerisi, sepet terk önleme, bütçe optimizasyonu, ödeme alternatifi,
                mağaza personeli desteği ve lokal LLM destekli akıllı alışveriş deneyimi.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics():
    metrics = calculate_product_metrics(products_df)
    cart_df = get_products_by_ids(products_df, st.session_state.cart_ids)
    cart_metrics = calculate_cart_summary(cart_df)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Toplam Ürün</div>
                <div class="metric-value">{metrics["total_products"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Stokta Ürün</div>
                <div class="metric-value">{metrics["stock_products"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Sepet Toplamı</div>
                <div class="metric-value">{money(cart_metrics["total_price"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Senetli Ürün</div>
                <div class="metric-value">{metrics["senet_products"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_product_card(card, index):
    product_id = card.get("product_id")
    stock = str(card.get("stock_status", ""))

    stock_class = "stock-ok" if stock.lower() == "stokta" else "stock-warn"

    st.markdown(
        f"""
        <div class="product-card">
            <div class="product-name">{card.get("product_name", "")}</div>
            <div class="product-meta">
                {card.get("brand", "")} · {card.get("category", "")}
            </div>

            <div class="price-main">{card.get("best_price_text", "")}</div>
            <div class="price-label">{card.get("best_price_label", "En iyi fiyat")}</div>

            <div class="payment-row">
                Liste fiyatı: <b>{card.get("price_text", "")}</b>
            </div>

            <div class="payment-row">
                Havale: <b>{card.get("bank_transfer_text", "Yok")}</b>
            </div>

            <div class="payment-row">
                6 taksit aylık: <b>{card.get("installment_6_monthly_text", "Yok")}</b>
            </div>

            <div class="payment-row">
                Senetli aylık: <b>{card.get("senet_monthly_text", "Yok")}</b>
            </div>

            <div class="payment-row">
                Stok: <span class="{stock_class}">{stock}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns(2)

    with b1:
        if st.button("Sepete ekle", key=f"cart_{index}_{product_id}"):
            if product_id not in st.session_state.cart_ids:
                st.session_state.cart_ids.append(product_id)
                st.success("Ürün sepete eklendi.")
                st.rerun()

    with b2:
        if st.button("Favori", key=f"fav_{index}_{product_id}"):
            if product_id not in st.session_state.favorites:
                st.session_state.favorites.append(product_id)
                st.success("Ürün favorilere eklendi.")
                st.rerun()


def render_product_cards(cards):
    if not cards:
        st.info("Bu cevap için gösterilecek ürün kartı bulunamadı.")
        return

    st.markdown('<div class="section-title">Önerilen Ürünler</div>', unsafe_allow_html=True)

    for start in range(0, len(cards), 3):
        cols = st.columns(3)
        for i, card in enumerate(cards[start:start + 3]):
            with cols[i]:
                render_product_card(card, start + i)


def run_query(user_query, mode="customer"):
    cart_df = get_products_by_ids(products_df, st.session_state.cart_ids)

    if mode == "store":
        response = run_store_assistant(
            products_df=products_df,
            user_query=user_query,
            customer_context=st.session_state.store_context,
            current_results=st.session_state.last_results,
            cart_df=cart_df,
        )
        st.session_state.store_context["customer_profile"] = response.get("customer_profile")
    else:
        response = run_customer_assistant(
            products_df=products_df,
            user_query=user_query,
            customer_context=st.session_state.customer_context,
            current_results=st.session_state.last_results,
            cart_df=cart_df,
        )
        st.session_state.customer_context["customer_profile"] = response.get("customer_profile")

    st.session_state.last_response = response
    st.session_state.last_results = response.get("result_df")

    st.session_state.chat_history.append(
        {
            "mode": mode,
            "query": user_query,
            "decision": response.get("decision_label"),
            "answer": response.get("answer"),
        }
    )

    return response


def render_response(response):
    if not response:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">AI Cevabı</div>
                <div class="section-subtitle">
                    Bir müşteri ihtiyacı yazın veya hızlı senaryolardan birini seçin.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    badge = badge_class(response.get("decision_badge_type"))

    st.markdown(
        f"""
        <div class="glass-card">
            <span class="badge {badge}">{response.get("decision_label")}</span>
            <span class="badge badge-default">Nevade AI</span>
            <div class="section-title" style="margin-top:10px;">AI Cevabı</div>
            <div class="ai-answer">{response.get("answer", "")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("AI Analiz Detayı"):
        st.write("Karar:", response.get("decision"))
        st.write("Analiz:", response.get("analysis_summary"))
        st.write("Profil:", response.get("profile_summary"))
        st.write("Sepet:", response.get("cart_metrics", {}).get("summary_text", ""))

    render_product_cards(response.get("product_cards", []))


def render_sidebar():
    with st.sidebar:
        st.markdown("## Nevade AI Panel")

        st.markdown("### Müşteri Profili")
        profile_text = st.session_state.customer_context.get("customer_profile")
        if profile_text:
            last_summary = st.session_state.last_response.get("profile_summary") if st.session_state.last_response else ""
            st.markdown(
                f"""
                <div class="profile-box">
                    <div class="profile-title">Aktif Profil</div>
                    <div class="profile-text">{last_summary or "Profil güncellendi."}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Henüz müşteri profili oluşmadı.")

        st.markdown("### Sepet")
        cart_df = get_products_by_ids(products_df, st.session_state.cart_ids)
        cart_metrics = calculate_cart_summary(cart_df)
        st.write(cart_metrics["summary_text"])

        if st.session_state.cart_ids:
            if st.button("Sepeti temizle"):
                st.session_state.cart_ids = []
                st.rerun()

        st.markdown("### Favoriler")
        st.write(f"{len(st.session_state.favorites)} ürün favoride.")

        if st.session_state.favorites:
            if st.button("Favorileri temizle"):
                st.session_state.favorites = []
                st.rerun()

        st.markdown("### Sistem")
        st.caption("LLM sırası: Ollama → Gemini → Güvenli Fallback")
        st.caption("Karar motorları: ürün, sepet, bütçe, ödeme, profil")


# =====================================================
# MAIN UI
# =====================================================

render_sidebar()
render_header()
render_metrics()

tab_customer, tab_store, tab_dashboard, tab_history = st.tabs(
    [
        "Müşteri Asistanı",
        "Mağaza Personeli",
        "AI Dashboard",
        "Konuşma Geçmişi",
    ]
)


# =====================================================
# CUSTOMER TAB
# =====================================================

with tab_customer:
    left, right = st.columns([0.95, 1.35])

    with left:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Kişisel Alışveriş Asistanı</div>
                <div class="section-subtitle">
                    Müşteri ihtiyacını yazın. Sistem ürün önerisi, ödeme alternatifi,
                    sepet kurtarma veya bütçe optimizasyonu akışını otomatik seçer.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        query = st.text_area(
            "Müşteri mesajı",
            value=st.session_state.active_prompt,
            height=120,
            placeholder="Örnek: Kart limitim yetmedi / Annem için kolay telefon öner / 50000 TL çeyiz paketi yap",
        )

        c1, c2 = st.columns([1, 1])

        with c1:
            ask_clicked = st.button("AI Asistana Sor", use_container_width=True)

        with c2:
            if st.button("Temizle", use_container_width=True):
                st.session_state.active_prompt = ""
                st.rerun()

        if ask_clicked and query.strip():
            with st.spinner("Nevade AI analiz ediyor..."):
                response = run_query(query.strip(), mode="customer")
                st.session_state.active_prompt = ""
                st.rerun()

        st.markdown("### Hızlı Senaryolar")

        for prompt in get_quick_customer_prompts():
            if st.button(prompt, key=f"quick_customer_{prompt}", use_container_width=True):
                st.session_state.active_prompt = prompt
                with st.spinner("Nevade AI analiz ediyor..."):
                    response = run_query(prompt, mode="customer")
                st.rerun()

    with right:
        render_response(st.session_state.last_response)


# =====================================================
# STORE TAB
# =====================================================

with tab_store:
    left, right = st.columns([0.95, 1.35])

    with left:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Mağaza Personeli Copilot</div>
                <div class="section-subtitle">
                    Personelin müşteriye ne söyleyeceğini ve hangi aksiyonu alacağını önerir.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        store_query = st.text_area(
            "Personel sorusu",
            height=120,
            placeholder="Örnek: Müşteri kart limitim yetmedi diyor ne önerelim?",
            key="store_query_input",
        )

        if st.button("Personel Asistanına Sor", use_container_width=True):
            if store_query.strip():
                with st.spinner("Personel cevabı hazırlanıyor..."):
                    response = run_query(store_query.strip(), mode="store")
                st.rerun()

        st.markdown("### Personel Hızlı Senaryolar")

        for prompt in get_quick_store_prompts():
            if st.button(prompt, key=f"quick_store_{prompt}", use_container_width=True):
                with st.spinner("Personel cevabı hazırlanıyor..."):
                    response = run_query(prompt, mode="store")
                st.rerun()

    with right:
        render_response(st.session_state.last_response)


# =====================================================
# DASHBOARD TAB
# =====================================================

with tab_dashboard:
    st.markdown(
        """
        <div class="glass-card">
            <div class="section-title">AI Yetenekleri</div>
            <div class="section-subtitle">
                Projede aktif olan kişisel alışveriş asistanı yetenekleri.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    capabilities = get_ai_capabilities()

    for start in range(0, len(capabilities), 3):
        cols = st.columns(3)
        for i, cap in enumerate(capabilities[start:start + 3]):
            with cols[i]:
                st.markdown(
                    f"""
                    <div class="capability-card">
                        <div class="capability-title">{cap["title"]}</div>
                        <div class="capability-desc">{cap["description"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### Ürün Veri Özeti")

    metrics = calculate_product_metrics(products_df)

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Kategori Sayısı", metrics["category_count"])
    m2.metric("Marka Sayısı", metrics["brand_count"])
    m3.metric("Ortalama Fiyat", money(metrics["average_price"]))
    m4.metric("Havale Avantajlı Ürün", metrics["bank_transfer_products"])

    st.markdown("### Ürün Listesi")

    show_cols = [
        col for col in [
            "product_id",
            "product_name",
            "category",
            "brand",
            "price",
            "bank_transfer_price",
            "installment_6_total",
            "senet_total_price",
            "stock_status",
        ]
        if col in products_df.columns
    ]

    st.dataframe(products_df[show_cols], use_container_width=True)


# =====================================================
# HISTORY TAB
# =====================================================

with tab_history:
    st.markdown(
        """
        <div class="glass-card">
            <div class="section-title">Konuşma Geçmişi</div>
            <div class="section-subtitle">
                Bu oturumda yapılan müşteri ve personel görüşmeleri.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_history:
        st.info("Henüz konuşma yok.")
    else:
        for idx, item in enumerate(reversed(st.session_state.chat_history), start=1):
            with st.expander(f"{idx}. {item.get('decision')}"):
                st.write("Mod:", item.get("mode"))
                st.write("Soru:", item.get("query"))
                st.write("Cevap:")
                st.write(item.get("answer"))

    if st.button("Konuşma geçmişini temizle"):
        st.session_state.chat_history = []
        st.rerun()