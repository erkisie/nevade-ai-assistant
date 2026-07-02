import pandas as pd

from src.customer_intelligence_engine import safe_number, money, normalize_text


# =====================================================
# BUDGET OPTIMIZATION ENGINE
# Bütçe aşımı olduğunda paketi/sepeti optimize eder
# =====================================================


OPTIONAL_PACKAGE_GROUPS = [
    "Küçük Ev Aleti",
    "Televizyon",
    "Fırın",
]


REQUIRED_PACKAGE_GROUPS = [
    "Buzdolabı",
    "Çamaşır Makinesi",
]


def get_price(row):
    """
    Paket/sepet için en mantıklı fiyatı bulur.
    Öncelik: package_price > bank_transfer_price > cash_price > price
    """

    for col in ["package_price", "bank_transfer_price", "cash_price", "price"]:
        value = safe_number(row.get(col, 0))

        if value > 0:
            return value

    return 0


def calculate_total(df):
    if df is None or df.empty:
        return 0

    return sum(get_price(row) for _, row in df.iterrows())


def has_package_group(df):
    return df is not None and not df.empty and "package_group" in df.columns


def find_cheaper_same_group(products_df, current_row, used_ids=None, budget_limit=None):
    """
    Paketteki ürün yerine aynı package_group için daha ucuz alternatif arar.
    """

    if products_df is None or products_df.empty:
        return None

    used_ids = used_ids or []

    group = current_row.get("package_group", "")
    current_price = get_price(current_row)

    if not group or current_price <= 0:
        return None

    candidates = products_df.copy()

    if "product_id" in candidates.columns:
        candidates = candidates[
            ~candidates["product_id"].astype(str).isin([str(x) for x in used_ids])
        ]

    # Grup kelimesini ürün adı/açıklama/kategori içinde ara
    group_norm = normalize_text(group)

    text_cols = [
        "product_name",
        "category",
        "description",
        "features",
        "use_case",
        "capacity",
    ]

    def match_group(row):
        text = " ".join(str(row.get(col, "")) for col in text_cols)
        text = normalize_text(text)

        if group_norm == "buzdolabi":
            return "buzdolabi" in text or "buz dolabi" in text

        if group_norm == "camasir makinesi":
            return "camasir" in text

        if group_norm == "firin":
            return "firin" in text

        if group_norm == "televizyon":
            return "televizyon" in text or "tv" in text

        if group_norm == "kucuk ev aleti":
            return (
                "supurge" in text
                or "blender" in text
                or "cay" in text
                or "tost" in text
                or "airfryer" in text
                or normalize_text(row.get("category", "")) == "kucuk ev aleti"
            )

        return group_norm in text

    candidates = candidates[candidates.apply(match_group, axis=1)]

    if candidates.empty:
        return None

    candidates = candidates.copy()
    candidates["optimizer_price"] = candidates.apply(get_price, axis=1)

    candidates = candidates[
        (candidates["optimizer_price"] > 0)
        & (candidates["optimizer_price"] < current_price)
    ]

    if budget_limit:
        candidates = candidates[candidates["optimizer_price"] <= safe_number(budget_limit)]

    if candidates.empty:
        return None

    if "stock_status" in candidates.columns:
        candidates["stock_priority"] = candidates["stock_status"].apply(
            lambda x: 1 if normalize_text(x) == "stokta" else 0
        )
    else:
        candidates["stock_priority"] = 0

    candidates = candidates.sort_values(
        ["stock_priority", "optimizer_price"],
        ascending=[False, True],
    )

    new_row = candidates.iloc[0].copy()
    new_row["package_group"] = group
    new_row["package_price"] = get_price(new_row)
    new_row["optimization_note"] = f"{group} için daha ekonomik alternatif seçildi."

    return new_row


def try_replace_with_cheaper_alternatives(products_df, package_df, budget):
    """
    Paketteki pahalı ürünleri daha ucuz alternatiflerle değiştirmeyi dener.
    """

    if package_df is None or package_df.empty:
        return package_df, []

    optimized_rows = []
    notes = []

    used_ids = []

    if "product_id" in package_df.columns:
        used_ids = package_df["product_id"].astype(str).tolist()

    # Pahalı ürünlerden başlayarak değiştir
    working_df = package_df.copy()
    working_df["optimizer_price"] = working_df.apply(get_price, axis=1)
    working_df = working_df.sort_values("optimizer_price", ascending=False)

    for _, row in working_df.iterrows():
        current_total = calculate_total(pd.DataFrame(optimized_rows + [row]))

        cheaper = find_cheaper_same_group(
            products_df=products_df,
            current_row=row,
            used_ids=used_ids,
        )

        if cheaper is not None:
            old_price = get_price(row)
            new_price = get_price(cheaper)

            if new_price < old_price:
                optimized_rows.append(cheaper)
                used_ids.append(str(cheaper.get("product_id", "")))
                notes.append(
                    f"{row.get('package_group', 'Ürün')}: {row.get('product_name', '')} yerine "
                    f"{cheaper.get('product_name', '')} seçildi. Tasarruf: {money(old_price - new_price)}"
                )
            else:
                optimized_rows.append(row)
        else:
            optimized_rows.append(row)

    if not optimized_rows:
        return package_df, notes

    optimized_df = pd.DataFrame(optimized_rows)

    # Orijinal package_group sırasını kabaca koru
    group_order = {
        "Buzdolabı": 1,
        "Çamaşır Makinesi": 2,
        "Fırın": 3,
        "Televizyon": 4,
        "Küçük Ev Aleti": 5,
    }

    optimized_df["group_order"] = optimized_df["package_group"].map(group_order).fillna(99)
    optimized_df = optimized_df.sort_values("group_order").drop(columns=["group_order"])

    return optimized_df, notes


