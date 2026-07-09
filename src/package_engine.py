import re
import pandas as pd


# =====================================================
# PACKAGE ENGINE
# Amaç:
# Çeyiz / ev kurma / paket taleplerinde farklı kategorilerden
# bütçeye uygun mantıklı ürün kombinasyonu oluşturmak.
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


def row_text(row):
    return normalize_text(
        f"{row.get('product_name', '')} "
        f"{row.get('category', '')} "
        f"{row.get('brand', '')} "
        f"{row.get('description', '')} "
        f"{row.get('features', '')} "
        f"{row.get('use_case', '')} "
        f"{row.get('payment_options', '')}"
    )


def is_package_request(query_info):
    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("normalized_query", "")
        or query_info.get("original_query", "")
    )

    package_words = [
        "ceyiz",
        "paket",
        "set",
        "ev kuruyorum",
        "ev diziyorum",
        "evleniyorum",
        "dugun",
        "yeni ev",
        "beyaz esya paketi",
    ]

    return any(word in q for word in package_words)


def detect_package_type(query_info):
    q = normalize_text(
        query_info.get("raw_query", "")
        or query_info.get("normalized_query", "")
        or query_info.get("original_query", "")
    )

    if any(x in q for x in ["ceyiz", "evleniyorum", "dugun"]):
        return "ceyiz"

    if any(x in q for x in ["ev kuruyorum", "ev diziyorum", "yeni ev"]):
        return "ev_kurma"

    if "beyaz esya" in q:
        return "beyaz_esya"

    return "genel_paket"


def detect_product_group(row):
    text = row_text(row)

    if "buzdolabi" in text or "no frost" in text or "minibar" in text or "sogutucu" in text:
        return "buzdolabi"

    if "camasir" in text and "bulasik" not in text:
        return "camasir_makinesi"

    if "bulasik" in text:
        return "bulasik_makinesi"

    if "televizyon" in text or "smart tv" in text or re.search(r"\btv\b", text):
        return "televizyon"

    if "supurge" in text or "temizlik" in text:
        return "supurge"

    if "firin" in text or "ankastre" in text or "ocak" in text:
        return "firin"

    if "klima" in text:
        return "klima"

    if "laptop" in text or "bilgisayar" in text or "notebook" in text:
        return "laptop"

    if "telefon" in text or "iphone" in text or "galaxy" in text:
        return "telefon"

    return "diger"


PACKAGE_PRIORITIES = {
    "ceyiz": [
        {"group": "buzdolabi", "label": "Buzdolabı", "priority": 1, "budget_ratio": 0.28},
        {"group": "camasir_makinesi", "label": "Çamaşır Makinesi", "priority": 2, "budget_ratio": 0.22},
        {"group": "bulasik_makinesi", "label": "Bulaşık Makinesi", "priority": 3, "budget_ratio": 0.18},
        {"group": "televizyon", "label": "Televizyon", "priority": 4, "budget_ratio": 0.20},
        {"group": "supurge", "label": "Süpürge", "priority": 5, "budget_ratio": 0.08},
        {"group": "firin", "label": "Fırın / Ankastre", "priority": 6, "budget_ratio": 0.12},
    ],
    "ev_kurma": [
        {"group": "buzdolabi", "label": "Buzdolabı", "priority": 1, "budget_ratio": 0.26},
        {"group": "camasir_makinesi", "label": "Çamaşır Makinesi", "priority": 2, "budget_ratio": 0.20},
        {"group": "bulasik_makinesi", "label": "Bulaşık Makinesi", "priority": 3, "budget_ratio": 0.17},
        {"group": "televizyon", "label": "Televizyon", "priority": 4, "budget_ratio": 0.18},
        {"group": "supurge", "label": "Süpürge", "priority": 5, "budget_ratio": 0.07},
        {"group": "firin", "label": "Fırın / Ankastre", "priority": 6, "budget_ratio": 0.12},
    ],
    "beyaz_esya": [
        {"group": "buzdolabi", "label": "Buzdolabı", "priority": 1, "budget_ratio": 0.34},
        {"group": "camasir_makinesi", "label": "Çamaşır Makinesi", "priority": 2, "budget_ratio": 0.28},
        {"group": "bulasik_makinesi", "label": "Bulaşık Makinesi", "priority": 3, "budget_ratio": 0.22},
        {"group": "firin", "label": "Fırın / Ankastre", "priority": 4, "budget_ratio": 0.16},
    ],
    "genel_paket": [
        {"group": "buzdolabi", "label": "Buzdolabı", "priority": 1, "budget_ratio": 0.28},
        {"group": "camasir_makinesi", "label": "Çamaşır Makinesi", "priority": 2, "budget_ratio": 0.22},
        {"group": "televizyon", "label": "Televizyon", "priority": 3, "budget_ratio": 0.20},
        {"group": "supurge", "label": "Süpürge", "priority": 4, "budget_ratio": 0.08},
    ],
}


