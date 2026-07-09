import os
import json
import re
from datetime import datetime

import pandas as pd


# =====================================================
# MEMORY ENGINE
# Amaç:
# Kullanıcı davranışı, tercihleri, son aramalar ve ödeme eğilimlerini
# lokal dosyada saklamak.
# =====================================================

MEMORY_DIR = "data"
MEMORY_FILE = os.path.join(MEMORY_DIR, "user_memory.json")
BEHAVIOR_FILE = os.path.join(MEMORY_DIR, "user_behavior.csv")


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


def ensure_memory_files():
    os.makedirs(MEMORY_DIR, exist_ok=True)

    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=2)

    if not os.path.exists(BEHAVIOR_FILE):
        df = pd.DataFrame(
            columns=[
                "timestamp",
                "user_id",
                "role",
                "query",
                "primary_intent",
                "product_types",
                "brands",
                "budget",
                "payment_priority",
                "result_count",
                "top_product",
                "guardrail_category",
                "strict_filter_active",
                "semantic_active",
                "package_type",
            ]
        )
        df.to_csv(BEHAVIOR_FILE, index=False)


def load_memory():
    ensure_memory_files()

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_memory(memory):
    ensure_memory_files()

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


def get_user_memory(user_id):
    memory = load_memory()

    if user_id not in memory:
        memory[user_id] = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query_count": 0,
            "last_queries": [],
            "preferred_product_types": {},
            "preferred_brands": {},
            "preferred_payment": {},
            "last_budget": None,
            "last_product_type": None,
            "last_brand": None,
            "last_intent": None,
            "last_use_cases": [],
        }
        save_memory(memory)

    return memory[user_id]


def update_counter(counter_dict, values):
    if not isinstance(values, list):
        values = [values]

    for value in values:
        if value in [None, "", [], {}]:
            continue

        value = str(value)

        counter_dict[value] = int(counter_dict.get(value, 0)) + 1

    return counter_dict


def top_key(counter_dict):
    if not counter_dict:
        return None

    return max(counter_dict.items(), key=lambda item: item[1])[0]


def update_user_memory(user_id, query_info, result_df=None):
    memory = load_memory()

    user_mem = memory.get(user_id) or get_user_memory(user_id)

    user_mem["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_mem["query_count"] = int(user_mem.get("query_count", 0)) + 1

    raw_query = query_info.get("raw_query") or query_info.get("original_query") or ""

    last_queries = user_mem.get("last_queries", [])
    last_queries.append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": raw_query,
        }
    )
    user_mem["last_queries"] = last_queries[-10:]

    product_types = query_info.get("product_types", []) or []
    brands = query_info.get("brands", []) or []
    payment_priority = query_info.get("payment_priority")
    budget = query_info.get("budget")
    use_cases = query_info.get("use_cases", []) or []

    user_mem["preferred_product_types"] = update_counter(
        user_mem.get("preferred_product_types", {}),
        product_types,
    )

    user_mem["preferred_brands"] = update_counter(
        user_mem.get("preferred_brands", {}),
        brands,
    )

    user_mem["preferred_payment"] = update_counter(
        user_mem.get("preferred_payment", {}),
        payment_priority,
    )

    if budget:
        user_mem["last_budget"] = budget

    if product_types:
        user_mem["last_product_type"] = product_types[-1]

    if brands:
        user_mem["last_brand"] = brands[-1]

    if query_info.get("primary_intent"):
        user_mem["last_intent"] = query_info.get("primary_intent")

    if use_cases:
        user_mem["last_use_cases"] = use_cases

    user_mem["top_product_type"] = top_key(user_mem.get("preferred_product_types", {}))
    user_mem["top_brand"] = top_key(user_mem.get("preferred_brands", {}))
    user_mem["top_payment"] = top_key(user_mem.get("preferred_payment", {}))

    memory[user_id] = user_mem
    save_memory(memory)

    return user_mem