def remove_optional_items_until_budget(package_df, budget):
    """
    Hala bütçe aşılıyorsa opsiyonel ürünleri çıkarır.
    Önce küçük ev aleti, sonra TV, sonra fırın denenir.
    """

    if package_df is None or package_df.empty:
        return package_df, []

    working_df = package_df.copy()
    notes = []
    budget_value = safe_number(budget)

    for optional_group in OPTIONAL_PACKAGE_GROUPS:
        total = calculate_total(working_df)

        if total <= budget_value:
            break

        if "package_group" not in working_df.columns:
            break

        group_rows = working_df[
            working_df["package_group"].astype(str) == optional_group
        ]

        if group_rows.empty:
            continue

        removed_price = calculate_total(group_rows)

        working_df = working_df[
            working_df["package_group"].astype(str) != optional_group
        ].copy()

        notes.append(
            f"Bütçeye yaklaşmak için opsiyonel {optional_group} paketten çıkarıldı. "
            f"Yaklaşık tasarruf: {money(removed_price)}"
        )

    return working_df, notes


def create_budget_optimization_answer(original_df, optimized_df, budget, notes):
    original_total = calculate_total(original_df)
    optimized_total = calculate_total(optimized_df)
    budget_value = safe_number(budget)

    if optimized_df is None or optimized_df.empty:
        return (
            f"Paket toplamı {money(original_total)} olduğu için {money(budget_value)} bütçeyi aşıyor. "
            "Uygun alternatif oluşturmak için ürün listesinin daha fazla ekonomik ürünle genişletilmesi gerekir."
        )

    lines = []

    for _, row in optimized_df.iterrows():
        group = row.get("package_group", "Ürün")
        name = row.get("product_name", "")
        price = money(get_price(row))
        stock = row.get("stock_status", "")

        lines.append(f"- {group}: {name} — yaklaşık {price} ({stock})")

    if optimized_total <= budget_value:
        status_text = (
            f"Optimize edilen paket toplamı yaklaşık {money(optimized_total)}. "
            f"Bu paket {money(budget_value)} bütçenin içinde kalıyor."
        )
    else:
        diff = optimized_total - budget_value
        status_text = (
            f"Optimize edilen paket toplamı yaklaşık {money(optimized_total)}. "
            f"Hâlâ bütçeyi yaklaşık {money(diff)} aşıyor; daha ekonomik ürün verisi eklenirse tam bütçe içine çekilebilir."
        )

    note_text = ""

    if notes:
        note_text = "\n\nYapılan optimizasyonlar:\n" + "\n".join(f"- {note}" for note in notes)

    return (
        "Bütçenizi aşmamak için paketi yeniden optimize ettim:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + status_text
        + note_text
        + "\n\n"
        + "İsterseniz paketi 'en ekonomik', 'en dengeli' veya 'en iyi ödeme seçeneği' modunda yeniden düzenleyebilirim."
    )


def run_budget_optimization(products_df, package_df, budget):
    """
    Ana bütçe optimizasyon akışı.
    """

    if budget is None or safe_number(budget) <= 0:
        return {
            "decision": "NO_BUDGET_TO_OPTIMIZE",
            "result_df": package_df,
            "answer": "Bütçe belirtilmediği için optimizasyon yapılamadı.",
            "optimized_total": calculate_total(package_df),
            "notes": [],
        }

    original_total = calculate_total(package_df)
    budget_value = safe_number(budget)

    if original_total <= budget_value:
        return {
            "decision": "BUDGET_OK",
            "result_df": package_df,
            "answer": (
                f"Paket toplamı yaklaşık {money(original_total)}. "
                f"Belirttiğiniz {money(budget_value)} bütçenin içinde kalıyor."
            ),
            "optimized_total": original_total,
            "notes": [],
        }

    optimized_df, replace_notes = try_replace_with_cheaper_alternatives(
        products_df=products_df,
        package_df=package_df,
        budget=budget_value,
    )

    optimized_total = calculate_total(optimized_df)

    remove_notes = []

    if optimized_total > budget_value:
        optimized_df, remove_notes = remove_optional_items_until_budget(
            package_df=optimized_df,
            budget=budget_value,
        )

    notes = replace_notes + remove_notes

    final_total = calculate_total(optimized_df)

    answer = create_budget_optimization_answer(
        original_df=package_df,
        optimized_df=optimized_df,
        budget=budget_value,
        notes=notes,
    )

    decision = "BUDGET_OPTIMIZED"

    if final_total > budget_value:
        decision = "BUDGET_PARTIALLY_OPTIMIZED"

    return {
        "decision": decision,
        "result_df": optimized_df,
        "answer": answer,
        "original_total": original_total,
        "optimized_total": final_total,
        "budget": budget_value,
        "notes": notes,
    }