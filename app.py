import os
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from src.advanced_nlp_engine import AdvancedNevadeNLPEngine
from src.utils import normalize_text, safe_number, money

try:
    from src.behavior_engine import BehaviorEngine
except Exception:
    BehaviorEngine = None

try:
    from src.llm_service import LLMService
except Exception:
    LLMService = None


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Nevade AI Assistant",
    page_icon="🛍️",
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
    st.error("Ürün listesi okunamadı. Lütfen data/products.csv dosyasını kontrol et.")
    st.exception(error)
    st.stop()


def load_engine_from_df(df):
    return AdvancedNevadeNLPEngine(df.copy())


engine = load_engine_from_df(raw_df)
products_df = engine.products_df
behavior_engine = BehaviorEngine(products_df, engine) if BehaviorEngine else None
llm_service = LLMService() if LLMService else None

st.sidebar.markdown("---")
st.sidebar.write(f"Yüklü ürün sayısı: {len(products_df)}")

if "category" in products_df.columns:
    st.sidebar.write(f"Kategori sayısı: {products_df['category'].nunique()}")


# =====================================================
# SESSION STATE
# =====================================================

def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


init_state("ai_messages", [])
init_state("support_messages", [])
init_state("cart", [])
init_state("favorites", [])
init_state("orders", [])
init_state("last_api_response", {})
init_state("last_result", None)


# =====================================================
# HELPERS
# =====================================================

def calculate_installment(price, months=6):
    price = safe_number(price)

    if months <= 0:
        return 0

    return round(price / months, 2)


def extract_product_ids(items):
    product_ids = []

    if not items:
        return product_ids

    for item in items:
        if isinstance(item, dict):
            product_id = (
                item.get("product_id")
                or item.get("id")
                or item.get("Product ID")
                or item.get("Ürün ID")
            )
        else:
            product_id = item

        if product_id is not None and str(product_id).strip() != "":
            product_ids.append(str(product_id).strip())

    return product_ids


def get_products_by_ids(product_ids):
    ids = extract_product_ids(product_ids)

    if not ids:
        return products_df.iloc[0:0]

    return products_df[
        products_df["product_id"].astype(str).isin(ids)
    ].copy()


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

    return float(cart_df["price"].apply(safe_number).sum())


def latest_order():
    if len(st.session_state.orders) == 0:
        return None

    return st.session_state.orders[-1]


def create_order_from_cart():
    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        return None

    total = cart_total()

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


def get_product_image(product):
    image_link = product.get("image_link", "")

    if isinstance(image_link, str):
        if image_link.startswith("http"):
            return image_link

        if os.path.exists(image_link):
            return image_link

    product_id = str(product.get("product_id", ""))

    for ext in ["png", "jpg", "jpeg", "webp"]:
        path = f"assets/products/{product_id}.{ext}"

        if os.path.exists(path):
            return path

    if os.path.exists("assets/products/placeholder.png"):
        return "assets/products/placeholder.png"

    return None


def clean_llm_message(message):
    if not isinstance(message, str):
        return message

    if "Not: LLM cevap üretimi" in message:
        return message.split("Not: LLM cevap üretimi")[0].strip()

    if "insufficient_quota" in message:
        return message.split("Not:")[0].strip()

    return message


# =====================================================
# API RESPONSE
# =====================================================

def create_api_response(area, user_query, query_info, message, products):
    clean_products = []
    products = products or []

    for index, product in enumerate(products):
        clean_products.append({
            "rank": index + 1,
            "product_id": str(product.get("product_id", "")),
            "product_name": product.get("product_name", ""),
            "category": product.get("category", ""),
            "brand": product.get("brand", ""),
            "price": safe_number(product.get("price", 0)),
            "stock_status": product.get("stock_status", ""),
            "match_label": product.get("match_label", ""),
            "final_score": product.get("final_score", 0),
            "reason": product.get("reason", ""),
            "product_link": product.get("product_link", ""),
            "image_link": product.get("image_link", ""),
            "payment": {
                "cash_price": safe_number(product.get("cash_price", 0)),
                "bank_transfer_price": safe_number(product.get("bank_transfer_price", 0)),
                "card_price": safe_number(product.get("card_price", 0)),
                "installment_3_total": safe_number(product.get("installment_3_total", 0)),
                "installment_6_total": safe_number(product.get("installment_6_total", 0)),
                "installment_9_total": safe_number(product.get("installment_9_total", 0)),
                "senet_total_price": safe_number(product.get("senet_total_price", 0)),
                "senet_monthly_9": safe_number(product.get("senet_monthly_9", 0))
            },
            "specs": product.get("specs", {})
        })

    return {
        "project": "Nevade AI Shopping Assistant",
        "area": area,
        "status": "success",
        "user_query": user_query,
        "detected_intent": query_info.get("intent"),
        "detected_category": query_info.get("category"),
        "detected_product_type": query_info.get("product_type"),
        "detected_budget": query_info.get("budget"),
        "detected_payment_preference": query_info.get("payment_preference"),
        "detected_priority": query_info.get("priority"),
        "assistant_message": message,
        "total_results": len(clean_products),
        "results": clean_products,
        "integration_note": (
            "Bu çıktı Nevade.com tarafında product_id üzerinden ürün kartı, arama sonucu, "
            "benzer ürün önerisi, sepet/favori önerisi veya hızlı işlem cevabı olarak kullanılabilir."
        )
    }


def save_last_result(area, user_query, query_info, message, products):
    message = clean_llm_message(message)

    api_response = create_api_response(
        area=area,
        user_query=user_query,
        query_info=query_info,
        message=message,
        products=products
    )

    st.session_state.last_result = {
        "area": area,
        "user_query": user_query,
        "query_info": query_info,
        "message": message,
        "products": products
    }

    st.session_state.last_api_response = api_response

    target = "ai_messages"

    if area.startswith("quick") or area.startswith("support"):
        target = "support_messages"

    st.session_state[target].insert(0, {
        "role": "assistant",
        "content": message,
        "products": products,
        "query_info": query_info
    })

    st.session_state[target].insert(0, {
        "role": "user",
        "content": user_query
    })


# =====================================================
# AI LOGIC
# =====================================================

def build_professional_ai_message(user_query, query_info, products):
    if not products:
        return (
            "Bu ihtiyaca uygun ürünü net olarak bulamadım. Ürün tipi, bütçe, ödeme yöntemi "
            "ve kullanım amacını biraz daha açık yazarsan sana daha doğru bir öneri sunabilirim."
        )

    top = products[0]
    alternatives = products[1:3]

    specs = top.get("specs", {}) or {}
    payment_analysis = top.get("payment_analysis", {}) or {}

    product_name = top.get("product_name", "")
    price = money(top.get("price", 0))

    product_type = query_info.get("product_type")
    category = query_info.get("category")
    budget = query_info.get("budget")
    payment_preference = query_info.get("payment_preference")
    priority = query_info.get("priority")
    user_profile = query_info.get("user_profile", [])

    intro = f"Bu ihtiyaca en uygun seçenek **{product_name}** olarak öne çıkıyor."

    analysis_parts = []

    if product_type:
        analysis_parts.append(
            "Önce yazdığın ürün tipine uygun ürünleri filtreledim."
        )
    elif category:
        analysis_parts.append(
            f"Önce {category} kategorisindeki ürünleri değerlendirdim."
        )

    if budget:
        if safe_number(top.get("price", 0)) <= safe_number(budget):
            analysis_parts.append(
                f"Ürün {money(budget)} bütçenin içinde kalıyor."
            )
        else:
            analysis_parts.append(
                f"Ürün {money(budget)} bütçeye en yakın güçlü alternatiflerden biri."
            )

    if user_profile:
        analysis_parts.append(
            f"Kullanım profili olarak {', '.join(user_profile)} ihtiyacını dikkate aldım."
        )

    if priority == "price":
        analysis_parts.append(
            "Öncelik uygun fiyat olduğu için fiyat/performans dengesi güçlü olan ürünler öne alındı."
        )

    elif priority == "payment":
        if payment_preference == "senet":
            analysis_parts.append(
                f"Senetli ödeme istediğin için ürünler senetli toplam fiyatlarına göre karşılaştırıldı. "
                f"Bu ürünün senetli toplamı {money(top.get('senet_total_price', 0))}."
            )
        elif payment_preference == "bank_transfer":
            analysis_parts.append(
                f"Havale ile ödeme istediğin için havale fiyatı dikkate alındı. "
                f"Bu ürünün havale fiyatı {money(top.get('bank_transfer_price', 0))}."
            )
        elif payment_preference in ["installment", "installment_3", "installment_6", "installment_9"]:
            analysis_parts.append(
                "Taksitli ödeme istediğin için taksit uygunluğu ve taksit toplamları değerlendirildi."
            )
        else:
            analysis_parts.append(
                "Ödeme seçenekleri fiyatla birlikte değerlendirildi."
            )

    elif priority == "energy":
        if specs.get("Enerji Sınıfı"):
            analysis_parts.append(
                f"Enerji verimliliği açısından {specs.get('Enerji Sınıfı')} enerji sınıfı dikkate alındı."
            )

    elif priority == "capacity":
        if specs.get("Kapasite"):
            analysis_parts.append(
                f"Kapasite ihtiyacına göre {specs.get('Kapasite')} kapasite bilgisi öne çıktı."
            )

    elif priority == "performance":
        perf_text = []

        if specs.get("İşlemci"):
            perf_text.append(f"işlemci {specs.get('İşlemci')}")
        if specs.get("RAM"):
            perf_text.append(f"RAM {specs.get('RAM')}")
        if specs.get("Depolama"):
            perf_text.append(f"depolama {specs.get('Depolama')}")

        if perf_text:
            analysis_parts.append(
                "Performans tarafında " + ", ".join(perf_text) + " bilgileri dikkate alındı."
            )

    elif priority == "usage":
        if specs.get("Kullanım Amacı"):
            analysis_parts.append(
                f"Kullanım amacı olarak {specs.get('Kullanım Amacı')} ihtiyacına uygun görünüyor."
            )

    feature_parts = []

    if specs.get("Kapasite"):
        feature_parts.append(f"kapasite {specs.get('Kapasite')}")
    if specs.get("Enerji Sınıfı"):
        feature_parts.append(f"enerji sınıfı {specs.get('Enerji Sınıfı')}")
    if specs.get("RAM"):
        feature_parts.append(f"RAM {specs.get('RAM')}")
    if specs.get("Depolama"):
        feature_parts.append(f"depolama {specs.get('Depolama')}")
    if specs.get("Garanti"):
        feature_parts.append(f"garanti {specs.get('Garanti')}")

    if feature_parts:
        analysis_parts.append(
            "Ürünün öne çıkan bilgileri: " + ", ".join(feature_parts) + "."
        )

    if payment_analysis.get("advice"):
        payment_sentence = payment_analysis["advice"]
    else:
        payment_sentence = (
            f"Liste fiyatı {price}. 6 taksit seçeneğinde aylık yaklaşık "
            f"{calculate_installment(top.get('price', 0), 6):.0f} TL olur."
        )

    alternative_sentence = ""

    if alternatives:
        alternative_names = ", ".join([
            item.get("product_name", "")
            for item in alternatives
            if item.get("product_name", "")
        ])

        if alternative_names:
            alternative_sentence = (
                f"Alternatif olarak {alternative_names} ürünlerini de inceleyebilirsin."
            )

    final_sentence = (
        "Bu nedenle ilk seçenek olarak bu ürünü göstermek mantıklı; "
        "ancak ödeme yöntemi, bütçe veya kullanım önceliği değişirse öneri sıralaması da değişebilir."
    )

    message = (
        f"{intro} "
        f"{' '.join(analysis_parts)} "
        f"{payment_sentence} "
        f"{alternative_sentence} "
        f"{final_sentence}"
    )

    return message.strip()


def try_llm_answer(user_query, query_info, products, fallback_message):
    if llm_service is None:
        return fallback_message

    try:
        if hasattr(llm_service, "is_enabled") and not llm_service.is_enabled():
            return fallback_message

        if hasattr(llm_service, "generate_shopping_answer"):
            message = llm_service.generate_shopping_answer(
                user_query=user_query,
                query_info=query_info,
                products=products,
                fallback_message=fallback_message
            )

            return clean_llm_message(message)

    except Exception:
        return fallback_message

    return fallback_message


def build_similar_products(user_query):
    products, query_info = engine.recommend(user_query, top_n=4)

    if not products:
        return [], "Benzer ürün bulamadım. Ürün adını veya kategoriyi biraz daha net yazabilirsiniz.", query_info

    message = (
        "Benzer veya alternatif ürünleri kategori, açıklama, fiyat aralığı, stok durumu "
        "ve ödeme seçenekleri birlikte değerlendirilerek listeledim."
    )

    return products, message, query_info


def handle_ai_assistant(user_query):
    query_info = engine.understand_query(user_query)
    intent = query_info.get("intent", "recommendation")

    if intent == "bundle_recommendation":
        products, message = engine.recommend_ceyiz_bundle(user_query)

    elif intent == "student_laptop":
        products, message = engine.recommend_student_laptops(user_query)

    elif intent == "comparison":
        products, message = engine.compare(user_query)

    elif intent == "similar":
        products, message, query_info = build_similar_products(user_query)

    else:
        products, query_info = engine.recommend(user_query, top_n=6)

        message = build_professional_ai_message(
            user_query=user_query,
            query_info=query_info,
            products=products
        )

    message = try_llm_answer(
        user_query=user_query,
        query_info=query_info,
        products=products,
        fallback_message=message
    )

    save_last_result(
        area="ai_assistant",
        user_query=user_query,
        query_info=query_info,
        message=message,
        products=products
    )


def compare_selected_products(row1, row2, focus_text):
    user_query = (
        f"{row1['product_name']} ile {row2['product_name']} ürünlerini "
        f"{focus_text if focus_text else 'fiyat, ödeme, kullanım kolaylığı ve özellikler'} açısından karşılaştır"
    )

    query_info = engine.understand_query(user_query)
    focus = normalize_text(focus_text)

    if "kullanim" in focus or "kolay" in focus or "pratik" in focus or "gunluk" in focus:
        query_info["priority"] = "usage"

    elif "kapasite" in focus or "hacim" in focus or "litre" in focus or "lt" in focus:
        query_info["priority"] = "capacity"

    elif "enerji" in focus or "tasarruf" in focus or "a+" in focus:
        query_info["priority"] = "energy"

    elif "senet" in focus:
        query_info["priority"] = "payment"
        query_info["payment_preference"] = "senet"

    elif "havale" in focus:
        query_info["priority"] = "payment"
        query_info["payment_preference"] = "bank_transfer"

    elif "taksit" in focus or "odeme" in focus:
        query_info["priority"] = "payment"

    elif (
        "performans" in focus
        or "islemci" in focus
        or "ram" in focus
        or "depolama" in focus
        or "ssd" in focus
    ):
        query_info["priority"] = "performance"

    elif "fiyat" in focus or "ucuz" in focus or "uygun" in focus:
        query_info["priority"] = "price"

    if hasattr(engine, "compare_rows"):
        return engine.compare_rows(row1, row2, query_info)

    products, _ = engine.recommend(user_query, top_n=2)

    return products, "Karşılaştırma motoru çalıştırıldı."


# =====================================================
# QUICK SUPPORT LOGIC
# =====================================================

def build_cart_response():
    cart_df = get_products_by_ids(st.session_state.cart)

    if cart_df.empty:
        return "Sepetiniz şu anda boş.", []

    total = cart_total()
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
        f"Sepetinizde {len(products)} ürün var. Toplam tutar {money(total)}. "
        f"6 taksit ile aylık yaklaşık {monthly:.0f} TL."
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


