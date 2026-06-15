import difflib


BRAND_ALIASES = {
    "macbook": "apple",
    "iphone": "apple",
    "galaxy": "samsung",
    "redmi": "xiaomi",
    "idea pad": "lenovo",
    "ideapad": "lenovo",
    "vivobook": "asus",
    "aspire": "acer",
    "inspiron": "dell"
}


def normalize_text(text):
    return str(text).lower().strip()


def get_brand_alias(word):
    word = normalize_text(word)

    if word in BRAND_ALIASES:
        return BRAND_ALIASES[word]

    return word


def extract_possible_terms(user_query):
    query = normalize_text(user_query)

    separators = [
        " mu ",
        " mü ",
        " mı ",
        " mi ",
        " vs ",
        " veya ",
        " ile ",
        " karşılaştır",
        " karsilastir",
        " kıyasla",
        " kiyasla"
    ]

    cleaned_query = query

    for sep in separators:
        cleaned_query = cleaned_query.replace(sep, "|")

    terms = [
        term.strip()
        for term in cleaned_query.split("|")
        if term.strip() != ""
    ]

    return terms


def calculate_text_similarity(text_1, text_2):
    text_1 = normalize_text(text_1)
    text_2 = normalize_text(text_2)

    return difflib.SequenceMatcher(None, text_1, text_2).ratio()


def find_best_product_for_term(term, products_df):
    term = normalize_text(term)
    alias_term = get_brand_alias(term)

    best_score = 0
    best_row = None

    for _, row in products_df.iterrows():
        product_name = normalize_text(row.get("product_name", ""))
        brand = normalize_text(row.get("brand", ""))
        category = normalize_text(row.get("category", ""))
        description = normalize_text(row.get("description", ""))

        score = 0

        if term == product_name:
            score += 100

        if term in product_name:
            score += 80

        if product_name in term:
            score += 70

        if alias_term == brand:
            score += 65

        if term == brand:
            score += 65

        if term in brand:
            score += 50

        if term in category:
            score += 35

        if term in description:
            score += 25

        fuzzy_name_score = calculate_text_similarity(term, product_name) * 40
        fuzzy_brand_score = calculate_text_similarity(alias_term, brand) * 35

        score += fuzzy_name_score
        score += fuzzy_brand_score

        if score > best_score:
            best_score = score
            best_row = row

    if best_score < 35:
        return None

    return best_row


def find_products_mentioned_in_query(user_query, products_df):
    terms = extract_possible_terms(user_query)
    matched_products = []

    for term in terms:
        product = find_best_product_for_term(term, products_df)

        if product is not None:
            product_id = str(product.get("product_id", ""))

            already_exists = any(
                str(item.get("product_id", "")) == product_id
                for item in matched_products
            )

            if not already_exists:
                matched_products.append(product)

    if len(matched_products) == 0:
        query = normalize_text(user_query)

        for _, row in products_df.iterrows():
            product_name = normalize_text(row.get("product_name", ""))
            brand = normalize_text(row.get("brand", ""))

            if brand in query or product_name in query:
                product_id = str(row.get("product_id", ""))

                already_exists = any(
                    str(item.get("product_id", "")) == product_id
                    for item in matched_products
                )

                if not already_exists:
                    matched_products.append(row)

    return matched_products