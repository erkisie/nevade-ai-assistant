import pandas as pd

from src.nlp_engine import normalize_text
from src.decision_engine import safe_number, money


PACKAGE_WORDS = [
    "paket",
    "paketi",
    "set",
    "seti",
    "kombin",
    "kombin yap",
    "ceyiz",
    "çeyiz",
    "ceyiz paketi",
    "çeyiz paketi",
    "alisveris listesi",
    "alışveriş listesi",
]


PACKAGE_TARGETS = [
    {
        "group": "Buzdolabı",
        "required": True,
        "words": [
            "buzdolabi",
            "buz dolabi",
            "buzdolabı",
            "buz dolabı",
            "no frost",
            "sogutucu",
        ],
    },
    {
        "group": "Çamaşır Makinesi",
        "required": True,
        "words": [
            "camasir",
            "çamaşır",
            "camasir makinesi",
            "çamaşır makinesi",
            "yikama",
        ],
    },
    {
        "group": "Fırın",
        "required": False,
        "words": [
            "firin",
            "fırın",
            "ankastre",
            "mini firin",
            "mini fırın",
            "elektrikli firin",
            "elektrikli fırın",
        ],
    },
    {
        "group": "Televizyon",
        "required": False,
        "words": [
            "televizyon",
            "tv",
            "smart tv",
            "4k",
            "ekran",
        ],
    },
    {
        "group": "Küçük Ev Aleti",
        "required": False,
        "words": [
            "supurge",
            "süpürge",
            "blender",
            "cay",
            "çay",
            "tost",
            "airfryer",
            "robot",
            "mutfak",
            "kucuk ev aleti",
            "küçük ev aleti",
        ],
    },
]


def is_package_request(query_info):
    q = query_info.get("normalized_query", "")
    original = str(query_info.get("original_query", "")).lower()

    combined = normalize_text(q + " " + original)

    return any(normalize_text(word) in combined for word in PACKAGE_WORDS)


def get_product_text(row):
    fields = [
        "product_name",
        "category",
        "brand",
        "description",
        "features",
        "use_case",
        "payment_options",
        "capacity",
        "energy_class",
        "screen_size",
        "product_type",
    ]

    parts = []

    for field in fields:
        if field in row:
            parts.append(str(row.get(field, "")))

    return normalize_text(" ".join(parts))


def effective_price(row):
    prices = [
        safe_number(row.get("bank_transfer_price", 0)),
        safe_number(row.get("cash_price", 0)),
        safe_number(row.get("price", 0)),
    ]

    prices = [p for p in prices if p > 0]

    if not prices:
        return 0

    return min(prices)


def package_match_score(row, words):
    text = get_product_text(row)

    score = 0

    for word in words:
        if normalize_text(word) in text:
            score += 30

    if normalize_text(row.get("stock_status", "")) == "stokta":
        score += 8

    if safe_number(row.get("bank_transfer_price", 0)) > 0:
        score += 4

    if safe_number(row.get("installment_6_total", 0)) > 0:
        score += 4

    if safe_number(row.get("senet_total_price", 0)) > 0:
        score += 4

    price = effective_price(row)

    if price > 0:
        score += max(0, 15 - int(price / 5000))

    return score


def select_best_item(products_df, target, used_ids, remaining_budget=None):
    if products_df is None or products_df.empty:
        return None

    candidates = products_df.copy()

    if used_ids:
        candidates = candidates[
            ~candidates["product_id"].astype(str).isin([str(x) for x in used_ids])
        ]

    if candidates.empty:
        return None

    candidates = candidates.copy()
    candidates["package_price"] = candidates.apply(effective_price, axis=1)
    candidates["package_match_score"] = candidates.apply(
        lambda row: package_match_score(row, target["words"]),
        axis=1,
    )

    candidates = candidates[candidates["package_match_score"] > 0]

    if remaining_budget is not None and remaining_budget > 0:
        budget_candidates = candidates[candidates["package_price"] <= remaining_budget]

        if not budget_candidates.empty:
            candidates = budget_candidates

    if candidates.empty:
        return None

    candidates = candidates.sort_values(
        ["package_match_score", "package_price"],
        ascending=[False, True],
    )

    return candidates.iloc[0]


def build_smart_package(products_df, query_info):
    budget = query_info.get("budget")
    budget_value = safe_number(budget) if budget else None

    selected_rows = []
    used_ids = []
    total_price = 0

    for target in PACKAGE_TARGETS:
        remaining_budget = None

        if budget_value:
            remaining_budget = max(budget_value - total_price, 0)

        row = select_best_item(
            products_df=products_df,
            target=target,
            used_ids=used_ids,
            remaining_budget=remaining_budget,
        )

        if row is not None:
            row = row.copy()
            row["package_group"] = target["group"]
            row["package_price"] = effective_price(row)
            row["package_required"] = target["required"]

            selected_rows.append(row)
            used_ids.append(str(row.get("product_id", "")))
            total_price += effective_price(row)

    if not selected_rows:
        return pd.DataFrame(), 0

    package_df = pd.DataFrame(selected_rows)

    return package_df, total_price


def create_package_fallback_answer(query_info, package_df, total_price):
    budget = query_info.get("budget")
    budget_value = safe_number(budget) if budget else None

    if package_df.empty:
        return (
            "Çeyiz paketi oluşturmak istedim ancak ürün listesinde paket kurmaya yetecek uygun ürün bulamadım. "
            "Buzdolabı, çamaşır makinesi, fırın, televizyon ve küçük ev aleti ürünleri eklendiğinde daha doğru paket hazırlanabilir."
        )

    lines = []

    for _, row in package_df.iterrows():
        group = row.get("package_group", "Ürün")
        name = row.get("product_name", "")
        price = money(row.get("package_price", row.get("price", 0)))
        stock = row.get("stock_status", "")

        lines.append(f"- {group}: {name} — yaklaşık {price} ({stock})")

    total_text = f"Paket toplamı yaklaşık {money(total_price)}."

    if budget_value:
        diff = budget_value - total_price

        if diff >= 0:
            budget_text = (
                f"Belirttiğiniz {money(budget_value)} bütçenin içinde kalıyor. "
                f"Yaklaşık {money(diff)} bütçe payı kalıyor."
            )
        else:
            budget_text = (
                f"Belirttiğiniz {money(budget_value)} bütçeyi yaklaşık {money(abs(diff))} aşıyor. "
                "Daha ekonomik alternatiflerle yeniden paket oluşturulabilir."
            )
    else:
        budget_text = "Bütçe belirtirseniz paketi daha net optimize edebilirim."

    return (
        "Çeyiz paketi için tek ürün yerine temel ihtiyaçları kapsayan bir kombin hazırladım:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + total_text
        + " "
        + budget_text
    )


def make_package_decision(products_df, query_info):
    package_df, total_price = build_smart_package(products_df, query_info)

    if package_df.empty:
        decision = "NO_PACKAGE_MATCH"
    else:
        decision = "PACKAGE_RECOMMENDATION"

    fallback_answer = create_package_fallback_answer(
        query_info=query_info,
        package_df=package_df,
        total_price=total_price,
    )

    if not package_df.empty:
        package_df = package_df.copy()
        package_df["rule_score"] = 100
        package_df["similarity_score"] = 100
        package_df["score"] = 98

    enriched_query_info = query_info.copy()
    enriched_query_info["package_total_price"] = total_price
    enriched_query_info["is_package"] = True

    return {
        "decision": decision,
        "query_info": enriched_query_info,
        "result_df": package_df,
        "fallback_answer": fallback_answer,
    }