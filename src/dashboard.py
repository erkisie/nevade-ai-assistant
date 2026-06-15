def get_dashboard_metrics(df):
    total_products = len(df)
    total_categories = df["category"].nunique()
    total_brands = df["brand"].nunique()

    in_stock_count = len(
        df[df["stock_status"].astype(str).str.lower() == "stokta"]
    )

    avg_price = df["price"].astype(float).mean()
    max_price = df["price"].astype(float).max()
    min_price = df["price"].astype(float).min()

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_brands": total_brands,
        "in_stock_count": in_stock_count,
        "avg_price": avg_price,
        "max_price": max_price,
        "min_price": min_price
    }


def get_category_distribution(df):
    return df["category"].value_counts()


def get_brand_distribution(df):
    return df["brand"].value_counts()