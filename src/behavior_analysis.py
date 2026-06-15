import pandas as pd


def load_user_behavior(file_path="data/user_behavior.csv"):
    behavior_df = pd.read_csv(file_path)
    return behavior_df


def analyze_behavior(behavior_df, products_df, user_id=1):
    user_actions = behavior_df[behavior_df["user_id"] == user_id]

    merged_df = user_actions.merge(
        products_df,
        on="product_id",
        how="left"
    )

    return merged_df


def get_behavior_summary(behavior_df, user_id=1):
    user_actions = behavior_df[behavior_df["user_id"] == user_id]

    favorite_count = len(user_actions[user_actions["action"] == "favorite"])
    cart_count = len(user_actions[user_actions["action"] == "cart"])
    view_count = len(user_actions[user_actions["action"] == "view"])

    return {
        "favorite_count": favorite_count,
        "cart_count": cart_count,
        "view_count": view_count
    }


def suggest_alternatives_from_behavior(behavior_df, products_df, user_id=1):
    user_actions = behavior_df[behavior_df["user_id"] == user_id]

    interested_product_ids = user_actions[
        user_actions["action"].isin(["favorite", "cart"])
    ]["product_id"].tolist()

    interested_products = products_df[
        products_df["product_id"].isin(interested_product_ids)
    ]

    if interested_products.empty:
        return products_df.head(3)

    interested_categories = interested_products["category"].unique().tolist()

    alternatives = products_df[
        (products_df["category"].isin(interested_categories)) &
        (~products_df["product_id"].isin(interested_product_ids))
    ]

    alternatives = alternatives.sort_values(by="price", ascending=True)

    return alternatives.head(5)