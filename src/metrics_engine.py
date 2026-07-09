import os
import pandas as pd
from datetime import datetime


# =====================================================
# METRICS ENGINE
# Amaç:
# Memory engine tarafından tutulan user_behavior.csv dosyasından
# AI kullanım metrikleri üretmek.
# =====================================================

BEHAVIOR_FILE = os.path.join("data", "user_behavior.csv")


def safe_read_behavior_log():
    if not os.path.exists(BEHAVIOR_FILE):
        return pd.DataFrame()

    try:
        df = pd.read_csv(BEHAVIOR_FILE)

        if df.empty:
            return pd.DataFrame()

        return df

    except Exception as e:
        print("Behavior log okunamadı:", e)
        return pd.DataFrame()


def safe_count(df):
    if df is None or df.empty:
        return 0

    return len(df)


def split_and_count(series):
    counter = {}

    if series is None:
        return counter

    for value in series.dropna().astype(str):
        if not value.strip():
            continue

        parts = [x.strip() for x in value.split(",") if x.strip()]

        for part in parts:
            counter[part] = counter.get(part, 0) + 1

    return counter


def top_items(counter, limit=10):
    if not counter:
        return []

    return sorted(counter.items(), key=lambda item: item[1], reverse=True)[:limit]


def value_counts_as_list(df, column, limit=10):
    if df is None or df.empty or column not in df.columns:
        return []

    counts = (
        df[column]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(limit)
    )

    return list(counts.items())


def calculate_ai_metrics():
    df = safe_read_behavior_log()

    if df.empty:
        return {
            "total_queries": 0,
            "customer_queries": 0,
            "store_queries": 0,
            "guardrail_events": 0,
            "strict_filter_events": 0,
            "semantic_events": 0,
            "package_events": 0,
            "top_product_types": [],
            "top_brands": [],
            "top_payments": [],
            "top_products": [],
            "top_guardrail_categories": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    total_queries = len(df)

    customer_queries = len(df[df.get("role", "") == "customer"]) if "role" in df.columns else 0
    store_queries = len(df[df.get("role", "") == "store"]) if "role" in df.columns else 0

    guardrail_events = 0

    if "guardrail_category" in df.columns:
        guardrail_events = len(
            df[
                df["guardrail_category"]
                .fillna("")
                .astype(str)
                .apply(lambda x: x not in ["", "safe", "none"])
            ]
        )

    strict_filter_events = 0

    if "strict_filter_active" in df.columns:
        strict_filter_events = len(
            df[
                df["strict_filter_active"]
                .fillna("")
                .astype(str)
                .str.lower()
                .isin(["true", "1", "aktif"])
            ]
        )

    semantic_events = 0

    if "semantic_active" in df.columns:
        semantic_events = len(
            df[
                df["semantic_active"]
                .fillna("")
                .astype(str)
                .str.lower()
                .isin(["true", "1", "aktif"])
            ]
        )

    package_events = 0

    if "package_type" in df.columns:
        package_events = len(
            df[
                df["package_type"]
                .fillna("")
                .astype(str)
                .apply(lambda x: x not in ["", "nan", "none"])
            ]
        )

    product_type_counter = split_and_count(df["product_types"]) if "product_types" in df.columns else {}
    brand_counter = split_and_count(df["brands"]) if "brands" in df.columns else {}

    return {
        "total_queries": total_queries,
        "customer_queries": customer_queries,
        "store_queries": store_queries,
        "guardrail_events": guardrail_events,
        "strict_filter_events": strict_filter_events,
        "semantic_events": semantic_events,
        "package_events": package_events,
        "top_product_types": top_items(product_type_counter),
        "top_brands": top_items(brand_counter),
        "top_payments": value_counts_as_list(df, "payment_priority"),
        "top_products": value_counts_as_list(df, "top_product"),
        "top_guardrail_categories": value_counts_as_list(df, "guardrail_category"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def metrics_to_dataframe(metric_list, name_col="Alan", value_col="Değer"):
    if not metric_list:
        return pd.DataFrame(columns=[name_col, value_col])

    return pd.DataFrame(metric_list, columns=[name_col, value_col])


def get_recent_activity(limit=50):
    df = safe_read_behavior_log()

    if df.empty:
        return pd.DataFrame()

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp", ascending=False)

    return df.head(limit)


def get_guardrail_report():
    df = safe_read_behavior_log()

    if df.empty or "guardrail_category" not in df.columns:
        return pd.DataFrame()

    report = (
        df["guardrail_category"]
        .fillna("unknown")
        .astype(str)
        .value_counts()
        .reset_index()
    )

    report.columns = ["guardrail_category", "count"]

    return report


def get_product_interest_report():
    df = safe_read_behavior_log()

    if df.empty or "product_types" not in df.columns:
        return pd.DataFrame(columns=["product_type", "count"])

    counter = split_and_count(df["product_types"])

    return pd.DataFrame(
        top_items(counter, limit=20),
        columns=["product_type", "count"]
    )


def get_payment_interest_report():
    df = safe_read_behavior_log()

    if df.empty or "payment_priority" not in df.columns:
        return pd.DataFrame(columns=["payment_priority", "count"])

    report = (
        df["payment_priority"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .reset_index()
    )

    report.columns = ["payment_priority", "count"]

    return report


def get_top_product_report():
    df = safe_read_behavior_log()

    if df.empty or "top_product" not in df.columns:
        return pd.DataFrame(columns=["product", "count"])

    report = (
        df["top_product"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .reset_index()
    )

    report.columns = ["product", "count"]

    return report


if __name__ == "__main__":
    metrics = calculate_ai_metrics()

    print("AI METRICS")
    print(metrics)

    print("\nRECENT ACTIVITY")
    print(get_recent_activity(10))