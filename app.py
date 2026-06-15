import os
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from src.advanced_nlp_engine import AdvancedNevadeNLPEngine, normalize_text


st.set_page_config(
    page_title="Nevade AI Assistant",
    layout="wide"
)


# =====================================================
# DATA LOAD
# =====================================================

def read_product_file(file_or_path):
    if hasattr(file_or_path, "name"):
        filename = file_or_path.name.lower()

        if filename.endswith(".xlsx"):
            return pd.read_excel(file_or_path)

        return pd.read_csv(file_or_path)

    path = str(file_or_path).lower()

    if path.endswith(".xlsx"):
        return pd.read_excel(file_or_path)

    return pd.read_csv(file_or_path)


uploaded_file = st.sidebar.file_uploader(
    "Ürün listesini yükle",
    type=["csv", "xlsx"]
)

try:
    if uploaded_file is not None:
        raw_df = read_product_file(uploaded_file)
        st.sidebar.success("Ürün listesi yüklendi.")
    else:
        raw_df = read_product_file("data/products.csv")

except Exception as error:
    st.error("Ürün listesi okunamadı.")
    st.exception(error)
    st.stop()


@st.cache_resource
def load_engine(csv_text):
    from io import StringIO

    df = pd.read_csv(StringIO(csv_text))
    return AdvancedNevadeNLPEngine(df)


csv_text = raw_df.to_csv(index=False)
engine = load_engine(csv_text)
products_df = engine.products_df


# =====================================================
# SESSION STATE
# =====================================================

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

if "support_messages" not in st.session_state:
    st.session_state.support_messages = []

if "support_menu" not in st.session_state:
    st.session_state.support_menu = "main"

if "cart" not in st.session_state:
    st.session_state.cart = []

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "last_api_response" not in st.session_state:
    st.session_state.last_api_response = {}


# =====================================================
# GENERAL HELPERS
# =====================================================

def calculate_installment(price, months=6):
    return round(float(price) / months, 2)


def get_product_image(product):
    image_link = product.get("image_link", "")

    if isinstance(image_link, str):
        if os.path.exists(image_link):
            return image_link

        if image_link.startswith("http"):
            return image_link

    product_id = str(product.get("product_id", ""))

    for ext in ["png", "jpg", "jpeg", "webp"]:
        path = f"assets/products/{product_id}.{ext}"

        if os.path.exists(path):
            return path

    if os.path.exists("assets/products/placeholder.png"):
        return "assets/products/placeholder.png"

    return None


def get_products_by_ids(product_ids):
    ids = [str(item) for item in product_ids]
    return products_df[products_df["product_id"].astype(str).isin(ids)]


def add_to_cart(product_id):
    product_id = str(product_id)

    if product_id not in st.session_state.cart:
        st.session_state.cart.append(product_id)


def add_to_favorites(product_id):
    product_id = str(product_id)

    if product_id not in st.session_state.favorites:
        st.session_state.favorites.append(product_id)


def remove_from_cart(product_id):
    product_id = str(product_id)

    if product_id in st.session_state.cart:
        st.session_state.cart.remove(product_id)


def remove_from_favorites(product_id):
    product_id = str(product_id)

    if product_id in st.session_state.favorites:
        st.session_state.favorites.remove(product_id)


def cart_total():
    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        return 0

    return float(cart_df["price"].sum())


def latest_order():
    if len(st.session_state.orders) == 0:
        return None

    return st.session_state.orders[-1]


def create_order_from_cart():
    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        return None

    total = float(cart_df["price"].sum())

    order = {
        "order_id": "NV-" + datetime.now().strftime("%H%M%S"),
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "Hazırlanıyor",
        "cargo_status": "Sipariş alındı, paketleme aşamasında.",
        "estimated_delivery": "2 iş günü",
        "total_price": total,
        "monthly_installment": calculate_installment(total, 6),
        "items": cart_df.to_dict("records"),
        "is_cancelled": False,
        "is_return_requested": False
    }

    st.session_state.orders.append(order)
    st.session_state.cart = []

    return order


def create_api_response(area, user_query, query_info, message, products):
    return {
        "assistant": "Nevade AI Assistant",
        "area": area,
        "query": user_query,
        "query_understanding": query_info,
        "message": message,
        "products": products,
        "cart_product_ids": st.session_state.cart,
        "favorite_product_ids": st.session_state.favorites,
        "latest_order": latest_order()
    }


def safe_number(value):
    try:
        return float(value)
    except Exception:
        return 0


def money(value):
    return f"{safe_number(value):,.0f} TL".replace(",", ".")


# =====================================================
# INVENTORY COMPARISON LOGIC
# =====================================================
def get_float_from_text(value):
    text = str(value).lower().replace(",", ".")
    numbers = []

    for part in text.split():
        try:
            numbers.append(float(part))
        except Exception:
            pass

    if len(numbers) == 0:
        import re
        found = re.findall(r"\d+\.?\d*", text)
        if found:
            return float(found[0])
        return 0

    return numbers[0]


