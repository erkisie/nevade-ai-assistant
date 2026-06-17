import os
import streamlit as st


def apply_nevade_theme():
    st.markdown(
        """
        <style>
        :root {
            --nevade-blue: #1599D6;
            --nevade-cyan: #23B7E5;
            --nevade-navy: #173A5E;
            --nevade-purple: #6B2B8E;
            --nevade-magenta: #C3378A;
            --nevade-bg: #F5F8FF;
            --nevade-card: rgba(255,255,255,0.82);
            --nevade-border: rgba(120, 160, 200, 0.28);
            --nevade-text: #10233D;
            --nevade-muted: #607086;
            --shadow: 0 18px 45px rgba(23, 58, 94, 0.12);
            --soft-shadow: 0 8px 24px rgba(23, 58, 94, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(35,183,229,0.22), transparent 30%),
                radial-gradient(circle at top right, rgba(195,55,138,0.20), transparent 28%),
                linear-gradient(135deg, #F7FBFF 0%, #F6F1FF 52%, #F9FBFF 100%);
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, h4, h5, h6, p, div, span, label {
            font-family: "Segoe UI", Arial, sans-serif !important;
            color: var(--nevade-text);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #FFFFFF 0%, #EEF8FF 100%);
            border-right: 1px solid rgba(21,153,214,0.16);
        }

        .nevade-shell {
            background: rgba(255,255,255,0.62);
            border: 1px solid rgba(255,255,255,0.70);
            border-radius: 30px;
            padding: 22px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            margin-bottom: 22px;
        }

        .nevade-hero {
            background:
                linear-gradient(135deg, rgba(21,153,214,0.98) 0%, rgba(107,43,142,0.96) 62%, rgba(195,55,138,0.92) 100%);
            border-radius: 28px;
            padding: 34px 38px;
            box-shadow: 0 22px 50px rgba(107,43,142,0.20);
            position: relative;
            overflow: hidden;
        }

        .nevade-hero::after {
            content: "";
            position: absolute;
            width: 280px;
            height: 280px;
            right: -80px;
            top: -120px;
            background: rgba(255,255,255,0.16);
            border-radius: 999px;
        }

        .nevade-hero-title {
            color: white !important;
            font-size: 38px;
            font-weight: 950;
            line-height: 1.08;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
        }

        .nevade-hero-subtitle {
            color: rgba(255,255,255,0.94) !important;
            font-size: 15px;
            line-height: 1.7;
            max-width: 940px;
        }

        .nevade-badge {
            display: inline-block;
            margin-top: 18px;
            margin-right: 8px;
            padding: 8px 13px;
            border-radius: 999px;
            background: rgba(255,255,255,0.16);
            border: 1px solid rgba(255,255,255,0.28);
            color: white !important;
            font-size: 12px;
            font-weight: 850;
        }

        .logo-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(21,153,214,0.18);
            border-radius: 26px;
            padding: 18px;
            box-shadow: var(--soft-shadow);
            backdrop-filter: blur(16px);
            min-height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .page-card {
            background: var(--nevade-card);
            border: 1px solid var(--nevade-border);
            border-radius: 26px;
            padding: 24px 26px;
            box-shadow: var(--soft-shadow);
            backdrop-filter: blur(18px);
            margin-bottom: 18px;
        }

        .page-title {
            color: var(--nevade-navy) !important;
            font-size: 25px;
            font-weight: 950;
            margin-bottom: 6px;
        }

        .page-subtitle {
            color: var(--nevade-muted) !important;
            font-size: 14px;
            line-height: 1.65;
        }

        .metric-card {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.92), rgba(244,249,255,0.88));
            border: 1px solid var(--nevade-border);
            border-radius: 24px;
            padding: 20px;
            box-shadow: var(--soft-shadow);
            min-height: 124px;
        }

        .metric-label {
            color: var(--nevade-muted) !important;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 10px;
        }

        .metric-value {
            color: var(--nevade-purple) !important;
            font-size: 32px;
            font-weight: 950;
            line-height: 1.1;
        }

        .metric-sub {
            color: var(--nevade-muted) !important;
            font-size: 12px;
            margin-top: 7px;
        }

        .product-card-shell {
            background: rgba(255,255,255,0.86);
            border: 1px solid var(--nevade-border);
            border-radius: 28px;
            padding: 20px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            margin-bottom: 20px;
        }

        .product-title {
            color: var(--nevade-navy) !important;
            font-size: 20px;
            font-weight: 950;
            margin-bottom: 4px;
        }

        .product-meta {
            color: var(--nevade-muted) !important;
            font-size: 13px;
            margin-bottom: 10px;
        }

        .product-price {
            background: linear-gradient(90deg, var(--nevade-purple), var(--nevade-magenta));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 30px;
            font-weight: 950;
            margin-bottom: 10px;
        }

        .badge {
            display: inline-block;
            background: rgba(21,153,214,0.10);
            color: var(--nevade-navy) !important;
            border: 1px solid rgba(21,153,214,0.20);
            padding: 7px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 850;
            margin: 4px 5px 6px 0;
        }

        .badge-purple {
            display: inline-block;
            background: rgba(107,43,142,0.10);
            color: var(--nevade-purple) !important;
            border: 1px solid rgba(107,43,142,0.20);
            padding: 7px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 850;
            margin: 4px 5px 6px 0;
        }

        .reason-box {
            background: linear-gradient(135deg, rgba(21,153,214,0.06), rgba(195,55,138,0.06));
            border: 1px solid rgba(120,160,200,0.22);
            border-radius: 18px;
            padding: 14px 16px;
            margin-top: 12px;
            color: var(--nevade-text) !important;
            font-size: 13.5px;
            line-height: 1.65;
        }

        .quick-box {
            background: rgba(255,255,255,0.86);
            border: 1px solid var(--nevade-border);
            border-radius: 24px;
            padding: 20px;
            box-shadow: var(--soft-shadow);
            min-height: 132px;
            margin-bottom: 12px;
        }

        .quick-title {
            color: var(--nevade-navy) !important;
            font-size: 18px;
            font-weight: 950;
            margin-bottom: 8px;
        }

        .quick-text {
            color: var(--nevade-muted) !important;
            font-size: 13px;
            line-height: 1.55;
        }

        .chat-user {
            background: rgba(21,153,214,0.10);
            border: 1px solid rgba(21,153,214,0.20);
            border-radius: 20px;
            padding: 15px 17px;
            margin: 11px 0;
            color: var(--nevade-text) !important;
            font-size: 14px;
            line-height: 1.6;
        }

        .chat-bot {
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--nevade-border);
            border-left: 6px solid var(--nevade-purple);
            border-radius: 20px;
            padding: 15px 17px;
            margin: 11px 0;
            box-shadow: var(--soft-shadow);
            color: var(--nevade-text) !important;
            font-size: 14px;
            line-height: 1.6;
        }

        .chat-role {
            color: var(--nevade-purple) !important;
            font-size: 12px;
            font-weight: 950;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        .stButton > button {
            width: 100%;
            border-radius: 16px;
            border: 1px solid rgba(107,43,142,0.22);
            background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(245,248,255,0.95));
            color: var(--nevade-navy);
            font-weight: 850;
            min-height: 44px;
            box-shadow: 0 6px 16px rgba(23,58,94,0.06);
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, var(--nevade-blue), var(--nevade-purple));
            color: white;
            border-color: transparent;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 18px !important;
            border: 1px solid rgba(107,43,142,0.22) !important;
            background: rgba(255,255,255,0.92) !important;
            box-shadow: 0 6px 16px rgba(23,58,94,0.04);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid rgba(120,160,200,0.25);
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.80);
            border: 1px solid var(--nevade-border);
            border-radius: 16px 16px 0 0;
            padding: 11px 16px;
            font-weight: 850;
            color: var(--nevade-navy);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(21,153,214,0.14), rgba(107,43,142,0.12)) !important;
            color: var(--nevade-purple) !important;
            border-bottom: 2px solid var(--nevade-purple);
        }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(120,160,200,0.18);
            border-radius: 16px;
            padding: 10px 12px;
        }

        div[data-testid="stExpander"] {
            background: rgba(255,255,255,0.82);
            border: 1px solid var(--nevade-border);
            border-radius: 18px;
            box-shadow: var(--soft-shadow);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header():
    logo_path = "assets/nevade_logo.png"

    st.markdown("<div class='nevade-shell'>", unsafe_allow_html=True)

    logo_col, hero_col = st.columns([1.15, 4.85], gap="large")

    with logo_col:
        st.markdown("<div class='logo-card'>", unsafe_allow_html=True)

        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(
                "<div style='font-size:28px; font-weight:950; color:#173A5E; text-align:center;'>nevade.com</div>",
                unsafe_allow_html=True
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with hero_col:
        st.markdown(
            """
            <div class="nevade-hero">
                <div class="nevade-hero-title">Nevade AI Shopping Assistant</div>
                <div class="nevade-hero-subtitle">
                    Kullanıcının ihtiyacını doğal dille anlayan, ürünleri fiyat, ödeme, stok,
                    kullanım amacı ve teknik özelliklere göre sıralayan profesyonel alışveriş asistanı.
                </div>
                <span class="nevade-badge">AI Ürün Önerisi</span>
                <span class="nevade-badge">Ödeme Analizi</span>
                <span class="nevade-badge">Ürün Karşılaştırma</span>
                <span class="nevade-badge">Sepet & Favori Davranışı</span>
                <span class="nevade-badge">API Hazır</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_page_intro(title, subtitle):
    st.markdown(
        f"""
        <div class="page-card">
            <div class="page-title">{title}</div>
            <div class="page-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )