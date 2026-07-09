import re
import pandas as pd


# =====================================================
# RESPONSE ENGINE
# Amaç:
# Karar motorunun seçtiği ürünü daha doğal, premium ve satış odaklı metne çevirmek.
# LLM çalışmasa bile cevaplar şablon gibi görünmesin.
# =====================================================


def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }

    for tr_char, simple_char in replacements.items():
        text = text.replace(tr_char, simple_char)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def safe_number(value):
    try:
        if pd.isna(value):
            return 0

        if isinstance(value, str):
            value = (
                value.replace("TL", "")
                .replace("₺", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )

        return float(value)

    except Exception:
        return 0


def money(value):
    return f"{safe_number(value):,.0f} TL".replace(",", ".")


def clean_value(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def detect_customer_focus(question, query_info=None):
    q = normalize_text(question)
    query_info = query_info or {}

    focus = {
        "student": False,
        "ceyiz": False,
        "budget": False,
        "lowest_monthly": False,
        "lowest_total": False,
        "installment": False,
        "stock": False,
        "comparison": False,
        "gift": False,
        "home": False,
    }

    if any(x in q for x in ["ogrenci", "ders", "okul", "universite", "odev", "sunum"]):
        focus["student"] = True

    if any(x in q for x in ["ceyiz", "evleniyorum", "dugun", "ev kuruyorum", "ev diziyorum", "paket"]):
        focus["ceyiz"] = True

    if query_info.get("budget") or any(x in q for x in ["butce", "tl", "fiyat", "ucuz", "uygun"]):
        focus["budget"] = True

    if query_info.get("payment_priority") == "lowest_monthly" or any(x in q for x in ["senet", "aylik", "elden odeme"]):
        focus["lowest_monthly"] = True

    if query_info.get("payment_priority") == "lowest_total" or any(x in q for x in ["havale", "pesin", "nakit", "en uygun"]):
        focus["lowest_total"] = True

    if query_info.get("payment_priority") == "card_installment" or any(x in q for x in ["taksit", "kart"]):
        focus["installment"] = True

    if any(x in q for x in ["stok", "var mi", "mevcut"]):
        focus["stock"] = True

    if any(x in q for x in ["karsilastir", "hangisi", "daha iyi", "alternatif"]):
        focus["comparison"] = True

    if any(x in q for x in ["hediye", "anneme", "babama", "esime"]):
        focus["gift"] = True

    if any(x in q for x in ["ev", "salon", "mutfak", "balkon", "oda"]):
        focus["home"] = True

    return focus


def product_type_label(row):
    text = normalize_text(
        f"{row.get('product_name', '')} {row.get('category', '')} {row.get('description', '')} {row.get('features', '')}"
    )

    if "buzdolabi" in text or "no frost" in text:
        return "buzdolabı"

    if "camasir" in text:
        return "çamaşır makinesi"

    if "bulasik" in text:
        return "bulaşık makinesi"

    if "televizyon" in text or "smart tv" in text or re.search(r"\btv\b", text):
        return "televizyon"

    if "supurge" in text:
        return "süpürge"

    if "laptop" in text or "bilgisayar" in text or "notebook" in text:
        return "laptop"

    if "telefon" in text or "iphone" in text or "galaxy" in text:
        return "telefon"

    return "ürün"


def usage_sentence(row, question, query_info=None):
    focus = detect_customer_focus(question, query_info)
    ptype = product_type_label(row)

    product_name = clean_value(row.get("product_name"))
    description = clean_value(row.get("description"))
    features = clean_value(row.get("features"))
    use_case = clean_value(row.get("use_case"))

    if focus["student"] and ptype == "laptop":
        return (
            f"{product_name}, öğrenci kullanımı için mantıklı bir seçenek. "
            f"Ders takibi, ödev, sunum hazırlama, internet kullanımı ve temel ofis işleri için uygun bir model olarak öne çıkıyor."
        )

    if focus["student"] and ptype == "telefon":
        return (
            f"{product_name}, öğrenci ve günlük kullanım için değerlendirilebilecek bir seçenek. "
            f"Sosyal medya, iletişim, kamera ve temel uygulama kullanımı için dengeli bir model olarak öne çıkıyor."
        )

    if focus["ceyiz"]:
        return (
            f"{product_name}, çeyiz veya yeni ev kurulumunda değerlendirilebilecek ürünlerden biri. "
            f"Ev kullanımı, ödeme seçenekleri ve stok durumu açısından paket içinde konumlandırılabilir."
        )

    if ptype == "buzdolabı":
        return (
            f"{product_name}, ev kullanımı için geniş hacimli ve pratik bir buzdolabı seçeneği olarak öne çıkıyor. "
            f"Özellikle düzenli mutfak kullanımı ve çeyiz ihtiyacı için değerlendirilebilir."
        )

    if ptype == "çamaşır makinesi":
        return (
            f"{product_name}, günlük çamaşır ihtiyacı için uygun bir model. "
            f"Ev ve çeyiz kullanımı tarafında ekonomik ve pratik bir seçenek olarak değerlendirilebilir."
        )

    if ptype == "televizyon":
        return (
            f"{product_name}, salon kullanımı, film-dizi izleme ve akıllı TV deneyimi için öne çıkan bir seçenek. "
            f"Geniş ekran isteyen müşteriler için uygun şekilde anlatılabilir."
        )

    if ptype == "süpürge":
        return (
            f"{product_name}, ev temizliği için tamamlayıcı ve pratik bir ürün. "
            f"Çeyiz paketi veya günlük ev kullanımı için değerlendirilebilir."
        )

    if ptype == "telefon":
        return (
            f"{product_name}, günlük kullanım, sosyal medya ve kamera ihtiyacı için dengeli bir seçenek olarak öne çıkıyor."
        )

    if description:
        return f"{product_name}, {description[:180].strip()}"

    if features:
        return f"{product_name}, {features[:180].strip()} özellikleriyle öne çıkıyor."

    if use_case:
        return f"{product_name}, {use_case} için değerlendirilebilecek bir ürün."

    return f"{product_name}, talebinize uygun seçeneklerden biri olarak öne çıkıyor."


def payment_sentence(row, query_info=None):
    query_info = query_info or {}

    payment_priority = query_info.get("payment_priority")

    list_price = money(row.get("price", 0))
    bank_price = money(row.get("bank_transfer_price", 0))
    installment_total = money(row.get("installment_6_total", 0))
    installment_monthly = money(safe_number(row.get("installment_6_total", 0)) / 6)
    senet_total = money(row.get("senet_total_price", 0))
    senet_monthly = money(row.get("senet_monthly_9", 0))

    if payment_priority == "lowest_total":
        return (
            f"Liste fiyatı {list_price}. Toplam maliyeti düşük tutmak isteyen müşteri için "
            f"havale fiyatı daha avantajlı görünüyor: {bank_price}."
        )

    if payment_priority == "lowest_monthly":
        return (
            f"Liste fiyatı {list_price}. Aylık ödeme kolaylığı isteyen müşteri için senetli ödeme seçeneği öne çıkarılabilir. "
            f"Senetli toplam {senet_total}, aylık yaklaşık {senet_monthly}."
        )

    if payment_priority == "card_installment":
        return (
            f"Liste fiyatı {list_price}. Kartla ödeme isteyen müşteri için 6 taksit toplamı {installment_total}, "
            f"aylık yaklaşık {installment_monthly} olarak anlatılabilir."
        )

    return (
        f"Liste fiyatı {list_price}. Toplam maliyeti düşük tutmak isteyen müşteriye havale fiyatı "
        f"({bank_price}), aylık ödeme kolaylığı isteyen müşteriye ise senetli ödeme "
        f"({senet_monthly}/ay) anlatılabilir."
    )


def stock_sentence(row):
    stock = clean_value(row.get("stock_status"))

    if normalize_text(stock) == "stokta":
        return "Ürün şu anda stokta görünüyor."

    if stock:
        return f"Stok durumu: {stock}. Satış öncesinde stok teyidi alınması iyi olur."

    return "Stok bilgisi görünmüyor; satış öncesinde mağazadan stok teyidi alınmalı."


def next_step_sentence(row, query_info=None):
    ptype = product_type_label(row)
    query_info = query_info or {}

    if query_info.get("payment_priority") == "lowest_monthly":
        return (
            "Müşteri aylık ödeme kolaylığına odaklanıyorsa, senetli ödeme tutarı üzerinden devam edilebilir. "
            "İsterseniz ürünü sepete ekleyip ödeme seçeneğini karşılaştırabilirsiniz."
        )

    if query_info.get("payment_priority") == "lowest_total":
        return (
            "Müşteri toplam fiyat avantajına odaklanıyorsa, havale seçeneği öne çıkarılabilir. "
            "İsterseniz ürünü sepete ekleyip diğer ödeme seçenekleriyle karşılaştırabilirsiniz."
        )

    if ptype == "laptop":
        return (
            "İsterseniz bu laptopu sepete ekleyebilir ya da benzer laptoplarla karşılaştırabilirsiniz."
        )

    if ptype == "buzdolabı":
        return (
            "İsterseniz ürünü sepete ekleyebilir veya çeyiz paketi içinde diğer beyaz eşyalarla birlikte değerlendirebilirsiniz."
        )

    return (
        "İsterseniz ürünü sepete ekleyebilir, ödeme seçeneğini karşılaştırabilir veya mağazadan stok teyidi alabilirsiniz."
    )


def generate_premium_customer_answer(decision_result, user_query):
    df = decision_result.get("result_df", pd.DataFrame())
    query_info = decision_result.get("query_info", {})

    if df is None or df.empty:
        return (
            "Bu talebe tam uygun bir ürün bulamadım. "
            "Ürün türünü, bütçeyi veya ödeme tercihini biraz daha net yazarsanız daha doğru öneri yapabilirim. "
            "Örneğin: “Öğrenci için 25 bin TL’ye kadar laptop” ya da “Senetli buzdolabı öner” gibi yazabilirsiniz."
        )

    row = df.iloc[0]

    intro = usage_sentence(row, user_query, query_info)
    stock = stock_sentence(row)
    payment = payment_sentence(row, query_info)
    next_step = next_step_sentence(row, query_info)

    return (
        f"{intro}\n\n"
        f"{stock} {payment}\n\n"
        f"{next_step}"
    )


def generate_premium_store_answer(decision_result, staff_question):
    df = decision_result.get("result_df", pd.DataFrame())
    query_info = decision_result.get("query_info", {})
    filter_info = decision_result.get("filter_info", {})

    if df is None or df.empty:
        return (
            "Müşteri talebi net bir ürünle eşleşmedi. "
            "Personel, müşteriden ürün türü, marka, bütçe veya ödeme tercihini netleştirmesini istemeli."
        )

    row = df.iloc[0]

    product_name = clean_value(row.get("product_name"))
    brand = clean_value(row.get("brand"))
    category = clean_value(row.get("category"))
    stock = clean_value(row.get("stock_status"))

    list_price = money(row.get("price", 0))
    bank_price = money(row.get("bank_transfer_price", 0))
    installment_total = money(row.get("installment_6_total", 0))
    installment_monthly = money(safe_number(row.get("installment_6_total", 0)) / 6)
    senet_total = money(row.get("senet_total_price", 0))
    senet_monthly = money(row.get("senet_monthly_9", 0))

    customer_ready = generate_premium_customer_answer(decision_result, staff_question)

    filter_note = ""

    if filter_info.get("active"):
        detected = ", ".join(filter_info.get("detected_types", []))
        filter_note = f"Strict ürün filtresi aktif çalıştı; yalnızca {detected} ürünleri değerlendirildi."

    elif filter_info.get("package_query"):
        filter_note = "Paket / çeyiz talebi algılandığı için çoklu kategori değerlendirmesine izin verildi."

    else:
        filter_note = "Net ürün tipi algılanmadığı için genel ürün eşleştirmesi yapıldı."

    return (
        f"Müşteri talebi:\n"
        f"Müşteri ürün ve ödeme bilgisi almak istiyor. {filter_note}\n\n"
        f"Müşteriye söylenecek hazır cevap:\n"
        f"{customer_ready}\n\n"
        f"Ürün ve ödeme özeti:\n"
        f"- Ürün: {product_name}\n"
        f"- Marka: {brand}\n"
        f"- Kategori: {category}\n"
        f"- Stok: {stock}\n"
        f"- Liste fiyatı: {list_price}\n"
        f"- Havale fiyatı: {bank_price}\n"
        f"- 6 taksit: {installment_total} / Aylık yaklaşık {installment_monthly}\n"
        f"- Senetli ödeme: {senet_total} / Aylık yaklaşık {senet_monthly}\n\n"
        f"Personel aksiyonu:\n"
        f"- Müşteri toplam uygun fiyat istiyorsa havale seçeneğini öne çıkarın.\n"
        f"- Aylık ödeme kolaylığı istiyorsa senetli ödeme seçeneğini anlatın.\n"
        f"- Satış öncesinde stok ve güncel ödeme koşullarını teyit edin."
    )