def get_energy_rank(value):
    value = str(value).upper().replace(" ", "")

    ranks = {
        "A+++": 5,
        "A++": 4,
        "A+": 3,
        "A": 2,
        "B": 1
    }

    return ranks.get(value, 0)


def compare_selected_products(row1, row2, focus_text):
    price1 = safe_number(row1["price"])
    price2 = safe_number(row2["price"])

    monthly1 = calculate_installment(price1, 6)
    monthly2 = calculate_installment(price2, 6)

    focus = normalize_text(focus_text)

    winner = None
    loser = None
    decision_reason = ""

    if "fiyat" in focus or "ucuz" in focus or "uygun" in focus:
        winner = row1 if price1 <= price2 else row2
        loser = row2 if price1 <= price2 else row1

        decision_reason = (
            f"Fiyat kriterine göre {winner['product_name']} daha avantajlıdır. "
            f"Çünkü {money(winner['price'])} fiyatıyla diğer üründen daha uygundur."
        )

    elif "capacity" in focus or "kapasite" in focus or "hacim" in focus or "kg" in focus or "lt" in focus or "l " in focus:
        cap1 = get_float_from_text(row1.get("capacity", ""))
        cap2 = get_float_from_text(row2.get("capacity", ""))

        if cap1 >= cap2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"Kapasite kriterine göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} kapasitesi {row1.get('capacity', '-')}, "
            f"{row2['product_name']} kapasitesi {row2.get('capacity', '-')} olarak görünüyor."
        )

    elif "enerji" in focus or "a+" in focus or "a++" in focus or "a+++" in focus:
        rank1 = get_energy_rank(row1.get("energy_class", ""))
        rank2 = get_energy_rank(row2.get("energy_class", ""))

        if rank1 >= rank2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"Enerji sınıfına göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} enerji sınıfı {row1.get('energy_class', '-')}, "
            f"{row2['product_name']} enerji sınıfı {row2.get('energy_class', '-')}."
        )

    elif "ram" in focus:
        ram1 = get_float_from_text(row1.get("ram", ""))
        ram2 = get_float_from_text(row2.get("ram", ""))

        if ram1 >= ram2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"RAM kriterine göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} RAM: {row1.get('ram', '-')}, "
            f"{row2['product_name']} RAM: {row2.get('ram', '-')}."
        )

    elif "depolama" in focus or "storage" in focus or "ssd" in focus or "hafiza" in focus:
        storage1 = get_float_from_text(row1.get("storage", ""))
        storage2 = get_float_from_text(row2.get("storage", ""))

        if storage1 >= storage2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"Depolama kriterine göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} depolama: {row1.get('storage', '-')}, "
            f"{row2['product_name']} depolama: {row2.get('storage', '-')}."
        )

    elif "senet" in focus:
        senet1 = safe_number(row1.get("senet_total_price", price1))
        senet2 = safe_number(row2.get("senet_total_price", price2))

        if senet1 <= senet2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"Senetli ödeme kriterine göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} senetli toplam fiyatı {money(row1.get('senet_total_price', price1))}, "
            f"{row2['product_name']} senetli toplam fiyatı {money(row2.get('senet_total_price', price2))}. "
            f"Senetli fiyat farkı yüksekse havale veya kredi kartı taksiti daha mantıklı olabilir."
        )

    elif "havale" in focus:
        havale1 = safe_number(row1.get("bank_transfer_price", price1))
        havale2 = safe_number(row2.get("bank_transfer_price", price2))

        if havale1 <= havale2:
            winner = row1
            loser = row2
        else:
            winner = row2
            loser = row1

        decision_reason = (
            f"Havale fiyatına göre {winner['product_name']} daha avantajlıdır. "
            f"{row1['product_name']} havale fiyatı {money(row1.get('bank_transfer_price', price1))}, "
            f"{row2['product_name']} havale fiyatı {money(row2.get('bank_transfer_price', price2))}."
        )

    else:
        winner = row1 if price1 <= price2 else row2
        loser = row2 if price1 <= price2 else row1

        decision_reason = (
            f"Genel değerlendirmede {winner['product_name']} daha dengeli seçenek görünüyor. "
            f"Fiyat, ödeme seçenekleri, stok, kullanım amacı ve ürün özellikleri birlikte dikkate alındı."
        )

    message = (
        f"{row1['product_name']} ve {row2['product_name']} karşılaştırıldı. "
        f"{decision_reason} "
        f"6 taksit hesabında {row1['product_name']} aylık yaklaşık {monthly1:.0f} TL, "
        f"{row2['product_name']} aylık yaklaşık {monthly2:.0f} TL olur."
    )

    products = []

    for row in [row1, row2]:
        price = safe_number(row["price"])
        monthly = calculate_installment(price, 6)

        if str(row["product_id"]) == str(winner["product_id"]):
            score = 0.92
            label_reason = "Bu ürün seçtiğiniz kritere göre daha avantajlı olduğu için öne çıkarıldı."
        else:
            score = 0.58
            label_reason = "Bu ürün alternatif olarak değerlendirildi; ancak seçtiğiniz kritere göre diğer ürün daha avantajlı görünüyor."

        reason = (
            f"{label_reason} "
            f"Fiyatı {price:.0f} TL, 6 taksit tutarı yaklaşık {monthly:.0f} TL. "
            f"Fiyat, ödeme tipi, stok, kullanım amacı ve teknik özellikler birlikte değerlendirildi."
        )

        product = engine.product_to_json(
            row,
            reason=reason,
            score=score
        )

        if str(row["product_id"]) == str(winner["product_id"]):
            product["match_label"] = "Daha avantajlı"
        else:
            product["match_label"] = "Alternatif"

        products.append(product)

    return products, message