def behavior_favorite_suggestion():
    favorite_ids = extract_product_ids(st.session_state.favorites)

    if not favorite_ids:
        return [], "Favorilerinde ürün olmadığı için alternatif öneri oluşturamadım."

    if behavior_engine:
        return behavior_engine.favorite_followup_suggestion(favorite_ids)

    first = get_products_by_ids([favorite_ids[-1]])
    query = first.iloc[0]["product_name"] if not first.empty else "benzer ürün"

    products, _ = engine.recommend(query, top_n=4)
    products = [
        product for product in products
        if str(product.get("product_id")) not in favorite_ids
    ][:3]

    return products, "Favoriye eklediğiniz ürüne göre benzer alternatifleri listeledim."


def behavior_cart_suggestion():
    cart_ids = extract_product_ids(st.session_state.cart)

    if not cart_ids:
        return [], "Sepetinde ürün olmadığı için daha uygun alternatif öneremedim."

    if behavior_engine:
        return behavior_engine.cart_abandonment_suggestion(cart_ids)

    cart_df = get_products_by_ids([cart_ids[-1]])

    if cart_df.empty:
        return [], "Sepetteki ürünü ürün listesinde bulamadım."

    row = cart_df.iloc[0]

    cheaper = products_df[
        (products_df["category"] == row["category"])
        & (products_df["price"].apply(safe_number) < safe_number(row["price"]))
    ].sort_values("price").head(3)

    products = []

    for _, product_row in cheaper.iterrows():
        products.append(
            engine.product_to_json(
                product_row,
                reason=f"{row['product_name']} ürününe göre daha uygun fiyatlı alternatiftir.",
                score=0.78
            )
        )

    return products, "Sepetteki ürüne göre daha uygun fiyatlı alternatifleri listeledim."


def build_order_tracking_response():
    order = latest_order()

    if order is None:
        return "Henüz oluşturulmuş siparişiniz bulunmuyor."

    if order.get("is_cancelled"):
        return f"{order['order_id']} numaralı siparişiniz iptal edilmiş görünüyor."

    return (
        f"Son siparişiniz {order['order_id']} numarasıyla {order['status']} durumunda. "
        f"Kargo durumu: {order['cargo_status']} Tahmini teslimat: {order['estimated_delivery']}."
    )


def cancel_latest_order():
    order = latest_order()

    if order is None:
        return "İptal edilebilecek bir siparişiniz bulunmuyor."

    if order.get("status") == "Teslim edildi":
        return "Teslim edilmiş siparişlerde iptal yerine iade talebi oluşturabilirsiniz."

    order["is_cancelled"] = True
    order["status"] = "İptal edildi"

    return f"{order['order_id']} numaralı siparişiniz için iptal talebi oluşturuldu."


def return_latest_order():
    order = latest_order()

    if order is None:
        return "İade talebi oluşturulabilecek bir siparişiniz bulunmuyor."

    if order.get("is_cancelled"):
        return "İptal edilmiş sipariş için iade talebi oluşturulamaz."

    order["is_return_requested"] = True
    order["status"] = "İade talebi alındı"

    return f"{order['order_id']} numaralı siparişiniz için iade talebi oluşturuldu."


def handle_support_action(action):
    products = []
    query_info = {"intent": action}

    if action == "siparisim_nerede":
        message = build_order_tracking_response()

    elif action == "sepet":
        message, products = build_cart_response()

    elif action == "favoriler":
        message, products = build_favorites_response()

    elif action == "siparis_olustur":
        order = create_order_from_cart()

        if order is None:
            message = "Sipariş oluşturmak için önce sepete ürün eklemelisiniz."
        else:
            message = f"Siparişiniz oluşturuldu. Sipariş numaranız {order['order_id']}."

    elif action == "iade_baslat":
        message = return_latest_order()

    elif action == "iptal_et":
        message = cancel_latest_order()

    elif action == "adres_degistir":
        message = "Teslimat adresi değişikliği sipariş kargoya verilmeden önce yapılabilir."

    elif action == "fatura":
        message = "Faturanıza sipariş detay sayfasından ulaşabilirsiniz."

    elif action == "kampanya":
        message = "Kampanya ve kupon alanında havale indirimi, taksit ve senetli ödeme avantajları gösterilebilir."

    elif action == "hesabim":
        message = "Hesabım alanında üyelik, adresler, kayıtlı kartlar ve sipariş geçmişi yönetilebilir."

    elif action == "destek":
        message = "Destek talebinizi kargo, ürün, ödeme, iade veya üyelik başlığıyla oluşturabilirsiniz."

    else:
        message = "Size sepet, favori, sipariş, iade, kampanya ve hesap işlemlerinde yardımcı olabilirim."

    save_last_result(
        area="quick_support",
        user_query=action,
        query_info=query_info,
        message=message,
        products=products
    )


# =====================================================
# CSS
# =====================================================