def score_package_product(row, target_group, target_budget=None, query_info=None):
    query_info = query_info or {}

    text = row_text(row)
    group = detect_product_group(row)

    score = 0

    if group == target_group:
        score += 100
    else:
        score -= 100

    if normalize_text(row.get("stock_status", "")) == "stokta":
        score += 12

    price = safe_number(row.get("price", 0))

    if target_budget and price:
        if price <= target_budget:
            score += 25
        elif price <= target_budget * 1.15:
            score += 8
        elif price <= target_budget * 1.30:
            score -= 8
        else:
            score -= 28

    q = normalize_text(query_info.get("raw_query", "") or query_info.get("normalized_query", ""))

    if "senet" in q or query_info.get("payment_priority") == "lowest_monthly":
        if safe_number(row.get("senet_total_price", 0)) > 0:
            score += 10
        if safe_number(row.get("senet_monthly_9", 0)) > 0:
            score += 8

    if "havale" in q or query_info.get("payment_priority") == "lowest_total":
        if safe_number(row.get("bank_transfer_price", 0)) > 0:
            score += 10

    if "ceyiz" in text:
        score += 5

    return score


def choose_best_product_for_group(products_df, group_info, total_budget, query_info):
    target_group = group_info["group"]
    target_budget = total_budget * group_info.get("budget_ratio", 0) if total_budget else None

    df = products_df.copy()
    df["package_group_detected"] = df.apply(detect_product_group, axis=1)

    candidates = df[df["package_group_detected"] == target_group].copy()

    if candidates.empty:
        return None

    candidates["package_score"] = candidates.apply(
        lambda row: score_package_product(row, target_group, target_budget, query_info),
        axis=1,
    )

    candidates = candidates.sort_values("package_score", ascending=False)

    return candidates.iloc[0]


def make_package_decision(products_df, query_info):
    if products_df is None or products_df.empty:
        return {
            "result_df": pd.DataFrame(),
            "query_info": query_info,
            "decision": "Paket için ürün verisi bulunamadı.",
            "fallback_answer": "Paket için ürün verisi bulunamadı.",
            "package_summary": {},
        }

    package_type = detect_package_type(query_info)
    priority_list = PACKAGE_PRIORITIES.get(package_type, PACKAGE_PRIORITIES["genel_paket"])

    total_budget = safe_number(query_info.get("budget", 0))
    selected_rows = []
    missing_groups = []

    current_total = 0

    for group_info in sorted(priority_list, key=lambda item: item["priority"]):
        best = choose_best_product_for_group(products_df, group_info, total_budget, query_info)

        if best is None:
            missing_groups.append(group_info["label"])
            continue

        selected_rows.append(best)
        current_total += safe_number(best.get("price", 0))

    if selected_rows:
        result_df = pd.DataFrame(selected_rows).copy()
    else:
        result_df = pd.DataFrame()

    if not result_df.empty:
        result_df["package_group"] = result_df.apply(
            lambda row: PACKAGE_GROUP_LABELS.get(detect_product_group(row), detect_product_group(row)),
            axis=1,
        )

        result_df["score"] = result_df.get("package_score", 80)

    remaining_budget = total_budget - current_total if total_budget else None

    if total_budget:
        if current_total <= total_budget:
            budget_status = "Bütçe içinde kaldı."
        elif current_total <= total_budget * 1.10:
            budget_status = "Bütçeyi az miktarda aşıyor."
        else:
            budget_status = "Bütçeyi belirgin şekilde aşıyor."
    else:
        budget_status = "Bütçe belirtilmedi."

    package_summary = {
        "package_type": package_type,
        "requested_budget": total_budget,
        "selected_total": current_total,
        "remaining_budget": remaining_budget,
        "budget_status": budget_status,
        "missing_groups": missing_groups,
        "selected_count": len(selected_rows),
    }

    decision_parts = [
        f"Paket tipi: {package_type}.",
        f"Seçilen ürün sayısı: {len(selected_rows)}.",
        f"Paket toplamı: {money(current_total)}.",
        budget_status,
    ]

    if total_budget:
        decision_parts.append(f"Talep edilen bütçe: {money(total_budget)}.")

    if missing_groups:
        decision_parts.append("Eksik kategoriler: " + ", ".join(missing_groups) + ".")

    return {
        "result_df": result_df,
        "query_info": query_info,
        "decision": " ".join(decision_parts),
        "fallback_answer": "Paket talebinize göre farklı kategorilerden ürün kombinasyonu hazırlandı.",
        "package_summary": package_summary,
    }