# =====================================================
# AI ASSISTANT LOGIC
# =====================================================

def build_similar_products(user_query):
    found_products = engine.find_products_in_text(user_query)

    if len(found_products) == 0:
        return [], "Benzer ürün önermek için ürün adını veya markayı daha net yazabilirsiniz."

    selected = found_products[0]

    candidates = products_df[
        (products_df["category"] == selected["category"]) &
        (products_df["product_id"] != selected["product_id"])
    ].copy()

    if candidates.empty:
        return [], "Bu ürünle aynı kategoride alternatif ürün bulunamadı."

    candidates["price_diff"] = abs(
        candidates["price"] - float(selected["price"])
    )

    candidates = candidates.sort_values("price_diff").head(5)

    products = []

    for _, row in candidates.iterrows():
        price = safe_number(row["price"])

        reason = (
            f"Bu ürün, {selected['product_name']} ile aynı kategoride olduğu için önerildi. "
            f"Fiyat olarak alternatif konumdadır. Peşin fiyatına 6 taksit tutarı yaklaşık "
            f"{calculate_installment(price, 6):.0f} TL olur."
        )

        products.append(
            engine.product_to_json(
                row,
                reason=reason,
                score=0.75
            )
        )

    message = f"{selected['product_name']} ürününe benzer alternatifleri listeledim."

    return products, message


def handle_ai_assistant(user_query):
    query_info = engine.understand_query(user_query)
    intent = query_info["intent"]

    if intent == "bundle_recommendation":
        products, message = engine.recommend_ceyiz_bundle(user_query)

    elif intent == "student_laptop":
        products, message = engine.recommend_student_laptops(user_query)

    elif intent == "comparison":
        products, message = engine.compare(user_query)

    elif intent == "similar":
        products, message = build_similar_products(user_query)

    else:
        products, query_info = engine.recommend(user_query, top_n=6)

        if len(products) == 0:
            message = (
                "Bu ihtiyaca uygun ürün bulamadım. "
                "Kategori, bütçe, marka veya kullanım amacı belirterek tekrar deneyebilirsiniz."
            )
        else:
            top = products[0]
            payment_preference = query_info.get("payment_preference")

            message = (
                f"İhtiyacınıza en uygun seçenek {top['product_name']} olarak görünüyor. "
                f"Fiyatı {top['price']:.0f} TL. Peşin fiyatına 6 taksit ile aylık yaklaşık "
                f"{top['monthly_installment_6']:.0f} TL."
            )

            if payment_preference == "senet":
                message += (
                    " Senetle alışveriş düşündüğünüz için ödeme tarafında da değerlendirdim. "
                    "Bu fiyat seviyesinde peşin fiyatına taksit veya havale indirimi varsa, "
                    "senet yerine bunlar daha avantajlı olabilir."
                )

    st.session_state.last_api_response = create_api_response(
        area="ai_assistant",
        user_query=user_query,
        query_info=query_info,
        message=message,
        products=products
    )

    st.session_state.ai_messages.insert(0, {
        "role": "assistant",
        "content": message,
        "products": products,
        "query_info": query_info
    })

    st.session_state.ai_messages.insert(0, {
        "role": "user",
        "content": user_query
    })


# =====================================================
# QUICK SUPPORT LOGIC
# =====================================================

def build_cart_response():
    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        return "Sepetiniz şu anda boş.", []

    total = float(cart_df["price"].sum())
    monthly = calculate_installment(total, 6)

    products = []

    for _, row in cart_df.iterrows():
        products.append(
            engine.product_to_json(
                row,
                reason="Bu ürün sepetinizde bulunmaktadır.",
                score=0.80
            )
        )

    message = (
        f"Sepetinizde {len(products)} ürün var. "
        f"Toplam tutar {total:.0f} TL. "
        f"Peşin fiyatına 6 taksit ile aylık yaklaşık {monthly:.0f} TL."
    )

    return message, products