st.markdown(
    """
    <style>
    :root {
        --blue: #1599D6;
        --cyan: #24B7E5;
        --navy: #173A5E;
        --purple: #6B2B8E;
        --magenta: #C3378A;
        --bg: #F6F8FF;
        --card: rgba(255,255,255,0.86);
        --border: rgba(110, 145, 190, 0.26);
        --text: #10233D;
        --muted: #607086;
        --shadow: 0 18px 45px rgba(23,58,94,0.11);
        --soft-shadow: 0 9px 26px rgba(23,58,94,0.07);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(36,183,229,0.22), transparent 30%),
            radial-gradient(circle at top right, rgba(195,55,138,0.18), transparent 28%),
            linear-gradient(135deg, #F7FCFF 0%, #F6F1FF 50%, #FFFFFF 100%);
    }

    .block-container {
        max-width: 1320px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, h5, h6, p, div, span, label {
        font-family: "Segoe UI", Arial, sans-serif !important;
        color: var(--text);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #EEF8FF 100%);
        border-right: 1px solid rgba(21,153,214,0.14);
    }

    [data-testid="collapsedControl"] {
        display: none !important;
    }

    button[kind="header"] {
        display: none !important;
    }

    .main-header {
        background:
            linear-gradient(135deg, rgba(21,153,214,0.98) 0%, rgba(107,43,142,0.96) 60%, rgba(195,55,138,0.90) 100%);
        border-radius: 30px;
        padding: 38px 42px;
        box-shadow: var(--shadow);
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }

    .main-header::after {
        content: "";
        position: absolute;
        right: -95px;
        top: -110px;
        width: 310px;
        height: 310px;
        background: rgba(255,255,255,0.15);
        border-radius: 999px;
    }

    .header-title {
        color: white !important;
        font-size: 40px;
        font-weight: 950;
        line-height: 1.08;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }

    .header-sub {
        color: rgba(255,255,255,0.95) !important;
        font-size: 15px;
        line-height: 1.7;
        max-width: 950px;
    }

    .header-badge {
        display: inline-block;
        margin-top: 18px;
        margin-right: 9px;
        margin-bottom: 8px;
        padding: 8px 14px;
        border-radius: 999px;
        background: rgba(255,255,255,0.17);
        border: 1px solid rgba(255,255,255,0.30);
        color: white !important;
        font-size: 12px;
        font-weight: 850;
    }

    .page-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 26px;
        padding: 24px 26px;
        box-shadow: var(--soft-shadow);
        backdrop-filter: blur(18px);
        margin-bottom: 18px;
    }

    .page-title {
        color: var(--navy) !important;
        font-size: 25px;
        font-weight: 950;
        margin-bottom: 6px;
    }

    .page-sub {
        color: var(--muted) !important;
        font-size: 14px;
        line-height: 1.65;
    }

    .metric-card {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 20px;
        box-shadow: var(--soft-shadow);
        min-height: 124px;
    }

    .metric-label {
        color: var(--muted) !important;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .metric-value {
        color: var(--purple) !important;
        font-size: 32px;
        font-weight: 950;
        line-height: 1.1;
    }

    .metric-sub {
        color: var(--muted) !important;
        font-size: 12px;
        margin-top: 7px;
    }

    .quick-box {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 20px;
        box-shadow: var(--soft-shadow);
        min-height: 132px;
        margin-bottom: 12px;
    }

    .quick-title {
        color: var(--navy) !important;
        font-size: 18px;
        font-weight: 950;
        margin-bottom: 8px;
    }

    .quick-text {
        color: var(--muted) !important;
        font-size: 13px;
        line-height: 1.55;
    }

    .product-card-shell {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--border);
        border-radius: 28px;
        padding: 20px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(18px);
        margin-bottom: 20px;
    }

    .product-title {
        color: var(--navy) !important;
        font-size: 20px;
        font-weight: 950;
        margin-bottom: 4px;
    }

    .product-meta {
        color: var(--muted) !important;
        font-size: 13px;
        margin-bottom: 10px;
    }

    .product-price {
        background: linear-gradient(90deg, var(--purple), var(--magenta));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 30px;
        font-weight: 950;
        margin-bottom: 10px;
    }

    .badge {
        display: inline-block;
        background: rgba(21,153,214,0.10);
        color: var(--navy) !important;
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
        color: var(--purple) !important;
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
        color: var(--text) !important;
        font-size: 13.5px;
        line-height: 1.65;
    }

    .chat-user {
        background: rgba(21,153,214,0.10);
        border: 1px solid rgba(21,153,214,0.20);
        border-radius: 20px;
        padding: 15px 17px;
        margin: 11px 0;
        color: var(--text) !important;
        font-size: 14px;
        line-height: 1.6;
    }

    .chat-bot {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--border);
        border-left: 6px solid var(--purple);
        border-radius: 20px;
        padding: 15px 17px;
        margin: 11px 0;
        box-shadow: var(--soft-shadow);
        color: var(--text) !important;
        font-size: 14px;
        line-height: 1.6;
    }

    .chat-role {
        color: var(--purple) !important;
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
        color: var(--navy);
        font-weight: 850;
        min-height: 44px;
        box-shadow: 0 6px 16px rgba(23,58,94,0.06);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--blue), var(--purple));
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
        border: 1px solid var(--border);
        border-radius: 16px 16px 0 0;
        padding: 11px 16px;
        font-weight: 850;
        color: var(--navy);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(21,153,214,0.14), rgba(107,43,142,0.12)) !important;
        color: var(--purple) !important;
        border-bottom: 2px solid var(--purple);
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(120,160,200,0.18);
        border-radius: 16px;
        padding: 10px 12px;
    }

    div[data-testid="stExpander"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: var(--soft-shadow);
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# UI COMPONENTS
# =====================================================

def render_header():
    st.markdown(
        """
        <div class="main-header">
            <div class="header-title">Nevade AI Shopping Assistant</div>
            <div class="header-sub">
                Kullanıcının ihtiyacını doğal dille anlayan, ürünleri fiyat, ödeme, stok,
                kullanım amacı ve teknik özelliklere göre sıralayan profesyonel alışveriş asistanı.
            </div>
            <span class="header-badge">AI Ürün Önerisi</span>
            <span class="header-badge">Ödeme Analizi</span>
            <span class="header-badge">Ürün Karşılaştırma</span>
            <span class="header-badge">Sepet & Favori Davranışı</span>
            <span class="header-badge">API Hazır</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_page_intro(title, subtitle):
    st.markdown(
        f"""
        <div class="page-card">
            <div class="page-title">{title}</div>
            <div class="page-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metrics():
    total_products = len(products_df)
    total_categories = products_df["category"].nunique()
    total_brands = products_df["brand"].nunique()
    cart_count = len(st.session_state.cart)

    c1, c2, c3, c4 = st.columns(4)

    metrics = [
        ("Ürün", total_products, "Yüklü ürün sayısı"),
        ("Kategori", total_categories, "Aktif kategori"),
        ("Marka", total_brands, "Tanımlı marka"),
        ("Sepet", cart_count, "Sepetteki ürün")
    ]

    for col, (label, value, sub) in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def show_chat_message(message):
    role = message.get("role", "")
    content = message.get("content", "")

    if role == "user":
        css_class = "chat-user"
        role_title = "Sen"
    else:
        css_class = "chat-bot"
        role_title = "Nevade Asistan"

    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="chat-role">{role_title}</div>
            {content}
        </div>
        """,
        unsafe_allow_html=True
    )


def show_product_card(product, key_prefix):
    st.markdown("<div class='product-card-shell'>", unsafe_allow_html=True)

    image_col, info_col = st.columns([1, 2.5], gap="large")

    with image_col:
        image = get_product_image(product)

        if image:
            st.image(image, use_container_width=True)
        else:
            st.markdown(
                """
                <div class="reason-box" style="height:150px; display:flex; align-items:center; justify-content:center; text-align:center;">
                    Ürün görseli yok
                </div>
                """,
                unsafe_allow_html=True
            )

    with info_col:
        specs = product.get("specs", {}) or {}

        st.markdown(
            f"""
            <div class="product-title">{product.get('product_name', '')}</div>
            <div class="product-meta">
                Product ID: {product.get('product_id', '')} |
                {product.get('category', '')} |
                {product.get('brand', '')} |
                {product.get('stock_status', '')}
            </div>
            <div class="product-price">{money(product.get('price', 0))}</div>
            """,
            unsafe_allow_html=True
        )

        badges = []

        if product.get("match_label"):
            badges.append(f"<span class='badge-purple'>{product.get('match_label')}</span>")

        for spec_key in ["Enerji Sınıfı", "Kapasite", "RAM", "Depolama", "Kullanım Amacı"]:
            if specs.get(spec_key):
                badges.append(f"<span class='badge'>{spec_key}: {specs.get(spec_key)}</span>")

        if badges:
            st.markdown("".join(badges), unsafe_allow_html=True)

        pay1, pay2, pay3 = st.columns(3)

        with pay1:
            st.metric("Havale", money(product.get("bank_transfer_price", 0)))

        with pay2:
            st.metric("6 Taksit", f"{calculate_installment(product.get('price', 0), 6):.0f} TL")

        with pay3:
            st.metric("Senetli Toplam", money(product.get("senet_total_price", 0)))

        st.markdown(
            f"""
            <div class="reason-box">
                <b>Neden önerildi?</b><br>
                {product.get('reason', 'Bu ürün ihtiyacınıza uygun olduğu için önerildi.')}
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("Teknik özellikler ve ödeme detayları"):
            left, right = st.columns(2)

            with left:
                st.write("**Teknik Özellikler**")
                if specs:
                    for key, value in specs.items():
                        if str(value).strip():
                            st.write(f"- **{key}:** {value}")
                else:
                    st.write("Teknik özellik bilgisi yok.")

            with right:
                st.write("**Ödeme Seçenekleri**")
                payment_items = [
                    ("Peşin", "cash_price"),
                    ("Havale", "bank_transfer_price"),
                    ("Kart", "card_price"),
                    ("3 Taksit Toplam", "installment_3_total"),
                    ("6 Taksit Toplam", "installment_6_total"),
                    ("9 Taksit Toplam", "installment_9_total"),
                    ("Senetli Toplam", "senet_total_price"),
                    ("Senet 9 Ay Aylık", "senet_monthly_9")
                ]

                for label, key in payment_items:
                    value = safe_number(product.get(key, 0))
                    if value > 0:
                        st.write(f"- **{label}:** {money(value)}")

    product_id = str(product.get("product_id", ""))

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("Sepete Ekle", key=f"{key_prefix}_cart_{product_id}"):
            add_to_cart(product_id)
            st.success("Sepete eklendi.")
            st.rerun()

    with b2:
        if st.button("Favoriye Ekle", key=f"{key_prefix}_fav_{product_id}"):
            add_to_favorites(product_id)
            st.success("Favorilere eklendi.")
            st.rerun()

    with b3:
        if st.button("Sepetten Çıkar", key=f"{key_prefix}_rm_cart_{product_id}"):
            remove_from_cart(product_id)
            st.info("Sepetten çıkarıldı.")
            st.rerun()

    with b4:
        if st.button("Favoriden Çıkar", key=f"{key_prefix}_rm_fav_{product_id}"):
            remove_from_favorites(product_id)
            st.info("Favorilerden çıkarıldı.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def show_product_list(products, prefix):
    if not products:
        st.info("Gösterilecek ürün bulunamadı.")
        return

    for index, product in enumerate(products):
        show_product_card(
            product,
            key_prefix=f"{prefix}_{index}_{product.get('product_id', '')}"
        )


def show_messages(messages, prefix):
    if not messages:
        st.info("Henüz konuşma başlamadı.")
        return

    for msg_index, message in enumerate(messages):
        show_chat_message(message)

        if message.get("query_info"):
            with st.expander("Algılama sonucu"):
                st.json(message.get("query_info", {}))

        if message.get("products"):
            show_product_list(
                message["products"],
                prefix=f"{prefix}_{msg_index}"
            )


# =====================================================
# MAIN UI
# =====================================================

render_header()

tabs = st.tabs([
    "Ana Sayfa",
    "AI Asistan",
    "Ürün Karşılaştır",
    "Sepet & Favoriler",
    "Hızlı İşlemler",
    "API / Teknik Çıktı"
])


# =====================================================
# ANA SAYFA
# =====================================================

with tabs[0]:
    render_page_intro(
        "Nevade AI Alışveriş Asistanı",
        "Doğal dil ile ürün önerisi, ödeme avantajı analizi, ürün karşılaştırma, sepet/favori davranışı ve API çıktısı özelliklerini tek sistemde gösteren profesyonel demo."
    )

    render_metrics()

    st.markdown("---")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="quick-box">
                <div class="quick-title">Doğal Dil ile Ürün Bul</div>
                <div class="quick-text">Kullanıcı ürün adını bilmeden ihtiyacını yazar; sistem doğru kategori ve ürünü önerir.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div class="quick-box">
                <div class="quick-title">Ödeme Avantajı Analizi</div>
                <div class="quick-text">Senet, havale, peşin ve taksit seçenekleri ürün bazında değerlendirilir.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div class="quick-box">
                <div class="quick-title">Sepet & Favori Davranışı</div>
                <div class="quick-text">Kullanıcının favori ve sepet davranışına göre alternatif ürün önerilir.</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =====================================================
# AI ASISTAN
# =====================================================

with tabs[1]:
    render_page_intro(
        "AI Asistan",
        "İhtiyacınızı doğal cümleyle yazın. Sistem ürün tipi, bütçe, ödeme yöntemi, stok ve teknik özellikleri analiz ederek öneri üretir."
    )

    ai_input = st.text_area(
        "İhtiyacınızı yazın",
        placeholder="Örn: senetle uyguna gelen bir buzdolabı öner / öğrenci için uygun fiyatlı laptop öner / çeyiz için 50000 TL civarı ürün öner",
        height=120,
        key="ai_input"
    )

    ask_col, clear_col = st.columns([1, 1])

    with ask_col:
        if st.button("AI Asistana Sor", key="ask_ai"):
            if ai_input.strip():
                handle_ai_assistant(ai_input)
                st.rerun()
            else:
                st.warning("Lütfen bir alışveriş ihtiyacı yaz.")

    with clear_col:
        if st.button("Konuşmayı Temizle", key="clear_ai"):
            st.session_state.ai_messages = []
            st.rerun()

    st.markdown("---")
    st.subheader("Konuşma ve Ürün Önerileri")
    show_messages(st.session_state.ai_messages, "ai")


# =====================================================
# URUN KARSILASTIR
# =====================================================

with tabs[2]:
    render_page_intro(
        "Ürün Karşılaştır",
        "İki ürünü seçin, kriter yazın. Sistem fiyat, senet, havale, enerji, kapasite, performans veya kullanım kolaylığına göre karar verir."
    )

    compare_categories = sorted(products_df["category"].dropna().unique().tolist())

    selected_category = st.selectbox(
        "Kategori seç",
        compare_categories,
        key="compare_category"
    )

    category_products_df = products_df[
        products_df["category"] == selected_category
    ].copy()

    product_options = category_products_df["product_name"].tolist()

    p1, p2 = st.columns(2)

    with p1:
        selected_product_1 = st.selectbox(
            "1. ürün",
            product_options,
            key="compare_product_1"
        )

    with p2:
        selected_product_2 = st.selectbox(
            "2. ürün",
            product_options,
            key="compare_product_2"
        )

    focus = st.text_input(
        "Karşılaştırma kriteri",
        placeholder="Örn: kullanım kolaylığı, fiyat, senet, havale, enerji sınıfı, kapasite, işlemci",
        key="compare_focus"
    )

    if st.button("Ürünleri Karşılaştır", key="compare_btn"):
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
                f"{focus if focus else 'fiyat, ödeme, kullanım kolaylığı ve özellikler'} açısından karşılaştır"
            )

            products, message = compare_selected_products(row1, row2, focus)

            query_info = engine.understand_query(user_query)
            query_info["source"] = "manual_comparison"
            query_info["comparison_focus"] = focus

            save_last_result(
                area="ai_assistant",
                user_query=user_query,
                query_info=query_info,
                message=message,
                products=products
            )

            st.rerun()

    st.markdown("---")
    show_messages(st.session_state.ai_messages, "comparison")


# =====================================================
# SEPET FAVORI
# =====================================================

with tabs[3]:
    render_page_intro(
        "Sepet & Favoriler",
        "Sepete ve favorilere eklenen ürünleri görüntüleyin. Buradan sipariş oluşturabilir veya davranış bazlı alternatif alabilirsiniz."
    )

    cart_col, fav_col = st.columns(2)

    with cart_col:
        st.subheader("Sepet")

        cart_df = get_products_by_ids(st.session_state.cart)

        if cart_df.empty:
            st.info("Sepet boş.")
        else:
            st.success(f"Sepet toplamı: {money(cart_total())}")

            for _, row in cart_df.iterrows():
                st.write(f"**{row['product_name']}** — {money(row['price'])}")

            if st.button("Sipariş Oluştur", key="create_order_from_cart_page"):
                order = create_order_from_cart()

                if order:
                    st.success(f"Sipariş oluşturuldu: {order['order_id']}")
                    st.rerun()

        if st.button("Sepetime Göre Daha Uygun Alternatif Bul", key="cart_behavior_page"):
            products, message = behavior_cart_suggestion()

            save_last_result(
                area="quick_support",
                user_query="Sepetime göre daha uygun alternatif bul",
                query_info={
                    "intent": "cart_behavior",
                    "cart_ids": extract_product_ids(st.session_state.cart)
                },
                message=message,
                products=products
            )

            st.rerun()

    with fav_col:
        st.subheader("Favoriler")

        fav_df = get_products_by_ids(st.session_state.favorites)

        if fav_df.empty:
            st.info("Favori ürün yok.")
        else:
            for _, row in fav_df.iterrows():
                st.write(f"**{row['product_name']}** — {money(row['price'])}")

        if st.button("Favorilerime Göre Alternatif Öner", key="favorite_behavior_page"):
            products, message = behavior_favorite_suggestion()

            save_last_result(
                area="quick_support",
                user_query="Favorilerime göre alternatif öner",
                query_info={
                    "intent": "favorite_behavior",
                    "favorite_ids": extract_product_ids(st.session_state.favorites)
                },
                message=message,
                products=products
            )

            st.rerun()

    st.markdown("---")
    st.subheader("Sepet / Favori Önerileri")
    show_messages(st.session_state.support_messages, "basket")


# =====================================================
# HIZLI ISLEMLER
# =====================================================

with tabs[4]:
    render_page_intro(
        "Hızlı İşlemler",
        "Sipariş takibi, fatura, adres değişikliği, iade, iptal, kampanya ve hesap işlemleri için demo destek merkezi."
    )

    q1, q2, q3 = st.columns(3)

    with q1:
        if st.button("Siparişim Nerede?", key="q_order"):
            handle_support_action("siparisim_nerede")
            st.rerun()

    with q2:
        if st.button("Sepetim", key="q_cart"):
            handle_support_action("sepet")
            st.rerun()

    with q3:
        if st.button("Favorilerim", key="q_fav"):
            handle_support_action("favoriler")
            st.rerun()

    q4, q5, q6 = st.columns(3)

    with q4:
        if st.button("Sipariş Oluştur", key="q_create_order"):
            handle_support_action("siparis_olustur")
            st.rerun()

    with q5:
        if st.button("İptal Et", key="q_cancel"):
            handle_support_action("iptal_et")
            st.rerun()

    with q6:
        if st.button("İade Başlat", key="q_return"):
            handle_support_action("iade_baslat")
            st.rerun()

    q7, q8, q9 = st.columns(3)

    with q7:
        if st.button("Faturama Nasıl Ulaşırım?", key="q_invoice"):
            handle_support_action("fatura")
            st.rerun()

    with q8:
        if st.button("Adres Değiştir", key="q_address"):
            handle_support_action("adres_degistir")
            st.rerun()

    with q9:
        if st.button("Kampanya ve Kupon", key="q_campaign"):
            handle_support_action("kampanya")
            st.rerun()

    st.markdown("---")

    if st.button("Hızlı İşlem Cevaplarını Temizle", key="clear_support_messages"):
        st.session_state.support_messages = []
        st.rerun()

    st.subheader("Hızlı İşlem Cevapları")
    show_messages(st.session_state.support_messages, "support")


# =====================================================
# API / DEBUG
# =====================================================

with tabs[5]:
    render_page_intro(
        "API / Teknik Çıktı",
        "Bu alan normal kullanıcı için değil; proje sunumu ve entegrasyon mantığını göstermek için product_id bazlı JSON çıktısını gösterir."
    )

    st.subheader("Son API JSON Çıktısı")

    st.code(
        json.dumps(
            st.session_state.last_api_response,
            ensure_ascii=False,
            indent=4
        ),
        language="json"
    )

    st.markdown("---")

    st.subheader("Sistem Durumu")

    llm_status = (
        "Aktif"
        if llm_service and hasattr(llm_service, "is_enabled") and llm_service.is_enabled()
        else "Lokal motor"
    )

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.metric("Öneri Motoru", "Aktif")

    with status_col2:
        st.metric("LLM", llm_status)

    with status_col3:
        st.metric("Product ID JSON", "Hazır")