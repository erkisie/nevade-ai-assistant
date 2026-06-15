def filter_products(df, selected_category=None, max_price=None, only_in_stock=False):
    filtered_df = df.copy()

    if selected_category and selected_category != "Tüm Kategoriler":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]

    if max_price is not None:
        filtered_df = filtered_df[filtered_df["price"].astype(float) <= max_price]

    if only_in_stock:
        filtered_df = filtered_df[
            filtered_df["stock_status"].astype(str).str.lower() == "stokta"
        ]

    return filtered_df