def apply_memory_to_query(user_id, query_info):
    """
    Kısa takip sorularında önceki bağlamı tamamlar.
    Örn:
    Önce: Öğrenci için laptop var mı?
    Sonra: Daha ucuzu var mı?
    -> product_types laptop olarak kalır.
    """

    user_mem = get_user_memory(user_id)
    q = normalize_text(query_info.get("raw_query", "") or query_info.get("normalized_query", ""))

    followup_words = [
        "daha ucuz",
        "daha uygunu",
        "baska",
        "alternatif",
        "benzeri",
        "daha iyisi",
        "taksitli",
        "senetli",
        "havale",
        "stokta",
        "var mi",
        "goster",
    ]

    is_followup = any(word in q for word in followup_words)

    if not is_followup:
        return query_info, {
            "active": False,
            "reason": "Takip sorusu algılanmadı.",
            "used_fields": [],
        }

    used_fields = []

    if query_info.get("product_types") in [None, "", [], {}] and user_mem.get("last_product_type"):
        query_info["product_types"] = [user_mem.get("last_product_type")]
        used_fields.append("last_product_type")

    if query_info.get("brands") in [None, "", [], {}] and user_mem.get("last_brand"):
        query_info["brands"] = [user_mem.get("last_brand")]
        used_fields.append("last_brand")

    if query_info.get("budget") in [None, "", 0] and user_mem.get("last_budget"):
        query_info["budget"] = user_mem.get("last_budget")
        used_fields.append("last_budget")

    if query_info.get("payment_priority") in [None, "", [], {}] and user_mem.get("top_payment"):
        query_info["payment_priority"] = user_mem.get("top_payment")
        used_fields.append("top_payment")

    if query_info.get("use_cases") in [None, "", [], {}] and user_mem.get("last_use_cases"):
        query_info["use_cases"] = user_mem.get("last_use_cases")
        used_fields.append("last_use_cases")

    return query_info, {
        "active": bool(used_fields),
        "reason": "Takip sorusu için kullanıcı hafızası uygulandı." if used_fields else "Takip sorusu algılandı ama kullanılacak hafıza bulunamadı.",
        "used_fields": used_fields,
    }


def log_user_behavior(
    user_id,
    role,
    query,
    query_info,
    result_df=None,
    guardrail_info=None,
    filter_info=None,
    semantic_info=None,
    package_summary=None,
):
    ensure_memory_files()

    result_count = 0
    top_product = ""

    if result_df is not None and hasattr(result_df, "empty") and not result_df.empty:
        result_count = len(result_df)
        top_product = str(result_df.iloc[0].get("product_name", ""))

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "role": role,
        "query": query,
        "primary_intent": query_info.get("primary_intent", ""),
        "product_types": ",".join(query_info.get("product_types", []) or []),
        "brands": ",".join(query_info.get("brands", []) or []),
        "budget": query_info.get("budget", ""),
        "payment_priority": query_info.get("payment_priority", ""),
        "result_count": result_count,
        "top_product": top_product,
        "guardrail_category": (guardrail_info or {}).get("category", ""),
        "strict_filter_active": (filter_info or {}).get("active", ""),
        "semantic_active": (semantic_info or {}).get("active", ""),
        "package_type": (package_summary or {}).get("package_type", ""),
    }

    try:
        df = pd.read_csv(BEHAVIOR_FILE)
    except Exception:
        df = pd.DataFrame()

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(BEHAVIOR_FILE, index=False)

    return row


def load_behavior_log(limit=100):
    ensure_memory_files()

    try:
        df = pd.read_csv(BEHAVIOR_FILE)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    return df.tail(limit).sort_values("timestamp", ascending=False)


def memory_summary_text(user_id):
    user_mem = get_user_memory(user_id)

    parts = []

    if user_mem.get("top_product_type"):
        parts.append(f"En çok ilgilendiği ürün tipi: {user_mem.get('top_product_type')}")

    if user_mem.get("top_brand"):
        parts.append(f"Öne çıkan marka ilgisi: {user_mem.get('top_brand')}")

    if user_mem.get("top_payment"):
        parts.append(f"Tercih edilen ödeme tipi: {user_mem.get('top_payment')}")

    if user_mem.get("last_budget"):
        parts.append(f"Son bilinen bütçe: {user_mem.get('last_budget')} TL")

    if not parts:
        return "Bu kullanıcı için henüz anlamlı davranış verisi oluşmadı."

    return " | ".join(parts)


if __name__ == "__main__":
    test_query = {
        "raw_query": "Öğrenci için laptop var mı?",
        "primary_intent": "general_question",
        "product_types": ["laptop"],
        "brands": [],
        "budget": 25000,
        "payment_priority": "lowest_monthly",
        "use_cases": ["ogrenci"],
    }

    user_id = "demo@nevade.com"

    update_user_memory(user_id, test_query)

    followup = {
        "raw_query": "Daha ucuzu var mı?",
        "primary_intent": "general_question",
        "product_types": [],
        "brands": [],
        "budget": None,
        "payment_priority": None,
        "use_cases": [],
    }

    updated, info = apply_memory_to_query(user_id, followup)

    print("MEMORY:", get_user_memory(user_id))
    print("UPDATED QUERY:", updated)
    print("MEMORY INFO:", info)