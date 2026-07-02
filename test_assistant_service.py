from src.assistant_service import (
    load_products,
    run_customer_assistant,
    get_quick_customer_prompts,
    calculate_product_metrics,
)


def run_test():
    products_df = load_products()

    print("ÜRÜN SAYISI:", len(products_df))

    metrics = calculate_product_metrics(products_df)
    print("METRICS:", metrics)

    context = {}

    response1 = run_customer_assistant(
        products_df=products_df,
        user_query="Annem için kullanımı kolay telefon öner",
        customer_context=context,
    )

    context["customer_profile"] = response1.get("customer_profile")

    print("\n--- 1. CEVAP ---")
    print("DECISION:", response1.get("decision"))
    print("LABEL:", response1.get("decision_label"))
    print("PROFILE:", response1.get("profile_summary"))
    print(response1.get("answer"))

    response2 = run_customer_assistant(
        products_df=products_df,
        user_query="Daha ucuzu var mı?",
        customer_context=context,
        current_results=response1.get("result_df"),
    )

    context["customer_profile"] = response2.get("customer_profile")

    print("\n--- 2. CEVAP ---")
    print("DECISION:", response2.get("decision"))
    print("LABEL:", response2.get("decision_label"))
    print("PROFILE:", response2.get("profile_summary"))
    print(response2.get("answer"))

    response3 = run_customer_assistant(
        products_df=products_df,
        user_query="Senet olur mu?",
        customer_context=context,
        current_results=response2.get("result_df"),
    )

    print("\n--- 3. CEVAP ---")
    print("DECISION:", response3.get("decision"))
    print("LABEL:", response3.get("decision_label"))
    print("PROFILE:", response3.get("profile_summary"))
    print(response3.get("answer"))

    print("\nHIZLI SORULAR:")
    for prompt in get_quick_customer_prompts():
        print("-", prompt)


if __name__ == "__main__":
    run_test()