PACKAGE_GROUP_LABELS = {
    "buzdolabi": "Buzdolabı",
    "camasir_makinesi": "Çamaşır Makinesi",
    "bulasik_makinesi": "Bulaşık Makinesi",
    "televizyon": "Televizyon",
    "supurge": "Süpürge",
    "firin": "Fırın / Ankastre",
    "klima": "Klima",
    "laptop": "Laptop",
    "telefon": "Telefon",
    "diger": "Diğer",
}


def generate_package_text(decision_result):
    df = decision_result.get("result_df", pd.DataFrame())
    summary = decision_result.get("package_summary", {})

    if df is None or df.empty:
        return "Paket oluşturmak için uygun ürün bulunamadı."

    lines = []

    lines.append("Paket önerisi hazırlandı.")
    lines.append("")

    for _, row in df.iterrows():
        group = row.get("package_group", PACKAGE_GROUP_LABELS.get(detect_product_group(row), "Ürün"))

        lines.append(
            f"- {group}: {row.get('product_name')} | {money(row.get('price', 0))} | Stok: {row.get('stock_status')}"
        )

    lines.append("")
    lines.append(f"Paket toplamı: {money(summary.get('selected_total', 0))}")

    if summary.get("requested_budget"):
        lines.append(f"Talep edilen bütçe: {money(summary.get('requested_budget'))}")
        lines.append(f"Bütçe durumu: {summary.get('budget_status')}")

    if summary.get("missing_groups"):
        lines.append("Eksik kalan kategoriler: " + ", ".join(summary.get("missing_groups")))

    return "\n".join(lines)


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    test_products = pd.DataFrame(
        [
            {
                "product_name": "Beko No Frost Buzdolabı 500 L",
                "category": "Beyaz Eşya",
                "brand": "Beko",
                "price": 18500,
                "stock_status": "Stokta",
                "description": "No Frost buzdolabı",
                "features": "Geniş hacim",
                "use_case": "Çeyiz",
                "payment_options": "Senet, havale",
                "senet_total_price": 21900,
                "senet_monthly_9": 2433,
                "bank_transfer_price": 17650,
            },
            {
                "product_name": "Vestel 7 kg Çamaşır Makinesi",
                "category": "Beyaz Eşya",
                "brand": "Vestel",
                "price": 15120,
                "stock_status": "Stokta",
                "description": "Çamaşır makinesi",
                "features": "7 kg",
                "use_case": "Çeyiz",
                "payment_options": "Senet, havale",
                "senet_total_price": 17779,
                "senet_monthly_9": 1975,
                "bank_transfer_price": 14560,
            },
            {
                "product_name": "Samsung 50 inç Smart TV",
                "category": "Televizyon",
                "brand": "Samsung",
                "price": 12900,
                "stock_status": "Stokta",
                "description": "Smart TV",
                "features": "4K",
                "use_case": "Salon, çeyiz",
                "payment_options": "Senet, havale",
                "senet_total_price": 15900,
                "senet_monthly_9": 1766,
                "bank_transfer_price": 12490,
            },
            {
                "product_name": "Philips Elektrikli Süpürge",
                "category": "Küçük Ev Aleti",
                "brand": "Philips",
                "price": 3999,
                "stock_status": "Stokta",
                "description": "Süpürge",
                "features": "Güçlü emiş",
                "use_case": "Çeyiz",
                "payment_options": "Senet, havale",
                "senet_total_price": 4999,
                "senet_monthly_9": 555,
                "bank_transfer_price": 3799,
            },
        ]
    )

    query_info = {
        "raw_query": "100 bin TL çeyiz paketi yap senetli olsun",
        "normalized_query": "100 bin tl ceyiz paketi yap senetli olsun",
        "budget": 100000,
        "payment_priority": "lowest_monthly",
    }

    result = make_package_decision(test_products, query_info)

    print(result["decision"])
    print(generate_package_text(result))