def build_favorites_response():
    fav_df = get_products_by_ids(st.session_state.favorites)

    if fav_df.empty:
        return "Favorilerinizde henüz ürün yok.", []

    products = []

    for _, row in fav_df.iterrows():
        products.append(
            engine.product_to_json(
                row,
                reason="Bu ürün favorilerinizde bulunmaktadır.",
                score=0.80
            )
        )

    message = f"Favorilerinizde {len(products)} ürün var."

    return message, products


def build_order_tracking_response():
    order = latest_order()

    if order is None:
        return (
            "Henüz oluşturulmuş siparişiniz bulunmuyor. "
            "Sepete ürün ekleyip sipariş oluşturabilirsiniz."
        )

    if order["is_cancelled"]:
        return f"{order['order_id']} numaralı siparişiniz iptal edilmiş görünüyor."

    return (
        f"Son siparişiniz {order['order_id']} numarasıyla {order['status']} durumunda. "
        f"Kargo durumu: {order['cargo_status']} "
        f"Tahmini teslimat: {order['estimated_delivery']}."
    )


def cancel_latest_order():
    order = latest_order()

    if order is None:
        return "İptal edilebilecek bir siparişiniz bulunmuyor."

    if order["status"] == "Teslim edildi":
        return "Teslim edilmiş siparişlerde iptal yerine iade talebi oluşturabilirsiniz."

    order["is_cancelled"] = True
    order["status"] = "İptal edildi"

    return f"{order['order_id']} numaralı siparişiniz için iptal talebi oluşturuldu."


def return_latest_order():
    order = latest_order()

    if order is None:
        return "İade talebi oluşturulabilecek bir siparişiniz bulunmuyor."

    if order["is_cancelled"]:
        return "İptal edilmiş sipariş için iade talebi oluşturulamaz."

    order["is_return_requested"] = True
    order["status"] = "İade talebi alındı"

    return f"{order['order_id']} numaralı siparişiniz için iade talebi oluşturuldu."


def handle_support_action(action):
    products = []
    query_info = {
        "intent": action
    }

    if action == "siparisim_nerede":
        message = build_order_tracking_response()

    elif action == "adres_degistir":
        message = (
            "Teslimat adresi değişikliği sipariş kargoya verilmeden önce yapılabilir. "
            "Demo sistemde bu işlem adres güncelleme talebi olarak modellenmiştir."
        )

    elif action == "iptal_iade":
        message = (
            "İptal veya iade işlemi için sipariş durumunuza göre işlem başlatabilirsiniz. "
            "İsterseniz iade talebi oluşturabilirim."
        )

    elif action == "eksik_kusurlu_yanlis":
        message = (
            "Eksik, kusurlu veya yanlış ürün bildirimi için destek talebi oluşturulabilir. "
            "Gerçek entegrasyonda ürün fotoğrafı ve sipariş numarası alınır."
        )

    elif action == "fatura":
        message = (
            "Faturanıza sipariş detay sayfasından ulaşabilirsiniz. "
            "Demo sistemde fatura bağlantısı API ile getirilecek şekilde tasarlanmıştır."
        )

    elif action == "sepet":
        message, products = build_cart_response()

    elif action == "favoriler":
        message, products = build_favorites_response()

    elif action == "iade_baslat":
        message = return_latest_order()

    elif action == "iptal_et":
        message = cancel_latest_order()

    elif action == "siparis_olustur":
        order = create_order_from_cart()

        if order is None:
            message = "Sipariş oluşturmak için önce sepete ürün eklemelisiniz."
        else:
            message = f"Siparişiniz oluşturuldu. Sipariş numaranız {order['order_id']}."

    elif action == "kampanya":
        message = (
            "Kampanya ve kupon işlemleri için demo sistemde peşin fiyatına 6 taksit, "
            "havale indirimi, senetli ödeme ve uygun fiyatlı alternatif önerileri desteklenmektedir."
        )

    elif action == "hesabim":
        message = (
            "Hesabım menüsünden üyelik bilgileri, adresler, şifre yenileme "
            "ve sipariş geçmişi yönetilebilir."
        )

    elif action == "destek":
        message = (
            "Destek talebinizi konu başlığına göre alabilirim: "
            "kargo, ürün, ödeme, iade veya üyelik."
        )

    else:
        message = (
            "Size sipariş, sepet, favori, iade, iptal, kampanya ve hesap işlemleriyle ilgili yardımcı olabilirim."
        )

    st.session_state.last_api_response = create_api_response(
        area="quick_support",
        user_query=action,
        query_info=query_info,
        message=message,
        products=products
    )

    st.session_state.support_messages.insert(0, {
        "role": "assistant",
        "content": message,
        "products": products
    })


