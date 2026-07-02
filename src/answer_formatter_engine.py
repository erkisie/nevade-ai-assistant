import pandas as pd

from src.customer_intelligence_engine import safe_number, money


def clean(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def get_best_price_text(row):
    bank = safe_number(row.get("bank_transfer_price", 0))
    cash = safe_number(row.get("cash_price", 0))
    card = safe_number(row.get("card_price", 0))
    price = safe_number(row.get("price", 0))

    options = []

    if bank > 0:
        options.append(("Havale", bank))

    if cash > 0:
        options.append(("Peşin", cash))

    if card > 0:
        options.append(("Kart", card))

    if price > 0:
        options.append(("Liste", price))

    if not options:
        return "Fiyat bilgisi bulunamadı."

    best_name, best_price = min(options, key=lambda x: x[1])

    return f"{best_name} fiyatı: {money(best_price)}"


def product_line(row):
    name = clean(row.get("product_name", ""))
    category = clean(row.get("category", ""))
    stock = clean(row.get("stock_status", ""))
    best_price = get_best_price_text(row)

    parts = [
        f"Ürün: {name}",
        f"Kategori: {category}" if category else "",
        best_price,
        f"Stok: {stock}" if stock else "",
    ]

    return "\n".join(f"- {p}" for p in parts if p)


def payment_line(row):
    lines = []

    bank = safe_number(row.get("bank_transfer_price", 0))
    price = safe_number(row.get("price", 0))
    installment_6 = safe_number(row.get("installment_6_total", 0))
    senet_total = safe_number(row.get("senet_total_price", 0))
    senet_monthly = safe_number(row.get("senet_monthly_9", 0))

    if bank > 0:
        if price > bank:
            lines.append(f"Havale ile {money(bank)}. Yaklaşık {money(price - bank)} avantaj sağlar.")
        else:
            lines.append(f"Havale ile {money(bank)}.")

    if installment_6 > 0:
        lines.append(f"6 taksit seçeneği: aylık yaklaşık {money(installment_6 / 6)}.")

    if senet_total > 0:
        if senet_monthly > 0:
            lines.append(f"Senetli ödeme: aylık yaklaşık {money(senet_monthly)}.")
        else:
            lines.append(f"Senetli toplam ödeme: {money(senet_total)}.")

    if not lines:
        lines.append("Bu ürün için ödeme alternatifi bilgisi sınırlı.")

    return "\n".join(f"- {line}" for line in lines)


def format_cart_rescue(result):
    df = result.get("result_df", pd.DataFrame())

    if df is None or df.empty:
        return (
            "Durum:\n"
            "Kart limiti veya ödeme tarafında sorun yaşanmış olabilir.\n\n"
            "Size önerim:\n"
            "Sepeti iptal etmeden önce daha uygun fiyatlı ürün, havale avantajı, taksit veya senetli ödeme seçeneklerini değerlendirebiliriz.\n\n"
            "Sonraki adım:\n"
            "İsterseniz bütçenize göre daha ekonomik ürünleri listeleyebilirim."
        )

    row = df.iloc[0]

    return (
        "Durum:\n"
        "Kart limitiniz yeterli gelmemiş olabilir. Sepeti iptal etmeden önce daha uygun bir alternatif önerebilirim.\n\n"
        "Alternatif ürün:\n"
        f"{product_line(row)}\n\n"
        "Ödeme avantajı:\n"
        f"{payment_line(row)}\n\n"
        "Sonraki adım:\n"
        "İsterseniz bu alternatifi en düşük fiyat, senetli ödeme veya en düşük aylık taksit seçeneğine göre yeniden sıralayabilirim."
    )


def format_product_recommendation(result):
    df = result.get("result_df", pd.DataFrame())
    analysis = result.get("customer_analysis", {})

    if df is None or df.empty:
        return (
            "Sonuç:\n"
            "İsteğinize uygun net bir ürün bulamadım.\n\n"
            "Ne yapabiliriz?\n"
            "Bütçe, marka veya ödeme tercihinizi yazarsanız daha doğru ürünler önerebilirim."
        )

    lines = []

    for _, row in df.head(3).iterrows():
        lines.append(product_line(row))

    category = analysis.get("category") or "ihtiyacınıza uygun"

    return (
        "Size önerim:\n"
        f"{category} kategorisinde öne çıkan ürünleri listeledim.\n\n"
        + "\n\n".join(lines)
        + "\n\nSonraki adım:\n"
        "İsterseniz bu ürünleri fiyat, taksit, senet veya havale avantajına göre karşılaştırabilirim."
    )


def format_payment_help(result):
    df = result.get("result_df", pd.DataFrame())

    if df is None or df.empty:
        return (
            "Ödeme bilgisi:\n"
            "Ödeme seçeneklerini kontrol edebilmem için ürün adını veya kategoriyi netleştirmeniz gerekiyor.\n\n"
            "Örnek:\n"
            "Senetle buzdolabı alabilir miyim?\n"
            "Havale avantajlı telefon var mı?"
        )

    row = df.iloc[0]

    return (
        "Ödeme seçenekleri:\n"
        f"{clean(row.get('product_name', 'Bu ürün'))} için ödeme alternatifleri aşağıdaki gibi:\n\n"
        f"{payment_line(row)}\n\n"
        "Sonraki adım:\n"
        "İsterseniz bu ürünü daha düşük aylık ödeme veya daha uygun peşin fiyat seçeneğine göre değerlendirebilirim."
    )


def format_package_answer(result):
    df = result.get("result_df", pd.DataFrame())
    query_info = result.get("query_info", {})
    budget = query_info.get("budget") or result.get("customer_analysis", {}).get("budget")
    total = query_info.get("package_total_price") or result.get("optimized_total")

    if df is None or df.empty:
        return (
            "Paket sonucu:\n"
            "Çeyiz/yeni ev paketi oluşturmak için yeterli ürün bulunamadı.\n\n"
            "Ne gerekli?\n"
            "Buzdolabı, çamaşır makinesi, televizyon, fırın ve küçük ev aleti ürünleriyle daha doğru paket oluşturulabilir."
        )

    lines = []

    for _, row in df.iterrows():
        group = clean(row.get("package_group", "Ürün"))
        name = clean(row.get("product_name", ""))
        price = money(row.get("package_price", row.get("price", 0)))
        stock = clean(row.get("stock_status", ""))

        lines.append(f"- {group}: {name} — {price} ({stock})")

    budget_text = ""

    if budget and total:
        diff = safe_number(total) - safe_number(budget)

        if diff <= 0:
            budget_text = f"Paket toplamı yaklaşık {money(total)}. Belirttiğiniz {money(budget)} bütçenin içinde kalıyor."
        else:
            budget_text = f"Paket toplamı yaklaşık {money(total)}. Bütçeyi yaklaşık {money(diff)} aşıyor."

    elif total:
        budget_text = f"Paket toplamı yaklaşık {money(total)}."

    return (
        "Paket önerisi:\n"
        "Yeni ev / çeyiz ihtiyacı için temel ürünlerden oluşan paket hazırladım.\n\n"
        + "\n".join(lines)
        + "\n\n"
        + budget_text
        + "\n\nSonraki adım:\n"
        "İsterseniz paketi en ekonomik, en dengeli veya senetli ödemeye uygun şekilde yeniden düzenleyebilirim."
    )


def format_order_support(result):
    return (
        "Sipariş desteği:\n"
        "Sipariş durumunu kontrol edebilmem için sipariş numarası gerekiyor.\n\n"
        "Örnek:\n"
        "NVD-1002 siparişim nerede?\n\n"
        "Sonraki adım:\n"
        "Sipariş numarasını yazarsanız kargo, teslimat ve durum bilgisini gösterebilirim."
    )


def format_general_help(result):
    return (
        "Size yardımcı olabilirim.\n\n"
        "Yapabileceklerim:\n"
        "- Ürün önerisi yapabilirim.\n"
        "- Çeyiz/yeni ev paketi hazırlayabilirim.\n"
        "- Kart limiti yetmezse daha uygun alternatif önerebilirim.\n"
        "- Senet, taksit veya havale seçeneklerini karşılaştırabilirim.\n"
        "- Sipariş ve kargo desteği sağlayabilirim.\n\n"
        "Örnek:\n"
        "50.000 TL çeyiz paketi yap\n"
        "Kart limitim yetmedi\n"
        "Annem için kolay telefon öner"
    )


def format_answer(result):
    decision = result.get("decision", "")

    if decision == "CART_RESCUE":
        return format_cart_rescue(result)

    if decision in ["PRODUCT_RECOMMENDATION", "NO_PRODUCT_TYPE_MATCH", "NO_BUDGET_MATCH"]:
        return format_product_recommendation(result)

    if decision in ["PAYMENT_HELP", "PAYMENT_ALTERNATIVE"]:
        return format_payment_help(result)

    if decision in [
        "PACKAGE_RECOMMENDATION",
        "BUDGET_OPTIMIZED",
        "BUDGET_PARTIALLY_OPTIMIZED",
        "BUDGET_OK",
    ]:
        return format_package_answer(result)

    if decision in ["ORDER_SUPPORT"]:
        return format_order_support(result)

    if decision in ["CHEAPER_ALTERNATIVE"]:
        return format_cart_rescue(result)
    
    if decision == "RANKING_REORDER":
        return result.get("answer", format_general_help(result))
    return format_general_help(result)