# =====================================================
# CSS
# =====================================================

st.markdown(
    """
    <style>
    :root {
        --nevade-blue: #009FE3;
        --nevade-pink: #E6007E;
        --nevade-dark: #1F4E79;
        --nevade-bg: #F8FBFD;
        --nevade-card: #FFFFFF;
        --nevade-border: #DCEAF3;
        --nevade-text: #1F2937;
        --nevade-muted: #64748B;
        --nevade-soft-blue: #EAF7FD;
        --nevade-soft-pink: #FFF0F7;
    }

    .stApp {
        background: var(--nevade-bg);
    }

    .block-container {
        max-width: 1380px;
        padding-top: 1rem;
    }

    h1, h2, h3, h4, h5, h6, p, div, span, label {
        font-family: "Segoe UI", Arial, sans-serif !important;
        color: var(--nevade-text);
        word-break: normal !important;
        overflow-wrap: break-word !important;
    }

    .main-header {
        background: linear-gradient(90deg, var(--nevade-blue), var(--nevade-dark));
        padding: 20px 26px;
        border-radius: 18px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(0,159,227,0.16);
    }

    .main-title {
        color: white !important;
        font-size: 30px;
        font-weight: 900;
    }

    .main-subtitle {
        color: white !important;
        font-size: 14px;
        line-height: 1.5;
    }

    .section-box {
        background: white;
        border: 1px solid var(--nevade-border);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 8px 22px rgba(31,78,121,0.07);
        margin-bottom: 14px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 900;
        color: var(--nevade-dark) !important;
        margin-bottom: 6px;
    }

    .section-subtitle {
        font-size: 14px;
        color: var(--nevade-muted) !important;
        line-height: 1.5;
    }

    .chat-user {
        background: var(--nevade-soft-blue);
        border: 1px solid var(--nevade-border);
        border-radius: 16px;
        padding: 12px 14px;
        margin: 10px 0;
        font-size: 14px;
        line-height: 1.5;
    }

    .chat-assistant {
        background: #FFFFFF;
        border: 1px solid var(--nevade-border);
        border-left: 5px solid var(--nevade-blue);
        border-radius: 16px;
        padding: 12px 14px;
        margin: 10px 0;
        font-size: 14px;
        line-height: 1.5;
        box-shadow: 0 4px 12px rgba(31,78,121,0.05);
    }

    .chat-role {
        font-size: 12px;
        font-weight: 900;
        color: var(--nevade-dark) !important;
        margin-bottom: 4px;
    }

    .product-card {
        background: white;
        border: 1px solid var(--nevade-border);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(31,78,121,0.05);
        overflow: hidden;
    }

    .comparison-card {
        background: white;
        border: 1px solid var(--nevade-border);
        border-radius: 16px;
        padding: 14px;
        box-shadow: 0 4px 14px rgba(31,78,121,0.05);
    }

    .product-title {
        font-size: 16px;
        font-weight: 900;
        color: var(--nevade-dark) !important;
        line-height: 1.35;
    }

    .product-price {
        font-size: 22px;
        font-weight: 900;
        color: var(--nevade-pink) !important;
        margin-top: 4px;
    }

    .mini-text {
        color: var(--nevade-muted) !important;
        font-size: 13px;
        line-height: 1.5;
    }

    .installment {
        background: var(--nevade-soft-pink);
        border: 1px solid #F7B9D8;
        color: var(--nevade-pink) !important;
        padding: 8px 10px;
        border-radius: 10px;
        font-weight: 800;
        margin-top: 6px;
        font-size: 13px;
        line-height: 1.4;
    }

    .match-label {
        background: var(--nevade-soft-blue);
        border: 1px solid var(--nevade-border);
        color: var(--nevade-dark) !important;
        padding: 7px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 800;
        display: inline-block;
        margin-top: 6px;
    }

    .spec-line {
        font-size: 13px;
        border-bottom: 1px solid #EEF5FA;
        padding: 5px 0;
        color: var(--nevade-muted) !important;
    }

    .price-box {
        background: #F8FBFD;
        border: 1px solid #DCEAF3;
        border-radius: 12px;
        padding: 10px;
        margin-top: 8px;
        font-size: 13px;
    }

    .price-row {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #EAF0F5;
        padding: 4px 0;
    }

    .price-row:last-child {
        border-bottom: none;
    }

    .price-label {
        color: #64748B !important;
        font-weight: 700;
    }

    .price-value {
        color: #1F4E79 !important;
        font-weight: 900;
    }

    .stButton button {
        border-radius: 999px;
        border: 1px solid var(--nevade-border);
        background: white;
        color: var(--nevade-dark);
        font-weight: 800;
        white-space: normal;
        min-height: 38px;
    }

    .stButton button:hover {
        background: var(--nevade-soft-blue);
        color: var(--nevade-blue);
        border: 1px solid var(--nevade-blue);
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# UI COMPONENTS
# =====================================================

def show_chat_message(message):
    role = message.get("role", "")
    content = message.get("content", "")

    if role == "user":
        st.markdown(
            f"""
            <div class="chat-user">
                <div class="chat-role">Sen</div>
                {content}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="chat-assistant">
                <div class="chat-role">Nevade Asistan</div>
                {content}
            </div>
            """,
            unsafe_allow_html=True
        )


def product_price_html(product):
    specs = product.get("specs", {})

    cash_price = product.get("cash_price", "")
    bank_transfer_price = product.get("bank_transfer_price", "")
    card_price = product.get("card_price", "")
    installment_3_total = product.get("installment_3_total", "")
    installment_6_total = product.get("installment_6_total", "")
    installment_9_total = product.get("installment_9_total", "")
    senet_total_price = product.get("senet_total_price", "")
    senet_monthly_9 = product.get("senet_monthly_9", "")

    rows = []

    def add_row(label, value):
        if value is not None and str(value).strip() != "":
            rows.append(
                f"""
                <div class="price-row">
                    <span class="price-label">{label}</span>
                    <span class="price-value">{money(value)}</span>
                </div>
                """
            )

    add_row("Peşin", cash_price)
    add_row("Havale", bank_transfer_price)
    add_row("Kart", card_price)
    add_row("3 Taksit Toplam", installment_3_total)
    add_row("6 Taksit Toplam", installment_6_total)
    add_row("9 Taksit Toplam", installment_9_total)
    add_row("Senetli Toplam", senet_total_price)
    add_row("Senet 9 Ay Aylık", senet_monthly_9)

    if not rows:
        return ""

    return f"""<div class="price-box">{''.join(rows)}</div>"""


def show_product_card(product, key_prefix):
    st.markdown('<div class="product-card">', unsafe_allow_html=True)

    image_col, info_col = st.columns([1, 3])

    with image_col:
        image = get_product_image(product)

        if image:
            st.image(image, use_container_width=True)

    with info_col:
        monthly = product.get(
            "monthly_installment_6",
            calculate_installment(product.get("price", 0), 6)
        )

        st.markdown(
            f"""
            <div class="product-title">{product.get('product_name', '')}</div>
            <div class="mini-text">{product.get('category', '')} | {product.get('brand', '')}</div>
            <div class="product-price">{money(product.get('price', 0))}</div>
            <div class="installment">Peşin fiyatına 6 taksit: {float(monthly):.0f} TL x 6</div>
            <div class="match-label">Sana uygunluk: {product.get('match_label', 'Uygun')}</div>
            {product_price_html(product)}
            <div class="mini-text" style="margin-top:8px;">{product.get('reason', '')}</div>
            """,
            unsafe_allow_html=True
        )

    product_id = str(product.get("product_id", ""))

    b1, b2 = st.columns(2)

    with b1:
        if st.button("Sepete Ekle", key=f"{key_prefix}_cart_{product_id}"):
            add_to_cart(product_id)
            st.success("Sepete eklendi.")

    with b2:
        if st.button("Favoriye Ekle", key=f"{key_prefix}_fav_{product_id}"):
            add_to_favorites(product_id)
            st.success("Favorilere eklendi.")

    st.markdown("</div>", unsafe_allow_html=True)


def show_comparison_cards(products, unique_prefix="compare"):
    if len(products) < 2:
        for index, product in enumerate(products):
            show_product_card(
                product,
                key_prefix=f"{unique_prefix}_single_{index}_{product.get('product_id', '')}"
            )
        return

    cols = st.columns(2)

    for index, product in enumerate(products[:2]):
        with cols[index]:
            st.markdown('<div class="comparison-card">', unsafe_allow_html=True)

            image = get_product_image(product)

            if image:
                st.image(image, use_container_width=True)

            monthly = product.get(
                "monthly_installment_6",
                calculate_installment(product.get("price", 0), 6)
            )

            st.markdown(
                f"""
                <div class="product-title">{product.get('product_name', '')}</div>
                <div class="mini-text">{product.get('category', '')} | {product.get('brand', '')}</div>
                <div class="product-price">{money(product.get('price', 0))}</div>
                <div class="installment">6 taksit: {float(monthly):.0f} TL x 6</div>
                <div class="match-label">{product.get('match_label', 'Uygun')}</div>
                {product_price_html(product)}
                """,
                unsafe_allow_html=True
            )

            specs = product.get("specs", {})

            if specs:
                for spec_name, spec_value in specs.items():
                    if str(spec_value).strip() != "":
                        st.markdown(
                            f"""
                            <div class="spec-line">
                                <b>{spec_name}</b>: {spec_value}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            st.markdown(
                f"""
                <div class="mini-text" style="margin-top:8px;">
                    {product.get('reason', '')}
                </div>
                """,
                unsafe_allow_html=True
            )

            product_id = str(product.get("product_id", ""))

            safe_key_base = f"{unique_prefix}_{index}_{product_id}"

            b1, b2 = st.columns(2)

            with b1:
                if st.button("Sepete Ekle", key=f"compare_cart_{safe_key_base}"):
                    add_to_cart(product_id)
                    st.success("Sepete eklendi.")

            with b2:
                if st.button("Favoriye Ekle", key=f"compare_fav_{safe_key_base}"):
                    add_to_favorites(product_id)
                    st.success("Favorilere eklendi.")

            st.markdown("</div>", unsafe_allow_html=True)


# =====================================================
# MAIN UI
# =====================================================

st.markdown(
    """
    <div class="main-header">
        <div class="main-title">NEVADE ASİSTAN</div>
        <div class="main-subtitle">
            NLP destekli alışveriş asistanı ve hızlı işlem merkezi.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


tab_ai, tab_support = st.tabs(
    [
        "🧠 Nevade AI Assistant",
        "⚡ Hızlı İşlemler"
    ]
)


# =====================================================
# TAB 1 - AI ASSISTANT
# =====================================================

with tab_ai:
    st.markdown(
        """
        <div class="section-box">
            <div class="section-title">Nevade AI Assistant</div>
            <div class="section-subtitle">
                İhtiyacını doğal cümleyle yaz veya envanterden kategori seçerek iki ürünü kontrollü karşılaştır.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### Envanterden Kontrollü Ürün Karşılaştır")

    compare_categories = sorted(products_df["category"].dropna().unique().tolist())

    selected_compare_category = st.selectbox(
        "Kategori seç",
        compare_categories,
        key="inventory_compare_category"
    )

    category_products_df = products_df[
        products_df["category"] == selected_compare_category
    ].copy()

    product_options = category_products_df["product_name"].tolist()

    compare_col1, compare_col2 = st.columns(2)

    with compare_col1:
        selected_product_1 = st.selectbox(
            "1. ürün",
            product_options,
            key="inventory_compare_product_1"
        )

    with compare_col2:
        selected_product_2 = st.selectbox(
            "2. ürün",
            product_options,
            key="inventory_compare_product_2"
        )

    comparison_focus = st.text_input(
        "Karşılaştırma kriteri",
        placeholder="Örn: fiyat, kullanım kolaylığı, öğrenciye uygunluk, taksit, işlemci, enerji sınıfı, senet",
        key="comparison_focus"
    )

    if st.button("Bu Ürünleri AI ile Karşılaştır"):
        if selected_product_1 == selected_product_2:
            st.warning("Karşılaştırmak için iki farklı ürün seçmelisin.")
        else:
            row1 = category_products_df[
                category_products_df["product_name"] == selected_product_1
            ].iloc[0]

            row2 = category_products_df[
                category_products_df["product_name"] == selected_product_2
            ].iloc[0]

            user_query = (
                f"{selected_product_1} ile {selected_product_2} ürünlerini "
                f"{comparison_focus if comparison_focus else 'fiyat, taksit, kullanım kolaylığı ve özellikler'} açısından karşılaştır"
            )

            products, message = compare_selected_products(
                row1=row1,
                row2=row2,
                focus_text=comparison_focus
            )

            query_info = engine.understand_query(user_query)

            enhanced_query_info = {
                **query_info,
                "source": "inventory_selected_comparison",
                "selected_category": selected_compare_category,
                "selected_product_1": selected_product_1,
                "selected_product_2": selected_product_2,
                "comparison_focus": comparison_focus
            }

            st.session_state.last_api_response = create_api_response(
                area="inventory_comparison",
                user_query=user_query,
                query_info=enhanced_query_info,
                message=message,
                products=products
            )

            st.session_state.ai_messages.insert(0, {
                "role": "assistant",
                "content": message,
                "products": products,
                "query_info": enhanced_query_info
            })

            st.session_state.ai_messages.insert(0, {
                "role": "user",
                "content": user_query
            })

            st.rerun()

    st.markdown("---")

    st.markdown("### Doğal Dil ile AI Asistana Sor")

    ai_input = st.text_area(
        "Asistana yaz",
        placeholder=(
            "Örn: 50000 TL civarı buzdolabı istiyorum, özelliklerine göre öner. "
            "Senetle alışveriş yapacağım, laptop öner. "
            "30000 TL altı telefon öner."
        ),
        height=110
    )

    if st.button("AI Asistana Sor"):
        if ai_input.strip() == "":
            st.warning("Lütfen bir alışveriş ihtiyacı yaz.")
        else:
            handle_ai_assistant(ai_input)
            st.rerun()

    if len(st.session_state.ai_messages) == 0:
        st.info("Henüz AI Assistant'a soru sorulmadı.")

    for msg_index, message in enumerate(st.session_state.ai_messages):
        show_chat_message(message)

        if message.get("query_info"):
            with st.expander("NLP analizi"):
                st.json(message["query_info"])

        if message.get("products"):
            source = message.get("query_info", {}).get("source")
            intent = message.get("query_info", {}).get("intent")

            if source == "inventory_selected_comparison" or intent == "comparison":
                show_comparison_cards(
                    message["products"],
                    unique_prefix=f"msg_{msg_index}_{source or intent or 'ai'}"
                )
            else:
                for product_index, product in enumerate(message["products"]):
                    show_product_card(
                        product,
                        key_prefix=f"ai_{msg_index}_{product_index}_{product['product_id']}"
                    )


# =====================================================
# TAB 2 - QUICK SUPPORT
# =====================================================

with tab_support:
    st.markdown(
        """
        <div class="section-box">
            <div class="section-title">Hızlı İşlemler</div>
            <div class="section-subtitle">
                Merhaba, sana yardımcı olmamı istediğin konuyu seçebilir misin?
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    main1, main2, main3 = st.columns(3)

    with main1:
        if st.button("📦 Siparişlerim"):
            st.session_state.support_menu = "siparislerim"
            st.rerun()

    with main2:
        if st.button("👤 Hesabım"):
            handle_support_action("hesabim")
            st.rerun()

    with main3:
        if st.button("💸 Kampanya ve Kupon"):
            handle_support_action("kampanya")
            st.rerun()

    main4, main5, main6 = st.columns(3)

    with main4:
        if st.button("📝 Destek Taleplerim"):
            handle_support_action("destek")
            st.rerun()

    with main5:
        if st.button("📎 Diğer"):
            st.session_state.support_menu = "diger"
            st.rerun()

    with main6:
        if st.button("🛒 Sepetim"):
            handle_support_action("sepet")
            st.rerun()

    if st.session_state.support_menu == "siparislerim":
        st.markdown("### Siparişlerim")
        st.write("Yapmak istediğin işlemi seçer misin?")

        s1, s2 = st.columns(2)

        with s1:
            if st.button("Siparişim nerede?"):
                handle_support_action("siparisim_nerede")
                st.rerun()

        with s2:
            if st.button("Teslimat adresimi değiştirebilir miyim?"):
                handle_support_action("adres_degistir")
                st.rerun()

        s3, s4 = st.columns(2)

        with s3:
            if st.button("İptal / İade İşlemlerim"):
                handle_support_action("iptal_iade")
                st.rerun()

        with s4:
            if st.button("Siparişim eksik/kusurlu/yanlış geldi"):
                handle_support_action("eksik_kusurlu_yanlis")
                st.rerun()

        if st.button("Faturama nasıl ulaşabilirim?"):
            handle_support_action("fatura")
            st.rerun()

    if st.session_state.support_menu == "diger":
        st.markdown("### Diğer İşlemler")

        d1, d2 = st.columns(2)

        with d1:
            if st.button("Favorilerim"):
                handle_support_action("favoriler")
                st.rerun()

        with d2:
            if st.button("Sipariş oluştur"):
                handle_support_action("siparis_olustur")
                st.rerun()

        d3, d4 = st.columns(2)

        with d3:
            if st.button("İade başlat"):
                handle_support_action("iade_baslat")
                st.rerun()

        with d4:
            if st.button("Sipariş iptal et"):
                handle_support_action("iptal_et")
                st.rerun()

    if len(st.session_state.support_messages) == 0:
        st.info("Hızlı işlem konuşması henüz başlamadı.")

    for msg_index, message in enumerate(st.session_state.support_messages):
        show_chat_message(message)

        if message.get("products"):
            for product_index, product in enumerate(message["products"]):
                show_product_card(
                    product,
                    key_prefix=f"support_{msg_index}_{product_index}_{product['product_id']}"
                )

    st.markdown("---")
    st.markdown("### Sepet Özeti")

    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        st.info("Sepet boş.")
    else:
        total = cart_total()
        monthly = calculate_installment(total, 6)

        st.success(
            f"Toplam: {total:.0f} TL | 6 taksit: {monthly:.0f} TL x 6"
        )

        for _, row in cart_df.iterrows():
            st.write(f"{row['product_name']} - {float(row['price']):.0f} TL")

        if st.button("Sipariş Oluştur"):
            order = create_order_from_cart()

            if order:
                st.success(f"Sipariş oluşturuldu: {order['order_id']}")
                st.rerun()

    with st.expander("API JSON çıktısı"):
        st.code(
            json.dumps(st.session_state.last_api_response, ensure_ascii=False, indent=4),
            language="json"
        )

    if st.button("Sohbetleri Temizle"):
        st.session_state.ai_messages = []
        st.session_state.support_messages = []
        st.session_state.last_api_response = {}
        st.session_state.support_menu = "main"
        st.rerun()